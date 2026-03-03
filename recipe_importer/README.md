# Recipe Importer

Batch import tool for recipe-display. Supports URL-based and text-based import.

## Installation

```bash
poetry install
```

## URL Discovery

Before importing, you need recipe URLs. The discovery script automatically finds all recipe URLs from any site:

```bash
# Run from the server/ directory (has all dependencies)
cd ../server

# Give it any recipe site root URL
poetry run python ../scripts/discover_recipe_urls.py https://smittenkitchen.com/ -o ../recipe_importer/urls_discovered.json

# Works with authenticated sites too (uses auth_presets.json automatically)
poetry run python ../scripts/discover_recipe_urls.py https://books.ottolenghi.co.uk/
```

**How it works:**

1. Tries to find the site's XML sitemap (robots.txt → sitemap index → sub-sitemaps)
2. Pre-filters URLs with heuristics (`/recipe/` in path → instant match, no LLM needed)
3. Sends ambiguous URLs to an LLM (DeepSeek V3.2) for classification
4. Falls back to HTML crawling if no sitemap found

**Options:**

| Flag | Description |
|------|-------------|
| `-o FILE` | Output JSON path (default: `urls_discovered.json`) |
| `--auth FILE` | Auth presets file (default: `auth_presets.json`) |
| `--no-sitemap` | Skip sitemap, go straight to HTML crawl |
| `--depth N` | Max crawl depth for HTML mode (default: 2) |
| `--max-pages N` | Max pages to fetch in HTML mode (default: 50) |

**Cost:** Near-zero. Sites with `/recipe/` in URLs use only heuristics (no LLM). Worst case (ambiguous URLs) ≈ $0.05 per site.

## Batch Import

### Import from URLs

```bash
poetry run recipe-importer url -f urls.json
```

Format of `urls.json`:

```json
["https://www.site1.com/recipe1", "https://www.site2.com/recipe2"]
```

### Import from text files

```bash
poetry run recipe-importer text -d ./my-recipes
```

Directory structure:

```
my-recipes/
  ├── recipe1.txt    # Recipe content
  ├── recipe1.jpg    # Optional image (same base name as .txt)
  ├── recipe2.txt
  └── recipe2.png
```

### Options

| Flag | Description |
|------|-------------|
| `-c N` | Concurrent imports (default: 10) |
| `-a URL` | API URL (default: `http://localhost:3001`) |
| `--auth FILE` | Auth presets file (default: `auth_presets.json`) |
| `--max-per-domain N` | Max concurrent requests per domain (default: 8) |
| `--list-recipes` | List recipes after import |
| `--clear` | Clear server recipes/images before import |
| `--headless` | No TUI, console output only |

## Full workflow example

```bash
# 1. Discover recipe URLs
cd server
poetry run python ../scripts/discover_recipe_urls.py https://cookieandkate.com/ -o ../recipe_importer/urls_discovered.json

# 2. Import them
cd ../recipe_importer
poetry run recipe-importer url -f urls_discovered.json

# Or in one pipeline:
cd server
poetry run python ../scripts/discover_recipe_urls.py https://cookieandkate.com/ -o /tmp/urls.json && \
cd ../recipe_importer && poetry run recipe-importer url -f /tmp/urls.json
```

## Auth Presets

For sites requiring authentication (e.g. Ottolenghi), configure `auth_presets.json`:

```json
{
  "books.ottolenghi.co.uk": {
    "id": "ottolenghi",
    "domain": ".books.ottolenghi.co.uk",
    "type": "cookie",
    "values": {
      "SESSION_COOKIE_NAME": "session_cookie_value"
    }
  }
}
```

Both the discovery script and the importer use this file automatically.
