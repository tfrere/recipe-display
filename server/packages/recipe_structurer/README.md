# Recipe Structurer

A Python package for structuring raw recipe content into a standardized format using LLMs.

## Installation

```bash
poetry install
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Then configure:

1. API Keys:

   - `DEEPSEEK_API_KEY`: Your DeepSeek API key
   - `MISTRAL_API_KEY`: Your Mistral API key

2. LLM Provider:
   - `LLM_PROVIDER`: Choose between "deepseek" or "mistral" (default: "mistral")

## Usage

```python
from recipe_structurer import RecipeStructurer

# Initialize with default provider (from LLM_PROVIDER env var)
structurer = RecipeStructurer()

# Or specify a provider explicitly
structurer = RecipeStructurer(provider="deepseek")

# Process a recipe
recipe = await structurer.structure(content)
```

## Testing

```bash
poetry run pytest
```
