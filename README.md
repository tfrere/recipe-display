# Recipe Display

Structured recipe management platform: scrape, structure, enrich, and display recipes with DAG-based step graphs, nutritional data, meal planning, and more.

## Architecture

```
client/               React SPA (Vite + MUI)
server/               FastAPI server (port 3001)
  packages/
    recipe_scraper/   CLI: scrape → structure → enrich → save JSON
    recipe_structurer/ LLM-powered recipe structuring (DeepSeek/OpenRouter)
    web_scraper/      HTML/URL content fetcher
recipe_importer/      Batch import CLI (reads URLs, calls server API)
```

Recipes are stored as JSON files on disk (`server/data/recipes/*.recipe.json`).
No database required.

## Prerequisites

- Python 3.12+
- Node.js 20+
- [Poetry](https://python-poetry.org/) for Python dependency management

## Setup

### Server

```bash
cd server
cp .env.example .env
# Edit .env with your API keys (OPENROUTER_API_KEY, etc.)
poetry install
poetry run uvicorn server:app --port 3001 --reload
```

### Client

```bash
cd client
yarn install
yarn dev
```

### Recipe Importer (batch import)

```bash
cd recipe_importer
poetry install
poetry run python src/main.py --help
```

## Running Tests

### Server + packages

```bash
cd server
poetry run pytest                                    # all tests
poetry run pytest packages/recipe_scraper/tests/     # scraper tests only
poetry run pytest packages/recipe_structurer/tests/  # structurer tests only
```

Some tests require API keys (`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`) and will skip if not set.

### Client

```bash
cd client
yarn test          # single run
yarn test:watch    # watch mode
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | LLM provider for structuring & enrichment |
| `DEEPSEEK_API_KEY` | Optional | Alternative LLM provider |
| `PRIVATE_ACCESS_SECRET` | Optional | Token for private recipe access |
| `LANGFUSE_PUBLIC_KEY` | Optional | Observability (Langfuse) |
| `LANGFUSE_SECRET_KEY` | Optional | Observability (Langfuse) |

## Data Sources

See [DATA_SOURCES.md](DATA_SOURCES.md) for recipe data sources, licenses, and attribution.
