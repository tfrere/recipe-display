import os
import json
from typing import Any, Dict, Type, TypeVar
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from .base import LLMProvider

T = TypeVar('T', bound=BaseModel)

class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        model: str = "claude-3-haiku-20240307",
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.client = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        )

    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
    ) -> T:
        """Generate structured content using Anthropic's API"""
        schema_json = output_schema.model_json_schema()
        enhanced_prompt = f"""You must respond with a valid JSON that matches this schema:
{json.dumps(schema_json, indent=2)}

Here's the actual prompt:
{prompt}

Remember to only respond with the JSON, nothing else."""

        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": enhanced_prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **self.additional_params
        )

        # Parse the response content as JSON and validate against the schema
        content = response.content[0].text
        data = json.loads(content)
        return output_schema.model_validate(data)

    def get_model_config(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.additional_params
        }

    @property
    def provider_name(self) -> str:
        return "anthropic" 