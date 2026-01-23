"""
Gemini (Google) LLM integration.
Used as the primary processor for search results.
"""
import json
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import ToolCallLogger

from .base import BaseLLM, LLMResponse


class GeminiLLM(BaseLLM):
    """Gemini LLM provider using Google AI API."""

    provider_name = "gemini"
    default_model = "gemini-2.0-flash"

    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.logger = ToolCallLogger("gemini")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from Gemini."""
        model_name = model or self.default_model

        self.logger.log_call(
            action="generate",
            params={
                "model": model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "prompt_length": len(prompt),
            },
        )

        try:
            model_instance = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )

            generation_config = genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            response = await model_instance.generate_content_async(
                prompt,
                generation_config=generation_config,
            )

            # Extract token counts if available
            input_tokens = None
            output_tokens = None
            if hasattr(response, "usage_metadata"):
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

            llm_response = LLMResponse(
                content=response.text,
                provider=self.provider_name,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=(input_tokens or 0) + (output_tokens or 0) if input_tokens or output_tokens else None,
                success=True,
                raw_response=response,
            )

            self.logger.log_result(
                action="generate",
                success=True,
                result=f"Generated response",
            )

            return llm_response

        except Exception as e:
            self.logger.log_result(
                action="generate",
                success=False,
                error=str(e),
            )
            return LLMResponse(
                content="",
                provider=self.provider_name,
                model=model_name,
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
        """Generate a structured response from Gemini."""
        structured_prompt = self._build_structured_prompt(prompt, output_schema)

        system = system_prompt or (
            "You are a helpful assistant that always responds with valid JSON. "
            "Never include markdown code blocks or explanations, just pure JSON."
        )

        response = await self.generate(
            prompt=structured_prompt,
            system_prompt=system,
            model=model,
            temperature=0.2,
            **kwargs,
        )

        if not response.success:
            return None, response

        try:
            content = response.content.strip()
            # Remove markdown if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
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
        """Check if Gemini API is accessible."""
        try:
            response = await self.generate(
                prompt="Say 'ok'",
                max_tokens=10,
            )
            return response.success
        except Exception:
            return False

    async def process_search_results(
        self,
        raw_results: list[dict],
        schema: type[BaseModel],
    ) -> list[BaseModel]:
        """
        Process raw search results into structured event data.
        This is Gemini's main role as the processor.
        """
        if not raw_results:
            return []

        system_prompt = """You are a data extraction specialist. Your job is to extract
structured event information from raw search results.

RULES:
1. Only extract information that is explicitly present in the source
2. If a field is not available, use null
3. NEVER make up or guess information
4. Always preserve the source URL for traceability
5. If an event seems invalid or incomplete, skip it"""

        prompt = f"""Extract event information from these search results:

{json.dumps(raw_results, indent=2)}

Return a JSON array of events matching the provided schema.
Only include events with verifiable information."""

        parsed, response = await self.generate_structured(
            prompt=prompt,
            output_schema=schema,
            system_prompt=system_prompt,
        )

        if parsed:
            return [parsed] if not isinstance(parsed, list) else parsed
        return []
