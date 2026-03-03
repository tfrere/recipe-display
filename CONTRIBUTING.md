# Contributing

Thanks for your interest in contributing to Recipe Display! Here's how to get started.

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Poetry](https://python-poetry.org/) for Python dependencies
- [Yarn](https://yarnpkg.com/) for Node dependencies
- Docker (optional, for one-command setup)

### Option A: Docker (recommended)

```bash
cp server/.env.example server/.env
# Edit server/.env with your API keys
docker compose up
```

Client at `http://localhost:5173`, server at `http://localhost:3001`.

### Option B: Manual

```bash
# Server
cd server
cp .env.example .env
poetry install
poetry run uvicorn server:app --port 3001 --reload

# Client (in a second terminal)
cd client
yarn install
yarn dev
```

## Development workflow

1. Fork the repo and create a branch from `main`.
2. Make your changes.
3. Run the tests:

```bash
# Server
cd server && poetry run pytest

# Client
cd client && yarn test
```

4. Run the linters:

```bash
# Client
cd client && yarn lint
```

5. Open a pull request against `main`.

## Project structure

| Path | What it does |
|------|-------------|
| `client/` | React SPA (Vite + MUI, i18n en/fr) |
| `server/` | FastAPI backend |
| `server/repositories/` | Storage abstraction layer (Repository Pattern) |
| `server/services/` | Business logic & subprocess orchestration |
| `server/packages/recipe_scraper/` | Scraping, enrichment, nutrition matching |
| `server/packages/recipe_structurer/` | LLM-based recipe structuring |
| `server/packages/web_scraper/` | HTML/URL content fetching |
| `recipe_importer/` | Batch import CLI |
| `scripts/` | Quality auditing and data maintenance |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full pipeline documentation.

## What to work on

- Check the [open issues](../../issues) for bugs and feature requests.
- Issues labeled **good first issue** are a great place to start.
- [PIPELINE_IMPROVEMENTS.md](PIPELINE_IMPROVEMENTS.md) lists known quality issues in the nutrition/structuring pipeline.

## Conventions

- **Commits**: short imperative subject, e.g. "add auth to delete endpoints".
- **Locale strings**: all user-facing UI text must go through i18n `t()` keys in `client/src/locales/`.
- **Recipe content**: stays in the source language (French for FR sources, English for EN). Never translate recipe content at runtime.
- **Technical metadata** (field names, logs, comments): English.

## Code of conduct

Be kind. Assume good intent. Keep discussions constructive and focused on the work.
