"""
LLM Router with fallback chain.
Implements the fallback strategy: Gemini → OpenAI → Claude → Error
"""
from typing import Any

from pydantic import BaseModel

from app.core.logging import get_logger

from .base import BaseLLM, LLMResponse
from .claude import ClaudeLLM
from .gemini import GeminiLLM
from .openai import OpenAILLM

logger = get_logger("llm.router")


class LLMRouter:
    """
    Routes LLM requests with automatic fallback.

    Architecture:
    - Claude: Prompt engineering (primary)
    - Gemini: Processing (primary, cheaper)
    - OpenAI: Processing fallback
    - Claude: Final fallback for processing
    """

    def __init__(self):
        self.claude = ClaudeLLM()
        self.gemini = GeminiLLM()
        self.openai = OpenAILLM()

        # Fallback chain for processing
        self._processor_chain: list[BaseLLM] = [
            self.gemini,
            self.openai,
            self.claude,
        ]

        # Track failures for circuit breaker
        self._failure_counts: dict[str, int] = {
            "claude": 0,
            "gemini": 0,
            "openai": 0,
        }
        self._circuit_open: dict[str, bool] = {
            "claude": False,
            "gemini": False,
            "openai": False,
        }

    def _is_available(self, provider: str) -> bool:
        """Check if provider is available (circuit not open)."""
        return not self._circuit_open.get(provider, False)

    def _record_failure(self, provider: str) -> None:
        """Record a failure and potentially open circuit."""
        self._failure_counts[provider] = self._failure_counts.get(provider, 0) + 1
        if self._failure_counts[provider] >= 3:
            self._circuit_open[provider] = True
            logger.warning(f"Circuit opened for {provider} after 3 failures")

    def _record_success(self, provider: str) -> None:
        """Record success and reset failure count."""
        self._failure_counts[provider] = 0
        self._circuit_open[provider] = False

    async def generate_prompt(
        self,
        query: str,
        category: str,
        location: str,
        date_range: str,
        **kwargs: Any,
    ) -> str:
        """
        Generate optimized search prompt using Claude.
        Claude is the designated prompt engineer.
        """
        if not self._is_available("claude"):
            logger.warning("Claude circuit open, using raw query")
            return query

        try:
            prompt = await self.claude.create_search_prompt(
                query=query,
                category=category,
                location=location,
                date_range=date_range,
                **kwargs,
            )
            self._record_success("claude")
            return prompt
        except Exception as e:
            self._record_failure("claude")
            logger.error(f"Claude prompt generation failed: {e}")
            return query

    async def process_results(
        self,
        raw_results: list[dict],
        output_schema: type[BaseModel],
        prompt: str | None = None,
    ) -> tuple[BaseModel | None, LLMResponse]:
        """
        Process raw results using the fallback chain.
        Tries: Gemini → OpenAI → Claude
        """
        if not raw_results:
            return None, LLMResponse(
                content="",
                provider="none",
                model="none",
                success=False,
                error="No results to process",
            )

        processing_prompt = prompt or f"""Extract and structure the following data:
{raw_results}

Follow the schema exactly. Only include verified information."""

        last_error = None

        for llm in self._processor_chain:
            provider = llm.provider_name

            if not self._is_available(provider):
                logger.info(f"Skipping {provider} (circuit open)")
                continue

            logger.info(f"Attempting processing with {provider}")

            try:
                parsed, response = await llm.generate_structured(
                    prompt=processing_prompt,
                    output_schema=output_schema,
                )

                if response.success and parsed:
                    self._record_success(provider)
                    logger.info(f"Processing succeeded with {provider}")
                    return parsed, response
                else:
                    self._record_failure(provider)
                    last_error = response.error

            except Exception as e:
                self._record_failure(provider)
                last_error = str(e)
                logger.error(f"Processing with {provider} failed: {e}")

        # All providers failed
        return None, LLMResponse(
            content="",
            provider="fallback_exhausted",
            model="none",
            success=False,
            error=f"All processors failed. Last error: {last_error}",
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        preferred_provider: str = "gemini",
        **kwargs: Any,
    ) -> LLMResponse:
        """
        General generation with fallback.
        """
        providers = {
            "claude": self.claude,
            "gemini": self.gemini,
            "openai": self.openai,
        }

        # Start with preferred, then try others
        order = [preferred_provider] + [p for p in providers if p != preferred_provider]

        for provider_name in order:
            if not self._is_available(provider_name):
                continue

            provider = providers[provider_name]
            try:
                response = await provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    **kwargs,
                )
                if response.success:
                    self._record_success(provider_name)
                    return response
                else:
                    self._record_failure(provider_name)
            except Exception as e:
                self._record_failure(provider_name)
                logger.error(f"Generation with {provider_name} failed: {e}")

        return LLMResponse(
            content="",
            provider="fallback_exhausted",
            model="none",
            success=False,
            error="All LLM providers failed",
        )

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all LLM providers."""
        return {
            "claude": await self.claude.health_check(),
            "gemini": await self.gemini.health_check(),
            "openai": await self.openai.health_check(),
        }

    def reset_circuits(self) -> None:
        """Reset all circuit breakers."""
        self._failure_counts = {"claude": 0, "gemini": 0, "openai": 0}
        self._circuit_open = {"claude": False, "gemini": False, "openai": False}
        logger.info("All circuits reset")
