from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

from ..providers.base import LLMProvider
from ..exceptions.validation import ValidationRetryError

T = TypeVar('T', bound=BaseModel)

class StructuredGenerator:
    def __init__(
        self,
        provider: LLMProvider,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.max_retries = max_retries

    async def generate(
        self,
        prompt: str,
        schema: Type[T],
    ) -> T:
        """Generate structured content with automatic retry on validation failure"""
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                result = await self.provider.generate(prompt, schema)
                return result
            except ValidationError as e:
                attempts += 1
                last_error = e
                
                if attempts >= self.max_retries:
                    break
                    
                # Enhance prompt with validation error feedback
                prompt = self._enhance_prompt_with_error(prompt, e)

        raise ValidationRetryError(
            f"Failed to generate valid content after {self.max_retries} attempts",
            last_error=last_error
        )

    def _enhance_prompt_with_error(self, original_prompt: str, error: ValidationError) -> str:
        """Enhance the prompt with validation error information"""
        error_details = "\n".join([f"- {err['msg']}" for err in error.errors()])
        return f"""{original_prompt}

Previous attempt failed with the following validation errors:
{error_details}

Please ensure the response matches the required schema and fix these errors.""" 