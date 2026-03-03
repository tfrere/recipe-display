# Architecture: Recipe Import Pipeline

This document describes how a recipe URL is transformed into a structured, enriched JSON file. It covers every component, model, and decision involved in the process.

## Table of Contents

- [Overview](#overview)
- [Pipeline Diagram](#pipeline-diagram)
- [1. Recipe Importer (CLI Client)](#1-recipe-importer-cli-client)
- [2. Server API](#2-server-api)
- [3. Web Scraper](#3-web-scraper)
- [4. Recipe Structurer](#4-recipe-structurer)
- [5. Recipe Enricher](#5-recipe-enricher)
- [6. Recipe Reviewer](#6-recipe-reviewer)
- [7. Output Format](#7-output-format)
- [8. Data Files Reference](#8-data-files-reference)
- [9. LLM Usage Summary](#9-llm-usage-summary)
- [10. Configuration](#10-configuration)
- [11. Known Limitations & Quality Metrics](#11-known-limitations--quality-metrics)

---

## Overview

The pipeline transforms a recipe URL (or raw text, or image) into a fully structured JSON file containing:

- **Metadata** (title, servings, difficulty, nationality, tags)
- **Ingredients** with quantities, units, English translations, and categories
- **Steps** organized as a Directed Acyclic Graph (DAG) with dependencies
- **Nutrition** per serving (calories, protein, fat, carbs, fiber, sugar, saturated fat + minerals) with confidence scoring
- **Diets** (vegan, vegetarian, pescatarian, gluten-free)
- **Seasons** based on ingredient availability (ADEME data for France)
- **Times** computed from the DAG critical path (total, active, passive)

The system uses **3 LLM calls** per recipe: one to preformat text, one to generate the DAG structure, and one to review the result. Ingredient parsing is hybrid: an LLM annotates ingredient lines, then a CRF model extracts structured data.

### Resilience

Every external call in the pipeline is protected against transient failures:

- **Pass 1 (preformat)**: 2 retries with exponential backoff, 120s timeout per attempt
- **Pass 2 (DAG generation)**: 3 retries via Instructor's built-in retry mechanism
- **Subprocess execution**: 10-minute hard timeout with forced kill
- **Web scraping**: try/except with error trace logging and Langfuse tagging
- **Enrichment**: each sub-step (diets, seasons, times, nutrition) is isolated — a failure in one does not block the others
- **File writes**: atomic JSON writes (temp file + `os.replace`) prevent corruption on crash
- **Slug collisions**: auto-increment suffix (`-2`, `-3`, …) when a file with the same slug exists
- **Progress cleanup**: stale progress entries are garbage-collected after 5 minutes

---

## Pipeline Diagram

```
URL / Text / Image
        │
        ▼
┌──────────────────┐
│  Recipe Importer  │  CLI client (Python)
│  recipe_importer/ │  Sends URL to server API
└────────┬─────────┘
         │ POST /api/recipes
         ▼
┌──────────────────┐
│   FastAPI Server  │  Spawns async subprocess
│   server/         │
└────────┬─────────┘
         │ python -m recipe_scraper.cli
         ▼
┌──────────────────┐     ┌─────────────────────┐
│   Web Scraper     │────▶│  HTML + Schema.org   │
│   web_scraper/    │     │  extraction          │
└────────┬─────────┘     └─────────────────────┘
         │ WebContent (title, text, images, structured_data)
         ▼
┌──────────────────────────────────────────────┐
│            Recipe Structurer                  │
│            recipe_structurer/                 │
│                                              │
│  Pass 1: LLM Preformat                      │
│    Raw text → annotated text with            │
│    «name» [english] {category} markers       │
│                                              │
│  Pass 1.5: CRF Ingredient Parsing           │
│    Annotated lines → Ingredient objects      │
│    (quantity, unit, name, preparation)        │
│                                              │
│  Pass 2: LLM DAG Generation                 │
│    Annotated text + ingredients → Recipe     │
│    (steps with uses/produces/requires)        │
│                                              │
│  Pydantic validation: graph integrity check  │
└────────┬─────────────────────────────────────┘
         │ Recipe (validated Pydantic model)
         ▼
┌──────────────────────────────────────────────┐
│            Recipe Enricher                    │
│            recipe_scraper/enrichment/         │
│                                              │
│  ┌─ Quantity Estimation (3-layer system)      │
│  ├─ Nutrition (unified index + embeddings)   │
│  ├─ Diet Detection (curated lists)           │
│  ├─ Season Detection (ADEME data)            │
│  └─ DAG Time Calculation (critical path)     │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│            Recipe Reviewer                    │
│            recipe_scraper/services/           │
│              recipe_reviewer.py               │
│                                              │
│  Adversarial LLM (different model) compares  │
│  structured output to original source text.  │
│  Auto-applies corrections to ingredients,    │
│  steps, and metadata.                        │
└────────┬─────────────────────────────────────┘
         │
         ▼
    {slug}.recipe.json + image
```

---

## 1. Recipe Importer (CLI Client)

**Location:** `recipe_importer/src/`

The importer is a standalone CLI tool that feeds URLs to the server API and tracks progress. It does not process recipes itself.

### Entry Point

```
python -m src.main url -f urls.json --concurrent 10
```

| Flag | Default | Description |
|------|---------|-------------|
| `-f` / `--file` | required | JSON file containing a list of URLs |
| `-c` / `--concurrent` | `10` | Max parallel imports |
| `-a` / `--api-url` | `http://localhost:3001` | Server base URL |
| `--auth` | `auth_presets.json` | Path to authentication presets |
| `--max-per-domain` | `8` | Max concurrent requests per domain |
| `--headless` | off | Disable Rich TUI, console-only output |
| `--clear` | off | Delete all recipes before import |

### How It Works

1. **Load URLs** from the JSON file (simple array of strings)
2. **Shuffle** URLs to spread load across domains
3. **Per-domain semaphore** limits concurrency to `--max-per-domain` per site
4. For each URL, `POST /api/recipes` with `{type: "url", url: "...", credentials: ...}`
5. **Stream progress** via Server-Sent Events (SSE), with polling fallback
6. **Retry** on server errors: `MAX_RETRIES = 2`, exponential backoff (`5s * attempt`)
7. **Stall detection**: if no new progress for 15 minutes, abort (no retry — subprocess may still run)
8. Display progress via Rich TUI (panels, progress bars, active recipe list)

### Authentication Presets

`auth_presets.json` maps domains to credentials (cookies, bearer tokens, API keys). Used for paywalled recipe sites. This file is gitignored.

```json
{
  "recipes.example.com": {
    "type": "cookie",
    "domain": ".recipes.example.com",
    "values": { "SESSION_ID": "abc123" }
  }
}
```

### Key Files

| File | Role |
|------|------|
| `main.py` | CLI entry point, argument parsing |
| `importer.py` | Orchestrates parallel imports with domain semaphores |
| `recipe_processors.py` | Retry logic, SSE streaming, polling, stall detection |
| `progress_tracker.py` | Rich TUI display, progress mapping |
| `api_client.py` | HTTP client for server API |
| `report.py` | Post-import summary report |

---

## 2. Server API

**Location:** `server/`

FastAPI application that receives import requests and spawns processing subprocesses.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/recipes` | Start recipe generation (URL, text, or image) |
| `GET` | `/api/recipes/progress/{id}` | Poll generation progress |
| `GET` | `/api/recipes/progress/{id}/stream` | SSE progress stream |
| `GET` | `/api/recipes` | List all recipes |
| `GET` | `/api/recipes/{slug}` | Get a single recipe |
| `POST` | `/api/recipes/manual` | Create recipe without generation |

### Recipe Generation Flow

When `POST /api/recipes` is called:

1. **Duplicate check**: in-memory URL index (`sourceUrl → slug`) rejects duplicates with HTTP 409
2. **Register progress**: creates a progress tracker with steps (`check_existence`, `scraping`, `structuring`, `enriching`, `saving`)
3. **Spawn subprocess**: `python -m recipe_scraper.cli --mode url --url <url> ...`
4. **Stream stdout**: parse subprocess output line by line, update progress steps
5. **Concurrency**: `asyncio.Semaphore(50)` limits total concurrent subprocesses

### Progress Tracking

The server maintains in-memory progress for each import:
- Steps have status (`pending`, `in_progress`, `completed`, `error`)
- SSE subscribers receive real-time updates via `asyncio.Queue`
- Polling clients get the latest state snapshot
- Keepalive pings every 15 seconds prevent SSE timeout
- Stale entries (completed/error with no active SSE listeners) are garbage-collected after 5 minutes

### Subprocess Safety

Each recipe import runs as a subprocess with a **600-second (10 min) hard timeout**. If a subprocess exceeds this limit, it is forcefully killed (`process.kill()`) to prevent resource leaks.

### Key Files

| File | Role |
|------|------|
| `api/routes/recipes.py` | Recipe CRUD + generation endpoints |
| `api/dependencies.py` | Singleton wiring (repository → service) |
| `repositories/recipe_repository.py` | Abstract storage interface (Repository Pattern) |
| `repositories/json_file_repository.py` | JSON-on-disk implementation (index, read/write, images) |
| `services/recipe_service.py` | Subprocess orchestration, progress management, access control |
| `services/progress_service.py` | In-memory progress store with SSE support |

> **Repository Pattern**: `RecipeService` never touches the filesystem directly.
> All data access goes through a `RecipeRepository` interface, injected via
> `dependencies.py`. The current implementation is `JsonFileRepository`.
> Swapping to SQLite or PostgreSQL only requires a new implementation and a
> one-line change in `dependencies.py`.

---

## 3. Web Scraper

**Location:** `server/packages/web_scraper/`

Fetches HTML from recipe URLs and extracts clean content.

### Scraping Strategy

1. **HTTP fetch** via `httpx.AsyncClient` (30s timeout, follows redirects)
2. **Schema.org extraction**: searches for `<script type="application/ld+json">` blocks containing `schema.org/Recipe` JSON-LD
3. **Text extraction** via [Trafilatura](https://trafilatura.readthedocs.io/) (extracts main article content, strips navigation/ads)
4. **Fallback**: if Trafilatura returns empty, falls back to BeautifulSoup `get_text()`
5. **Image extraction**: finds `<img>` tags in the article, validates each with a parallel HEAD request
6. **Title**: uses `name` from schema.org data if available, otherwise `<title>` tag

### Schema.org Handling

The scraper handles multiple JSON-LD structures found in the wild:

- Direct `{"@type": "Recipe", ...}`
- Array `[{"@type": "Recipe", ...}]`
- Graph `{"@graph": [{"@type": "Recipe", ...}]}`
- Composite `{"@type": ["Article", "Recipe"], ...}`

When found, the structured data is passed downstream to improve LLM input quality.

### Output Model

```python
class WebContent(BaseModel):
    title: str
    main_content: str
    image_urls: List[str]
    structured_data: Optional[Dict[str, Any]]  # schema.org/Recipe
```

---

## 4. Recipe Structurer

**Location:** `server/packages/recipe_structurer/`

Transforms raw text into a validated recipe DAG using a hybrid LLM + CRF approach.

### Pass 1: LLM Preformat

**Model:** DeepSeek V3.2 (via OpenRouter or direct API)

The first LLM call cleans and annotates the raw recipe text. When schema.org data is available, the structurer builds a pre-cleaned text from it, which significantly reduces LLM hallucination.

**Input:** Raw recipe text (or schema.org-derived text)

**Output:** Annotated text with markers:
```
INGREDIENTS:
- 200g «farine» [all-purpose flour] {pantry}
- 3 «œufs» [eggs] {egg}
- 100ml «lait» [milk] {dairy}

STEPS:
1. Mélanger la farine et les œufs
2. Ajouter le lait progressivement
...
```

The `«name»` markers preserve the original language, `[english]` provides the English name, and `{category}` assigns an ingredient category.

If the LLM determines the text is not a recipe, it responds with `REJECT:` and processing stops.

Pass 1 has **retry logic** (2 attempts with exponential backoff) and a **120-second timeout** per attempt. `REJECT:` responses are not retried — they indicate legitimate content rejection.

### Pass 1.5: CRF Ingredient Parsing

**Library:** [`ingredient-parser-nlp`](https://github.com/strangetom/ingredient-parser) (CRF-based)

After the LLM annotates ingredient lines, a Conditional Random Field model extracts structured data:

1. Parse each annotated line with regex to extract `«name»`, `[english]`, `{category}`
2. Feed the English name + quantity text to the CRF parser
3. CRF outputs: `quantity`, `unit`, `name`, `preparation`
4. Normalize units (e.g., "tablespoons" → "tbsp", "grammes" → "g")
5. Build `Ingredient` Pydantic objects with unique `id` (snake_case, suffixed `_2`, `_3` for duplicates)

Duplicate ingredients (e.g., butter used in two sub-recipes with different preparations) are kept separate to preserve distinct DAG references.

**Fallback:** If CRF parsing fails or returns no ingredients, the LLM-generated ingredients from Pass 2 are kept instead.

### Pass 2: LLM DAG Generation

**Model:** DeepSeek V3.2 (same provider as Pass 1)  
**Library:** [Instructor](https://github.com/jxnl/instructor) (structured output via function calling)

The second LLM call receives:
- The preformatted text from Pass 1
- The CRF-parsed ingredients as JSON
- A system prompt with the Recipe schema and a few-shot example

It generates:
- `steps[]` with `uses`, `produces`, `requires` fields forming a DAG
- `metadata` (title, servings, difficulty, recipeType, tags)
- `tools[]` (special equipment)
- `finalState` (the completed dish)

**Structured output** is enforced via Instructor, which validates the LLM response against the Pydantic `Recipe` model.

### Graph Validation

The `Recipe` Pydantic model includes a `@model_validator` that enforces 6 rules:

1. **Non-empty uses**: every step must reference ingredients or states (except equipment steps like "preheat oven")
2. **Valid references**: every `uses` reference must be an ingredient ID or a state produced by a previous step
3. **Valid requires**: every `requires` reference must be a state produced by a previous step
4. **No duplicate states**: each `produces` value must be unique
5. **No unused ingredients**: every non-optional ingredient must appear in at least one step's `uses`
6. **No orphan states**: every produced state must be consumed by a later step or be the `finalState`

If validation fails, the LLM is retried (up to 3 times via Instructor's `max_retries`).

### Pass 1.5b: Quantity Normalization (deterministic)

After CRF parsing, a deterministic post-processing layer (`normalize_quantity_post_crf`) fixes known CRF failure modes:

1. **Implicit quantities**: `unit=pinch, qty=None` → `qty=1, unit=pinch` (for all recognized units)
2. **Modifier extraction**: `unit="scant teaspoon"` → `qty=0.85, unit=tsp` (with calibrated multipliers: scant=0.85x, heaping=1.25x, big=1.5x, tiny=0.5x)
3. **Bare modifiers** (legacy): `unit="scant"` → `qty=0.85, unit=tsp`
4. **Plural normalization**: `drops → drop`, `thin slices → slice`

All corrections are tagged with `quantitySource: "inferred"` to distinguish them from explicitly stated quantities (`null` = exact from source) and LLM estimates (`"estimated"`).

### Post-Processing

After Pass 2, the system:

1. **Replaces** LLM ingredients with CRF-parsed ones (if CRF produced results)
2. **Deterministic ID resolution**: if a step references an unknown ID, a 3-step chain resolves it: exact match → suffix strip (`_N`) → original-language name lookup
3. **Drops** invalid references that can't be resolved
4. **Re-validates** the graph after corrections

### Key Files

| File | Role |
|------|------|
| `__init__.py` | `RecipeStructurer` class, schema.org text builder |
| `generator.py` | 3-pass pipeline orchestration, LLM client setup |
| `services/preformat.py` | Pass 1 LLM call |
| `services/ingredient_parser.py` | CRF parsing, regex extraction, fuzzy matching |
| `prompts/preformat.py` | System prompt for Pass 1 |
| `prompts/unified.py` | System prompt + few-shot example for Pass 2 |
| `models/recipe.py` | Pydantic models with graph validation |

---

## 5. Recipe Enricher

**Location:** `server/packages/recipe_scraper/src/recipe_scraper/recipe_enricher.py`

After structuring, the recipe is enriched with computed metadata. Most enrichment is deterministic. LLM calls are used only as last-resort fallbacks: weight estimation for unusual items, quantity estimation for ambiguous ingredients, and nutrition alias resolution.

Each enrichment sub-step is **fault-isolated**: diets, seasons, and DAG times run in individual `try/except` blocks with safe defaults. The async nutrition pipeline (matching + profile) is wrapped separately. A failure in any sub-step does not prevent the others from completing.

### Enrichment Architecture (Feb 2026)

The enrichment layer was refactored into a dedicated `enrichment/` subpackage:

```
recipe_scraper/enrichment/
├── __init__.py      # Orchestrator (enrich_recipe_async)
├── nutrition.py     # Weight estimation, quantity estimation, nutrition profiles
├── diet.py          # Diet detection (vegan, vegetarian, etc.)
├── seasons.py       # Seasonal classification (ADEME)
├── times.py         # DAG critical path computation
└── sanitize.py      # Post-enrichment cleanup
```

### 5.1 Quantity Estimation (3-layer system)

Quantities are resolved through 3 layers before nutrition is computed:

| Layer | Type | When | Tag |
|-------|------|------|-----|
| **Layer 0** | Prompt guidance | Pass 1 (preformat) | n/a |
| **Layer 1** | Deterministic rules | Pass 1.5b (post-CRF) | `quantitySource: "inferred"` |
| **Layer 2** | LLM with context | Enrichment | `quantitySource: "estimated"` |

**Layer 0**: Soft examples in the preformat prompt encourage the LLM to output explicit quantities (`"a pinch" → "1 pinch"`) and separate modifiers from units.

**Layer 1**: Deterministic post-processing in `ingredient_parser.py` (see Pass 1.5b above). Handles 94% of `qty=None` cases on the current corpus.

**Layer 2**: For residual `qty=None` ingredients, a lightweight LLM (`google/gemini-2.0-flash-001`) estimates quantities using recipe context (title, servings, recipe type). Results are cached in `resolved_ingredients.json`. Negligible ingredients (salt, pepper, herbs) are skipped.

This 3-layer approach avoids hallucination: deterministic methods resolve the vast majority, and the LLM only handles genuinely ambiguous cases with explicit provenance tracking.

### 5.2 Nutrition Calculation

**File:** `services/nutrition_matcher.py` + `enrichment/nutrition.py`  
**Embedding model:** BAAI/bge-small-en-v1.5 (local, via sentence-transformers)  
**Database:** Unified nutrition index (~10,800 foods with per-100g macros), merged in-memory from 3 sources:
- **OpenNutrition** (~5,300 entries) — USDA-derived baseline (ODbL)
- **CIQUAL 2025** (~3,300 entries) — French government food composition database (ANSES, Licence Ouverte)
- **MEXT Japan 7th** (~2,200 entries) — Japanese government food composition database (open)

Priority on duplicate English names: CIQUAL > OpenNutrition > MEXT. Each entry carries a `source` field for traceability. All matching is done on English names (`name_en`) regardless of recipe language.

For each ingredient:

1. **Skip** non-food items (parchment paper, skewers, toothpicks, etc.) and negligible items (salt, spices, herbs in small quantities)
2. **Match** the English name to the unified index using:
   - Exact name lookup (fast path, ~40,500 keys including alt names)
   - Semantic search via cosine similarity on BGE embeddings (threshold: 0.75)
   - Keyword validation to prevent false positives (e.g., "rice vinegar" must not match "rice")
3. **Estimate weight** in grams (resolution layers, first match wins):
   - Ingredient-specific portion weights from `portion_weights.json` (~1,465 entries from USDA FoodData Central)
   - Piece weights for count-based items (e.g., 1 egg = 50g, 1 apple = 180g)
   - Generic unit conversion as fallback (e.g., 1 tbsp = 15g for liquids)
   - LLM weight estimation for unusual items, cached in `weight_estimates_cache.json` (capped at 2000g max)
4. **Liquid retention heuristics**: large volumes of cooking liquids are not counted at 100%:
   - Discarded water (pasta water, blanching water): 0% retained
   - Frying oil (>400ml of neutral oil): 15% retained (USDA absorption factor)
   - Confit/rendering fat (duck fat, lard, >400ml): 20% retained
   - Alcohol (wine, beer, >250ml): 20% retained (evaporation)
   - Braising broth (>250ml, non-soup): 30% retained
   - Soup broth: 80% retained (broth IS the dish)
5. **Calculate** per-100g macros × estimated grams × retention factor / servings
6. **Servings sanity check**: if kcal/serving exceeds thresholds (1500 for desserts, 2000 for mains, 3000 absolute), attempt auto-correction by estimating realistic serving count (capped at 4× original)

**Extended macros**: In addition to the core 5 macros (calories, protein, fat, carbs, fiber), the pipeline computes **sugar** and **saturated fat** per serving from all 3 sources.

**Minerals**: 6 minerals are extracted per ingredient: **calcium**, **iron**, **magnesium**, **potassium**, **sodium**, **zinc** (all in mg). Sources: CIQUAL columns, MEXT columns, and USDA FDC API lookups for resolved ingredients. Minerals are only included in the recipe output when `mineralCoverage` ≥ 50% (i.e., at least half of the resolved ingredients contribute mineral data), ensuring displayed values are reliable.

**Confidence scoring** (based on resolution rate: resolved / total non-negligible):
- `high` (≥90%): reliable enough for meal planning
- `medium` (50–89%): displayed but flagged
- `low` (<50%): unreliable, not used in meal planner

**Issue tracking**: every unresolved ingredient is recorded with a reason (`no_translation`, `no_match`, `no_weight`) and stored in `metadata.nutritionIssues`. This enables systematic improvement of data files over time.

**Nutrition tags** are derived from per-serving values: `high-protein` (>20g), `low-calorie` (<400 kcal), `high-fiber` (>6g), `iron-rich` (≥5mg), `calcium-rich` (≥300mg), etc.

**Type coercion**: All quantity and servings values are defensively coerced to numeric types before any arithmetic. String values from legacy LLM structuring (e.g., `"null"`, `"~3"`, `"2 to 3"`, `"to taste"`) are handled by `fix_string_quantities.py` at the data level, and by runtime guards in `estimate_grams()` and `compute_nutrition_profile()` to prevent `TypeError` crashes.

### 5.3 Diet Detection

**File:** `recipe_enricher.py` (`_determine_diets`)  
**Data:** `data/diet_classification.json` (curated lists)

Diets are determined by checking ingredient `name_en` against curated lists:

| Diet | Excludes |
|------|----------|
| Vegan | meat, seafood, dairy, egg, honey, gelatin |
| Vegetarian | meat, seafood |
| Pescatarian | meat (but allows seafood) |
| Gluten-free | wheat, barley, rye, semolina, couscous, pasta, bread |

**Matching strategy:**
1. Word-boundary regex match against curated lists (primary source)
2. Fallback to LLM-assigned `category` field if no curated match found
3. Optional ingredients do not exclude a diet

### 5.4 Season Detection

**Data:** `data/seasonal_produce.json` (source: [ADEME Impact CO2](https://impactco2.fr/), Licence Ouverte 2.0)

Seasonal availability is determined for France:

1. Filter ingredients with category `produce`
2. Match each against the seasonal index (n-gram lookup, longest match first)
3. Skip year-round imports (bananas, lemons, avocados, etc.)
4. Intersect availability months across all seasonal ingredients
5. Map months to seasons: spring (Mar-May), summer (Jun-Aug), autumn (Sep-Nov), winter (Dec-Feb)
6. If no seasonal produce found, mark as `["all"]`

### 5.5 DAG Time Calculation

Times are computed from the step graph, not estimated by the LLM:

1. **Parse durations**: each step's ISO 8601 duration → minutes. Steps without duration get a 5-minute fallback (equipment steps get 0).
2. **Build graph**: `uses`/`produces`/`requires` relationships define dependencies between steps.
3. **Critical path**: dynamic programming computes `earliest_finish` for each step. The longest path through the DAG gives the wall-clock time.
4. **Active/passive split**: walk back the critical path, sum durations by `isPassive` flag.
5. **Cross-check**: if schema.org `totalTime` exists and diverges >30% from the DAG result, the schema.org time is used as ground truth.

**Output fields:**

| Field | Description |
|-------|-------------|
| `totalTime` | Wall-clock time (critical path) in ISO 8601 |
| `totalActiveTime` | Active time on critical path |
| `totalPassiveTime` | Passive time on critical path |
| `totalTimeMinutes` | Float convenience field |

---

## 6. Recipe Reviewer

**Location:** `server/packages/recipe_scraper/src/recipe_scraper/services/recipe_reviewer.py`

**Model:** Google Gemini 2.5 Flash via OpenRouter

The reviewer is an adversarial check using a **different LLM model** than the structurer. It compares the structured JSON against the original recipe text to catch errors:

- Missing or extra ingredients
- Wrong quantities or units
- Incorrect step descriptions
- Metadata issues (wrong servings, difficulty)
- Culinary incoherences

**Flow:**
1. Send the recipe JSON + source text (up to 24 000 chars) to Gemini
2. Receive structured corrections (JSON)
3. Auto-apply safe corrections (ingredient names, quantities, step text)
4. Skip time-related corrections (times are computed by the DAG, not the LLM)

The reviewer is non-blocking: if it fails or times out, the recipe is saved without review corrections.

---

## 7. Output Format

Each recipe is saved as `{slug}.recipe.json`. The slug is derived from the title (lowercased, hyphenated, ASCII-safe via `python-slugify`). If a file with the same slug already exists, a numeric suffix is appended (`-2`, `-3`, …) to prevent silent overwrites.

JSON files are written **atomically** (write to temp file, then `os.replace`) to prevent data corruption if the process crashes mid-write.

### Complete Structure

```jsonc
{
  "metadata": {
    "title": "Tarte Tatin",
    "description": "Classic French upside-down apple tart...",
    "servings": 8,
    "difficulty": "medium",              // "easy" | "medium" | "hard"
    "recipeType": "dessert",             // "appetizer" | "starter" | "main_course" | "dessert" | "drink" | "base"
    "totalTime": "PT1H45M",             // ISO 8601, computed from DAG
    "totalActiveTime": "PT45M",
    "totalPassiveTime": "PT1H",
    "totalTimeMinutes": 105.0,
    "totalActiveTimeMinutes": 45.0,
    "totalPassiveTimeMinutes": 60.0,
    "tags": ["french", "apple", "pastry"],
    "nationality": "French",
    "author": "Smitten Kitchen",
    "source": "smittenkitchen.com",
    "sourceUrl": "https://smittenkitchen.com/tarte-tatin",
    "image": "/images/tarte-tatin.jpg",
    "diets": ["vegetarian"],
    "seasons": ["autumn", "winter"],
    "nutritionPerServing": {
      "calories": 342.5,
      "protein": 3.2,
      "fat": 18.1,
      "carbs": 42.8,
      "fiber": 2.1,
      "sugar": 28.3,                     // grams per serving (from all 3 sources)
      "saturatedFat": 8.7,              // grams per serving
      "minerals": {                      // present only when mineralCoverage ≥ 0.5
        "calcium": 104,                  // mg per serving
        "iron": 4.88,
        "magnesium": 75,
        "potassium": 789,
        "sodium": 1580,
        "zinc": 3.62
      },
      "mineralCoverage": 0.75,          // ratio of resolved ingredients with mineral data
      "confidence": "high",              // "high" | "medium" | "low"
      "resolvedIngredients": 8,
      "matchedIngredients": 8,
      "totalIngredients": 8,
      "source": "opennutrition"
    },
    "nutritionTags": ["low-protein", "calcium-rich"],
    "nutritionIssues": [                 // Present only when issues exist
      {
        "ingredient": "truffle oil",
        "issue": "no_match",             // "no_translation" | "no_match" | "no_weight"
        "detail": "Not found in unified nutrition index"
      }
    ]
  },
  "ingredients": [
    {
      "id": "all_purpose_flour",
      "name": "farine",                   // Original language
      "name_en": "all-purpose flour",     // English translation
      "quantity": 250,                   // float | null (always numeric, never string)
      "unit": "g",
      "category": "grain",                // 16 categories (supermarket-aisle based)
      "preparation": null,
      "notes": null,
      "optional": false,
      "quantitySource": null              // null=exact | "inferred" | "estimated"
    }
  ],
  "tools": ["tarte tatin mold", "rolling pin"],
  "steps": [
    {
      "id": "make_caramel",
      "action": "Faire fondre le beurre et le sucre...",
      "duration": "PT15M",                // ISO 8601 or null
      "temperature": 180,                 // Celsius or null
      "stepType": "cook",                 // "prep" | "combine" | "cook" | "rest" | "serve"
      "isPassive": false,
      "subRecipe": "main",
      "uses": ["butter", "sugar"],         // Ingredient IDs or state IDs consumed
      "produces": "caramel",               // State created by this step
      "requires": [],                      // States needed but not consumed
      "visualCue": "amber colored"
    }
  ],
  "finalState": "tarte_tatin",
  "originalText": "...",                   // Raw scraped text (for debugging/review)
  "preformattedText": "..."               // LLM-annotated text from Pass 1
}
```

### Ingredient Categories

`meat`, `poultry`, `seafood`, `produce`, `dairy`, `egg`, `grain`, `legume`, `nuts_seeds`, `oil`, `herb`, `pantry`, `spice`, `condiment`, `beverage`, `other`

Categories are supermarket-aisle–based. Key distinctions:
- `herb` = fresh herbs only (basil, cilantro, parsley) — dried herbs go in `spice`
- `grain` = rice, pasta, flour, quinoa, oats, breadcrumbs
- `oil` = liquid fats (olive oil, vegetable oil); solid fats like butter go in `dairy`
- `pantry` = catch-all for shelf-stable items not in the above

### Step Types

| Type | Description |
|------|-------------|
| `prep` | Cutting, measuring, peeling |
| `combine` | Mixing, folding, whisking |
| `cook` | Any heat application |
| `rest` | Waiting, chilling, proofing |
| `serve` | Plating, garnishing |

### Graph Relationships

The step DAG is defined by three fields:

- **`uses`**: ingredient IDs or state IDs that this step consumes or transforms
- **`produces`**: a unique state ID created by this step (e.g., `caramelized_onions`)
- **`requires`**: state IDs that must exist but are not consumed (e.g., a preheated oven)

The frontend reconstructs the dependency graph from these relationships. Parallel tracks (e.g., making a sauce while cooking pasta) are naturally represented: steps with no shared dependencies can execute simultaneously.

---

## 8. Data Files Reference

All data files are in `server/packages/recipe_scraper/src/recipe_scraper/data/`.

| File | Description | Source | Size |
|------|-------------|--------|------|
| `seasonal_produce.json` | Vegetables/fruits with monthly availability | [ADEME Impact CO2](https://impactco2.fr/) (Licence Ouverte 2.0) | ~99 items |
| `diet_classification.json` | Curated ingredient lists per diet category | Hand-curated | 5 categories |
| `portion_weights.json` | Ingredient-specific unit-to-gram conversions | [USDA FoodData Central](https://fdc.nal.usda.gov/) (Foundation Foods + SR Legacy) | ~1,465 ingredients |
| `opennutrition_index.json` | Baseline food database with per-100g nutritional values | [OpenNutrition](https://github.com/nicholasgasior/opennutrition) (ODbL) | ~5,300 foods |
| `ciqual_index.json` | French food composition data (ANSES) | [CIQUAL 2025](https://ciqual.anses.fr/) (Licence Ouverte) | ~3,300 foods |
| `mext_index.json` | Japanese food composition data | [MEXT Japan 7th ed](https://www.mext.go.jp/en/policy/science_technology/policy/title01/detail01/1374030.htm) (open) | ~2,200 foods |
| `nutrition_embeddings.npy` | Pre-computed BGE-small embeddings for the unified food index | Computed locally (auto-recomputed on index change) | Binary |
| `nutrition_cache.json` | Cache of ingredient → nutrition matches | Auto-built | Grows over time |
| `nutrition_aliases_cache.json` | Maps unresolved ingredient names to USDA canonical names | Auto-built (LLM fallback) | ~800 entries |
| `weight_estimates_cache.json` | LLM-estimated weights for unusual unit/ingredient combos | Auto-built (LLM fallback, capped at 2000g) | Grows over time |
| `resolved_ingredients.json` | LLM quantity estimates with recipe context (Layer 2 cache) + USDA mineral data | Auto-built (Gemini Flash + USDA FDC API) | Grows over time |
| `qty_estimates_cache.json` | LLM-estimated quantities for ingredients missing qty+unit | Auto-built (Gemini Flash) | Grows over time |

---

## 9. LLM Usage Summary

| Stage | Model | Provider | Purpose | Output |
|-------|-------|----------|---------|--------|
| **Preformat** (Pass 1) | DeepSeek V3.2 | OpenRouter or direct | Clean & annotate raw text | Annotated text with `«»[]{}` markers |
| **DAG Generation** (Pass 2) | DeepSeek V3.2 | OpenRouter or direct | Generate recipe structure | `Recipe` Pydantic model (via Instructor) |
| **Review** | Gemini 2.5 Flash | OpenRouter | Adversarial quality check | Structured corrections |
| **Quantity estimation** (Layer 2) | Gemini 2.0 Flash | OpenRouter | Estimate missing ingredient quantities | `{qty, unit}` pairs |
| **Weight estimation** (fallback) | DeepSeek V3.2 | OpenRouter | Estimate grams for unusual items | `float` grams |
| **Nutrition alias** (fallback) | DeepSeek V3.2 | OpenRouter | Map unknown ingredients to USDA names | `string` canonical name |

The reviewer intentionally uses a **different model family** (Gemini vs. DeepSeek) to catch errors that the structurer's model might consistently make. The quantity estimator also uses Gemini to avoid reinforcing DeepSeek's biases from the structuring pass.

---

## 10. Configuration

### Environment Variables

| Variable | Required | Used by |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes (one of two) | Structurer, Enricher, Reviewer |
| `DEEPSEEK_API_KEY` | Yes (one of two) | Structurer (direct API, preferred if set) |
| `ADMIN_PASSWORD` | Optional | Server (admin login password) |

If both API keys are set, DeepSeek direct API is used for structuring (lower latency), and OpenRouter is used for everything else.

### Project Structure

```
recipe-display/
├── recipe_importer/          # CLI client for batch imports
│   └── src/
│       ├── main.py           # Entry point
│       ├── importer.py       # Parallel import orchestration
│       ├── recipe_processors.py  # Retry, SSE, polling
│       ├── progress_tracker.py   # Rich TUI
│       └── api_client.py     # HTTP client
│
├── server/                   # FastAPI backend
│   ├── api/
│   │   ├── routes/recipes.py     # Recipe endpoints
│   │   └── dependencies.py       # Singleton wiring
│   ├── repositories/
│   │   ├── recipe_repository.py  # Abstract storage interface
│   │   └── json_file_repository.py # JSON-on-disk implementation
│   ├── services/
│   │   ├── recipe_service.py     # Orchestration (uses repository)
│   │   └── progress_service.py   # SSE progress tracking
│   └── packages/
│       ├── web_scraper/      # HTML fetching & extraction
│       │   └── src/web_scraper/
│       │       ├── scraper.py    # Trafilatura + Schema.org
│       │       └── models.py     # WebContent, AuthPreset
│       │
│       ├── recipe_structurer/    # LLM + CRF structuring
│       │   └── src/recipe_structurer/
│       │       ├── __init__.py       # RecipeStructurer entry
│       │       ├── generator.py      # 3-pass pipeline
│       │       ├── models/recipe.py  # Pydantic models + validation
│       │       ├── services/
│       │       │   ├── preformat.py          # Pass 1
│       │       │   └── ingredient_parser.py  # Pass 1.5
│       │       └── prompts/
│       │           ├── preformat.py  # Pass 1 system prompt
│       │           └── unified.py    # Pass 2 system prompt
│       │
│       └── recipe_scraper/       # CLI + enrichment + review
│           └── src/recipe_scraper/
│               ├── cli.py                # CLI entry point
│               ├── scraper.py            # Orchestrator
│               ├── recipe_enricher.py    # Enrichment dispatcher
│               ├── enrichment/
│               │   ├── nutrition.py      # Weight/qty estimation, profiles
│               │   ├── diet.py           # Diet detection
│               │   ├── seasons.py        # Seasonal classification
│               │   ├── times.py          # DAG critical path
│               │   └── sanitize.py       # Post-enrichment cleanup
│               ├── services/
│               │   ├── nutrition_matcher.py       # BGE embeddings + unified index
│               │   ├── nutrition_resolver.py      # Ingredient resolution pipeline
│               │   └── recipe_reviewer.py         # Gemini review
│               └── data/
│                   ├── seasonal_produce.json
│                   ├── diet_classification.json
│                   ├── portion_weights.json
│                   ├── opennutrition_index.json
│                   ├── ciqual_index.json
│                   ├── mext_index.json
│                   ├── nutrition_embeddings.npy
│                   └── resolved_ingredients.json
│
├── server/scripts/              # Maintenance & audit tools
│   ├── nutrition_healthcheck.py # Fast nutrition gaps report (~15s, no LLM)
│   ├── re_enrich_nutrition.py   # Re-compute nutrition for all recipes (no LLM)
│   ├── fix_servings.py          # Auto-correct suspect serving counts
│   ├── fix_string_quantities.py # Coerce string quantities/servings to proper types
│   ├── build_usda_portions_index.py  # USDA FoodData Central import
│   ├── import_nutrition_sources.py   # CIQUAL + MEXT import
│   ├── backfill_resolved_minerals.py # Fetch minerals from USDA FDC API for resolved ingredients
│   ├── backfill_minerals_fast.py     # Cross-reference OpenNutrition → CIQUAL for minerals
│   ├── nutrition_audit.py       # Deep cross-validation via NutritionAgent
│   └── score_random_recipes.py  # Sample and score random recipes
│
└── client/                   # React frontend (Vite + MUI)
```

---

## 11. Known Limitations & Quality Metrics

This section documents the **honest state** of the pipeline. All numbers are from a full audit on **5,489 recipes** (Feb 24, 2026).

### Corpus Overview

| Metric | Value |
|--------|-------|
| Total recipes | 5,489 |
| Total ingredients | ~64,000 |
| Total steps | ~49,600 |
| Languages | English 90.2%, French 9.8% |
| Legacy recipes (single-pass LLM, no CRF) | 100% |
| 3-pass pipeline recipes (preformat+CRF+DAG) | 0% (pipeline ready, not yet re-imported) |

> **Note:** All existing recipes were generated by a legacy single-pass LLM pipeline. The current 3-pass pipeline (preformat → CRF → DAG) has been implemented and tested but requires a full re-import to take effect. Re-importing will activate the CRF ingredient parser, the 3-layer quantity normalization, and the `quantitySource` provenance tracking.

### Metadata Completeness

| Field | Coverage | Notes |
|-------|----------|-------|
| title | 99.98% | 1 missing |
| recipeType | 99.91% | 5 missing |
| servings | 99.87% | 7 missing; 412 (7.5%) have servings=1 |
| difficulty | 99.27% | 40 missing |
| sourceUrl | 99.3% | |
| image | 99.5% | |
| tags | 99.9% | |
| nationality | 38.9% | Under-detected (improvement candidate) |
| diets | 100.0% | |
| seasons | 100.0% | |
| totalTime (from DAG) | 99.98% | 1 missing |

### Nutrition Accuracy

| Metric | Value | Notes |
|--------|-------|-------|
| Recipes with nutrition data | 99.96% | 2 recipes with 0 kcal |
| **High confidence (≥90% resolved)** | **69.1%** | Reliable for meal planning |
| Medium confidence (50–89%) | 30.0% | Displayed but flagged |
| Low confidence (<50%) | 0.8% | Unreliable |
| Median kcal/serving | 416 | Reasonable for a mixed recipe corpus |
| P5–P95 range | 109–1,049 kcal | |

### Ingredient Quality

| Metric | Value | Notes |
|--------|-------|-------|
| Missing `name_en` | 0 (0%) | All ingredients have English translations |
| `qty=null, unit=null` | 11,072 | Expected: "to taste", spices, herbs |
| `qty=null, unit!=null` | 854 | **The problem** — addressed by 3-layer system |
| Has `quantitySource` tracking | 0 | Pending re-import |

Of the 854 problematic `qty=null, unit!=null` cases:
- **94.0%** (803) will be fixed by Layer 1 (deterministic rules) on re-import
- **2.3%** (20) are nutritionally negligible (salt, pepper)
- **3.6%** (31) will fall to Layer 2 (LLM estimation with context)

### Step Quality

| Metric | Value | Notes |
|--------|-------|-------|
| Steps without duration | 61.3% | Legacy LLM did not always generate durations |
| Steps with visual cues | 41.3% | |
| Step types | cook 28%, prep 27%, combine 27%, serve 12%, rest 7% | Balanced distribution |

> **Duration gap** is the single largest quality deficit. The current 3-pass pipeline generates durations more reliably via the DAG prompt. Re-import will reduce this significantly, but some steps (serve, garnish) legitimately have no duration.

### Root Causes of Remaining Inaccuracy

1. **Missing step durations (61.3%)**: The legacy LLM often omitted ISO 8601 durations. Steps without durations receive a 5-minute fallback, which inflates total time for simple steps and underestimates complex ones. **Fixed by re-import** via the new DAG prompt.

2. **`qty=null` with unit (854 occurrences)**: Implicit quantities ("a pinch", "a handful") not parsed by the legacy LLM. **Fixed by 3-layer system** (Layer 1 handles 94%, Layer 2 catches the rest).

3. **Nationality under-detected (38.9%)**: The legacy prompt did not consistently extract nationality. **Partially fixable** via the improved preformat prompt or a dedicated enrichment step.

4. **Servings=1 (7.5%)**: Some recipes legitimately serve 1 (single-serving smoothies, etc.), but others may be mis-parsed. A servings sanity-check script (`fix_servings.py`) exists and has corrected extreme cases.

### Improvement History

| Date | Change | Impact |
|------|--------|--------|
| Baseline | Initial nutrition system | 40.6% high confidence |
| +Frying oil/confit retention | 15%/20% retention heuristics for cooking fats | Reduced calorie outliers |
| +Weight cache fixes | Corrected aberrant LLM estimates (tortillas 280→45g) | Reduced P95 kcal |
| +Sauce whitelist | Unblocked standard sauces from composite filter | +5% high confidence |
| +LLM alias cache | ~300 previously unmatched ingredients resolved | +2% high confidence |
| +3-source nutrition index | CIQUAL 2025 + MEXT Japan added to OpenNutrition baseline | +15% high confidence |
| +USDA portion weights | 1,465 ingredient-specific unit-to-gram conversions | Better weight accuracy |
| +Servings auto-correction | LLM-based servings fix for outliers | Reduced false calorie outliers |
| +3-layer quantity system | Deterministic + LLM quantity estimation with provenance | 854 qty gaps resolved |
| +Sugar & saturated fat | Extended macros from all 3 nutrition sources | 100% recipes covered |
| +Minerals (Ca, Fe, Mg, K, Na, Zn) | CIQUAL + MEXT columns + USDA FDC API backfill | 40% recipes (coverage ≥50%) |
| +String quantity coercion | Fixed 605 string quantities + 116 string servings in data + runtime guards | 0 errors on re-enrichment |
| **Current (Feb 2026)** | All improvements combined | **69.1% high, 30.0% medium, 0.8% low** |

### What the Pipeline Cannot Do

- **Cooking loss**: the system does not model water evaporation or nutrient degradation during cooking. Raw ingredient macros are used as-is.
- **Absorption rates**: frying oil and confit fat use fixed retention factors (15% and 20%). Real absorption depends on food surface area, temperature, and time.
- **Serving size from source**: if the original recipe says "serves 4" but really feeds 8, nutrition will be inflated. The auto-correction heuristic catches extreme cases.
- **Yield tracking**: the system does not model dough rising, sauce reduction, or other volume changes that affect final portion sizes.

### Maintenance Scripts

```bash
# Quick nutrition healthcheck (~15s, no LLM calls)
cd server && poetry run python scripts/nutrition_healthcheck.py

# Re-compute nutrition for all recipes using latest data files (~2.5 min, no LLM calls)
cd server && poetry run python scripts/re_enrich_nutrition.py --all

# Fix suspect servings via LLM (one-shot)
cd server && poetry run python scripts/fix_servings.py

# Fix string quantities/servings in recipe JSONs (one-shot, idempotent)
cd server && poetry run python -m scripts.fix_string_quantities        # apply
cd server && poetry run python -m scripts.fix_string_quantities --dry-run  # preview

# Build USDA portions index from FoodData Central
cd server && poetry run python scripts/build_usda_portions_index.py

# Import CIQUAL/MEXT sources
cd server && poetry run python scripts/import_nutrition_sources.py --ciqual-xml --mext-xlsx

# Deep audit via NutritionAgent (slower, deterministic cross-validation)
cd server && poetry run python scripts/nutrition_audit.py
```

The healthcheck generates `server/data/nutrition_gaps.json` — a machine-readable report of all unresolved ingredients, prioritized by frequency. Use this to decide which data files to improve first.

### Data Quality Feedback Loop

The pipeline implements a self-improving data loop:

1. **During enrichment**: ingredients that can't be matched are tracked in `metadata.nutritionIssues`
2. **Gaps report**: `nutrition_healthcheck.py` aggregates all gaps across the corpus
3. **Cache files**: `nutrition_aliases_cache.json`, `weight_estimates_cache.json`, and `resolved_ingredients.json` grow over time, reducing LLM calls for known ingredients
4. **Re-enrichment**: `re_enrich_nutrition.py` propagates any data file improvement to all existing recipes without re-scraping or re-structuring
5. **Quantity provenance**: `quantitySource` field enables filtering recipes by data quality tier
