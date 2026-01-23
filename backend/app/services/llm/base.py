"""
Base LLM interface.
All LLM providers must implement this interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    success: bool = True
    error: str | None = None
    raw_response: Any = None


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    Ensures consistent interface across Claude, Gemini, OpenAI.
    """

    provider_name: str = "base"
    default_model: str = ""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            model: Model to use (defaults to provider's default)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: type[BaseModel],
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> tuple[BaseModel | None, LLMResponse]:
        """
        Generate a structured response matching a Pydantic schema.

        Args:
            prompt: The user prompt
            output_schema: Pydantic model class for output
            system_prompt: Optional system prompt
            model: Model to use

        Returns:
            Tuple of (parsed model or None, LLMResponse)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is accessible."""
        pass

    def _build_structured_prompt(
        self, prompt: str, output_schema: type[BaseModel]
    ) -> str:
        """Build a prompt that requests structured JSON output."""
        schema_json = output_schema.model_json_schema()
        return f"""{prompt}

You MUST respond with valid JSON matching this exact schema:
```json
{schema_json}
```

Respond ONLY with the JSON object, no additional text or markdown."""
