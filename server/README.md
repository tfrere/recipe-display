# Recipe Generator

A Python package to generate structured recipes from web content using OpenAI's GPT models.

## Installation

```bash
pip install recipe-generator
```

## Usage

```python
import asyncio
from recipe_generator import RecipeGenerator

async def main():
    generator = RecipeGenerator(api_key="your-openai-api-key")
    recipe = await generator.generate_from_url("https://example.com/recipe")
    print(recipe.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## Features

- Extract recipe content from web pages
- Clean and structure recipe data
- Handle authentication for protected recipe sites
- Generate standardized recipe format
- Save recipes with associated images
