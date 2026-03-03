# Recipe Structurer

Converts raw recipe text into a validated, graph-structured JSON format using a 3-pass LLM pipeline.

## Architecture

```
Raw text → [Pass 1: Preformat] → [Pass 1.5: NER] → [Pass 2: DAG] → Recipe JSON
                (DeepSeek)     (CRF ingredient-parser)  (Instructor)
```

- **Pass 1 (Preformat)**: Cleans messy web-scraped text into structured plain text with `[english_name] {category}` annotations. Uses raw OpenAI client.
- **Pass 1.5 (NER)**: Parses annotated ingredient lines into `Ingredient` objects via `strangetom/ingredient-parser` (CRF v2.5.0). Deterministic — no LLM.
- **Pass 2 (DAG)**: Builds the complete `Recipe` JSON graph from structured text + pre-parsed ingredients. Uses Instructor for Pydantic-validated structured output with automatic retries.

Post-processing applies deterministic ID correction (suffix stripping + original-language name lookup) to fix LLM reference mismatches.

## Installation

```bash
poetry install
```

## Configuration

Set one of these API keys in your `.env`:

- `OPENROUTER_API_KEY` — OpenRouter (default, routes to DeepSeek)
- `DEEPSEEK_API_KEY` — Direct DeepSeek API

## Usage

```python
from recipe_structurer import RecipeStructurer

structurer = RecipeStructurer()
recipe = await structurer.structure(content)

print(recipe.metadata.title)
print(recipe.ingredients)
print(recipe.steps)
```

## Testing

```bash
poetry run pytest
```

## Key modules

| Module | Role |
|---|---|
| `shared.py` | Shared constants (equipment keywords, ingredient categories) and ISO 8601 parsing |
| `models/recipe.py` | Pydantic models with 6-rule graph validator |
| `generator.py` | 3-pass pipeline orchestrator |
| `services/preformat.py` | Pass 1 — LLM text cleaning |
| `services/ingredient_parser.py` | Pass 1.5 — CRF parsing + deterministic ID resolution |
| `prompts/preformat.py` | System/user prompts for Pass 1 |
| `prompts/unified.py` | System/user prompts for Pass 2 |
