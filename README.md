# Structured LLM

A provider-agnostic library for generating structured outputs from LLMs using Pydantic and Instructor.

## Features

- Provider agnostic (supports Anthropic, Deepseek, and easily extensible)
- Automatic validation and retry with Pydantic
- Async support
- Type-safe with full typing support
- Easy to extend with new providers

## Installation

```bash
poetry install
```

## Environment Variables

Create a `.env` file with your API keys:

```env
ANTHROPIC_API_KEY=your_anthropic_key
DEEPSEEK_API_KEY=your_deepseek_key
```

## Usage

Here's a simple example of how to use the library:

```python
from pydantic import BaseModel, Field
from structured_llm.providers.anthropic import AnthropicProvider
from structured_llm.core.generator import StructuredGenerator

# Define your schema
class Recipe(BaseModel):
    title: str
    ingredients: list[str]
    steps: list[str]
    prep_time_minutes: int
    cooking_time_minutes: int
    difficulty: str

# Create a provider
provider = AnthropicProvider(
    model="claude-3-haiku",
    temperature=0.7
)

# Create a generator
generator = StructuredGenerator(provider=provider)

# Generate content
recipe = await generator.generate(
    prompt="Generate a recipe for chocolate cake",
    schema=Recipe
)

print(recipe.model_dump_json(indent=2))
```

## Adding a New Provider

To add a new provider, create a new class that inherits from `LLMProvider`:

```python
from structured_llm.providers.base import LLMProvider

class MyProvider(LLMProvider):
    async def generate(self, prompt: str, output_schema: Type[T]) -> T:
        # Implement your provider-specific logic here
        pass

    def get_model_config(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.additional_params
        }

    @property
    def provider_name(self) -> str:
        return "my_provider"
```

## Examples

Check out the `examples` directory for more usage examples.
