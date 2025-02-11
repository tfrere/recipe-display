# New Structured Output

A structured recipe generator using Deepseek LLM and Pydantic.

## Installation

```bash
poetry install
```

## Usage

```python
from new_structured_output.generator import generate_recipe

# Generate a recipe
cleaned_text, recipe_base, recipe_graph = await generate_recipe(recipe_text)
```

## Testing

```bash
poetry run python -m new_structured_output.tests.test_services
```
