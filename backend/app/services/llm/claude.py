"""
Claude (Anthropic) LLM integration.
Used as the Prompt Engineer in the architecture.
"""
import json
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import ToolCallLogger

from .base import BaseLLM, LLMResponse


class ClaudeLLM(BaseLLM):
    """Claude LLM provider using Anthropic API."""

    provider_name = "claude"
    default_model = "claude-sonnet-4-20250514"

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.logger = ToolCallLogger("claude")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from Claude."""
        model = model or self.default_model

        self.logger.log_call(
            action="generate",
            params={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "prompt_length": len(prompt),
            },
        )

        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
            )

            response = LLMResponse(
                content=message.content[0].text,
                provider=self.provider_name,
                model=model,
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
                total_tokens=message.usage.input_tokens + message.usage.output_tokens,
                success=True,
                raw_response=message,
            )

            self.logger.log_result(
                action="generate",
                success=True,
                result=f"Generated {response.output_tokens} tokens",
            )

            return response

        except Exception as e:
            self.logger.log_result(
                action="generate",
                success=False,
                error=str(e),
            )
            return LLMResponse(
                content="",
                provider=self.provider_name,
                model=model,
                success=False,
                error=str(e),
            )

    async def generate_structured(
        self,
        prompt: str,
        output_schema: type[BaseModel],
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> tuple[BaseModel | None, LLMResponse]:
        """Generate a structured response from Claude."""
        structured_prompt = self._build_structured_prompt(prompt, output_schema)

        system = system_prompt or (
            "You are a helpful assistant that always responds with valid JSON. "
            "Never include markdown code blocks, just pure JSON."
        )

        response = await self.generate(
            prompt=structured_prompt,
            system_prompt=system,
            model=model,
            temperature=0.3,  # Lower temperature for structured output
            **kwargs,
        )

        if not response.success:
            return None, response

        try:
            # Parse JSON from response
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)
            parsed = output_schema.model_validate(data)
            return parsed, response

        except (json.JSONDecodeError, Exception) as e:
            self.logger.log_result(
                action="generate_structured",
                success=False,
                error=f"Failed to parse response: {e}",
            )
            response.success = False
            response.error = f"Parse error: {e}"
            return None, response

    async def health_check(self) -> bool:
        """Check if Claude API is accessible."""
        try:
            response = await self.generate(
                prompt="Say 'ok'",
                max_tokens=10,
            )
            return response.success
        except Exception:
            return False

    async def create_search_prompt(
        self,
        query: str,
        category: str,
        location: str,
        date_range: str,
        additional_context: str = "",
    ) -> str:
        """
        Use Claude to create an optimized search prompt.
        This is Claude's main role in the architecture.
        """
        system_prompt = """You are a search query optimizer specializing in event discovery.
Your job is to take a user's event search query and create optimized search prompts
for Perplexity and Google Search (SerpAPI).

Output a search query that will find:
1. Specific events matching the criteria
2. Hidden gems and lesser-known events
3. Events with verifiable sources (official websites, event pages)

Be specific about location and time. Include relevant keywords for the category."""

        prompt = f"""Create an optimized search query for finding events.

User Query: {query}
Category: {category}
Location: {location}
Date Range: {date_range}
{f"Additional Context: {additional_context}" if additional_context else ""}

Respond with ONLY the search query, no explanation."""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=200,
        )

        return response.content.strip() if response.success else query
