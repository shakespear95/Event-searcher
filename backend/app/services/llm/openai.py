"""
OpenAI LLM integration.
Used as fallback processor when Gemini fails.
"""
import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import ToolCallLogger

from .base import BaseLLM, LLMResponse


class OpenAILLM(BaseLLM):
    """OpenAI LLM provider."""

    provider_name = "openai"
    default_model = "gpt-4o-mini"

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.logger = ToolCallLogger("openai")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from OpenAI."""
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
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content or ""

            llm_response = LLMResponse(
                content=content,
                provider=self.provider_name,
                model=model,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                total_tokens=response.usage.total_tokens if response.usage else None,
                success=True,
                raw_response=response,
            )

            self.logger.log_result(
                action="generate",
                success=True,
                result=f"Generated {llm_response.output_tokens} tokens",
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
        """Generate a structured response from OpenAI."""
        model = model or self.default_model

        self.logger.log_call(
            action="generate_structured",
            params={"model": model, "schema": output_schema.__name__},
        )

        try:
            messages = []
            system = system_prompt or "You are a helpful assistant that responds with valid JSON."
            messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": self._build_structured_prompt(prompt, output_schema)})

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"

            llm_response = LLMResponse(
                content=content,
                provider=self.provider_name,
                model=model,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                total_tokens=response.usage.total_tokens if response.usage else None,
                success=True,
                raw_response=response,
            )

            data = json.loads(content)
            parsed = output_schema.model_validate(data)

            self.logger.log_result(
                action="generate_structured",
                success=True,
                result=f"Parsed {output_schema.__name__}",
            )

            return parsed, llm_response

        except json.JSONDecodeError as e:
            self.logger.log_result(
                action="generate_structured",
                success=False,
                error=f"JSON parse error: {e}",
            )
            return None, LLMResponse(
                content="",
                provider=self.provider_name,
                model=model,
                success=False,
                error=f"JSON parse error: {e}",
            )
        except Exception as e:
            self.logger.log_result(
                action="generate_structured",
                success=False,
                error=str(e),
            )
            return None, LLMResponse(
                content="",
                provider=self.provider_name,
                model=model,
                success=False,
                error=str(e),
            )

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            response = await self.generate(
                prompt="Say 'ok'",
                max_tokens=10,
            )
            return response.success
        except Exception:
            return False
