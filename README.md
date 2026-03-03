# Recipe Display

Structured recipe management platform: scrape, structure, enrich, and display recipes with nutritional data, cooking timelines, meal planning, and more.

<!-- TODO: Add a hero screenshot or GIF here -->
<!-- ![Recipe Display](docs/screenshots/hero.png) -->

## Features

- **Import recipes from anywhere** — paste a URL, raw text, a photo, or create manually. An LLM pipeline (DeepSeek/OpenRouter) structures everything automatically.
- **Rich nutritional data** — each ingredient is matched against a unified index of ~10,800 foods (USDA, CIQUAL, MEXT Japan) via exact lookup + semantic embeddings. Per-serving macros, minerals, and confidence levels.
- **Cooking mode** — step-by-step walkthrough with built-in timers, hands-free voice progression, and keyboard shortcuts.
- **Cooking timeline (Gantt)** — visual DAG-based schedule showing parallel tasks, active vs. passive time.
- **Ingredient graph** — interactive node graph of recipe structure (ReactFlow).
- **Meal planner** — generate balanced weekly plans with macro tracking (ANSES references), shared-ingredient optimization, and shopping list export.
- **Smart scaling** — adjust servings and all quantities update with unit-aware conversions.
- **Pantry matching** — mark items you have at home; recipes sort by pantry coverage, shopping lists auto-check owned items.
- **Seasonal filtering** — recipes tagged by seasonal produce availability (ADEME data for France).
- **Bilingual UI** — full French/English interface via i18next. Recipe content stays in its source language.
- **Dark mode** — full theme support.
- **Print-friendly** — clean layout optimized for paper.
- **No database required** — recipes stored as JSON files on disk.

<!-- TODO: Add more screenshots here -->
<!--
| Recipe view | Cooking mode | Meal planner |
|:-:|:-:|:-:|
| ![Recipe](docs/screenshots/recipe.png) | ![Cooking](docs/screenshots/cooking.png) | ![Planner](docs/screenshots/planner.png) |
-->

## Quick start (Docker)

```bash
cp server/.env.example server/.env
# Edit server/.env with your API keys (OPENROUTER_API_KEY at minimum)
docker compose up
```

Client at `http://localhost:5173`, API at `http://localhost:3001`.

## Manual setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Poetry](https://python-poetry.org/) for Python dependency management

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
poetry run recipe-importer --help
```

### Recipe URL Discovery

Automatically discover all recipe URLs from any site (sitemap + LLM classification):

```bash
cd server
poetry run python ../scripts/discover_recipe_urls.py https://smittenkitchen.com/ -o urls.json
```

Then import them:

```bash
cd ../recipe_importer
poetry run recipe-importer url -f ../urls.json
```

See [recipe_importer/README.md](recipe_importer/README.md) for full options.

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

## Quality Auditing

Deterministic scripts (zero LLM, zero cost) to check recipe data quality:

```bash
cd server

# Full quality audit (structure, nutrition, graph, metadata, review)
poetry run python scripts/recipe_quality_audit.py

# Compare new recipes vs old (pre-v3) side-by-side
poetry run python scripts/recipe_quality_audit.py --compare

# JSON output (for CI/automation)
poetry run python scripts/recipe_quality_audit.py --json

# Nutrition-specific audits
poetry run python scripts/nutrition_healthcheck.py          # fast metadata + calorie distribution
poetry run python scripts/nutrition_audit.py                # full NutritionAgent validation

# Data cleanup (idempotent, safe to re-run)
poetry run python -m scripts.fix_string_quantities          # coerce string quantities/servings to numbers
poetry run python -m scripts.re_enrich_nutrition --all      # re-compute nutrition with latest data

# Review agent scoring on a sample
poetry run python scripts/score_random_recipes.py
```

See [PIPELINE_IMPROVEMENTS.md](PIPELINE_IMPROVEMENTS.md) for the current quality roadmap and known issues.

## Architecture

```
client/               React SPA (Vite + MUI)
server/               FastAPI server (port 3001)
  repositories/       Storage abstraction (Repository Pattern)
  services/           Business logic & subprocess orchestration
  packages/
    recipe_scraper/   CLI: scrape → structure → enrich → save JSON
    recipe_structurer/ LLM-powered recipe structuring (DeepSeek/OpenRouter)
    web_scraper/      HTML/URL content fetcher
recipe_importer/      Batch import CLI (reads URLs, calls server API)
scripts/
  discover_recipe_urls.py   LLM-powered URL discovery (sitemap + crawl)
  crawl_sitemaps.py         Legacy sitemap crawler (hardcoded Tier S sites)
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full pipeline architecture (scraper → structurer → enricher → reviewer) |
| [DATA_SOURCES.md](DATA_SOURCES.md) | Nutrition data sources, licenses, and attribution |
| [PIPELINE_IMPROVEMENTS.md](PIPELINE_IMPROVEMENTS.md) | Quality audit results, known issues, and improvement roadmap |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to set up, develop, and contribute |
| [NOTICE](NOTICE) | Third-party data licenses (ODbL, Etalab, USDA) |

## License

MIT — see [LICENSE](LICENSE).

Nutrition data files carry their own licenses (ODbL, Licence Ouverte Etalab, public domain). See [NOTICE](NOTICE) for details.
