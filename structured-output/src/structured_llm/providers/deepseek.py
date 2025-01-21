import os
from typing import Any, Dict, Type, TypeVar
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from .base import LLMProvider

T = TypeVar('T', bound=BaseModel)

class DeepseekProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=api_base or "https://api.deepseek.com/v1",
        )
        self.instructor_client = instructor.patch(self.client)

    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
    ) -> T:
        """Generate structured content using Deepseek's API"""
        response = await self.instructor_client.chat.completions.create(
            model=self.model,
            response_model=output_schema,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **self.additional_params
        )
        return response

    def get_model_config(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.additional_params
        }

    @property
    def provider_name(self) -> str:
        return "deepseek" 