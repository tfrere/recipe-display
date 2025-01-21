from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMProvider(ABC):
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.additional_params = kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
    ) -> T:
        """Generate structured content based on prompt and schema"""
        pass

    @abstractmethod
    def get_model_config(self) -> Dict[str, Any]:
        """Return provider-specific model configuration"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider"""
        pass 