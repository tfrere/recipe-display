# Data Sources

This document lists all external data sources used in the project, their licenses, and where they are used.

## Seasonal Produce

| Field | Value |
|---|---|
| **Source** | ADEME Impact CO2 (https://impactco2.fr/api/v1/fruitsetlegumes) |
| **License** | Licence Ouverte 2.0 (Etalab) |
| **File** | `server/packages/recipe_scraper/src/recipe_scraper/data/seasonal_produce.json` |
| **Content** | 99 fruits and vegetables with monthly availability in France |
| **Used by** | `recipe_enricher.py` — seasonal classification of recipes |
| **Last updated** | 2026-02-16 |

Additional produce entries (wild mushrooms, fresh herbs, forgotten vegetables) were added manually based on:
- Atlas des Champignons (https://www.atlas-des-champignons.com/calendrier-de-cueillette/)
- Calendrier des herbes aromatiques (https://quandplanter.fr/calendrier-aromatiques)

## Nutrition Data

| Field | Value |
|---|---|
| **Source** | OpenNutrition (https://www.opennutrition.app/) |
| **License** | ODbL (Open Database License) |
| **Files** | `server/packages/recipe_scraper/src/recipe_scraper/data/opennutrition_index.json` (5,299 entries), `opennutrition_embeddings.npy` (pre-computed BGE-small vectors) |
| **Content** | Food items with macros per 100g (kcal, protein, fat, carbs, fiber, sugar, saturated fat) aggregated from USDA, CNF, FRIDA, AUSNUT |
| **Used by** | `nutrition_matcher.py` — ingredient-to-nutrition matching via exact lookup + BGE-small embeddings |
| **Last updated** | 2026-02-09 |

The OpenNutrition dataset is also available as a MCP server: https://github.com/deadletterq/mcp-opennutrition (GPL-3.0).

## Ingredient Translation

| Field | Value |
|---|---|
| **Source** | Custom dictionary + LLM fallback |
| **License** | Project-internal |
| **File** | `server/packages/recipe_scraper/src/recipe_scraper/data/ingredient_translations.json` |
| **Content** | French-to-English ingredient name mappings |
| **Used by** | `ingredient_translator.py` — translates ingredient names before nutrition matching |
| **Last updated** | 2026-02-13 |

## Nutrition Cache

| Field | Value |
|---|---|
| **Source** | Generated at runtime |
| **License** | Derived from OpenNutrition (ODbL) |
| **File** | `server/packages/recipe_scraper/src/recipe_scraper/data/nutrition_cache.json` |
| **Content** | Cached results from BGE-small embedding matches against the OpenNutrition index |
| **Used by** | `nutrition_matcher.py` — avoids re-computing embeddings for already-matched ingredients |

## LLM Providers

| Provider | Model | Used for | API |
|---|---|---|---|
| DeepSeek | deepseek-v3.2 | Recipe structuring (Pass 1 + Pass 2) | Via OpenRouter |
| Google | gemini-2.5-flash | Recipe review (Pass 3) + Review Agent | Via OpenRouter |
| BAAI | bge-small-en-v1.5 | Nutrition embedding matching | Local (sentence-transformers) |

## Embedding Model

| Field | Value |
|---|---|
| **Source** | HuggingFace (https://huggingface.co/BAAI/bge-small-en-v1.5) |
| **License** | MIT |
| **Used by** | `nutrition_matcher.py` — encodes ingredient names for semantic search against OpenNutrition index |
| **Size** | 33M parameters, 384-dim embeddings |

## Macronutrient Reference Ranges

The Meal Planner uses macronutrient distribution ranges to evaluate meal balance.

| Source | Protein | Carbs | Fat | Notes |
|---|---|---|---|---|
| **ANSES (France, 2016)** | 10-20% | 40-55% | 35-40% | Primary reference (French audience) |
| IOM/USDA AMDR | 10-35% | 45-65% | 20-35% | US reference, broader ranges |
| EFSA (Europe) | ~10-15% | ~52% | ~31.5% | Based on labelling RIs |
| WHO/OMS | — | — | <= 30% | Focus on fat quality, not strict ranges |

The app uses **ANSES values** as default, with ideal targets at the midpoint of each range.
See `MacroBalanceBar.jsx` for implementation details.

References:
- ANSES: https://anses.fr/fr/content/l%E2%80%99anses-actualise-les-rep%C3%A8res-de-consommations-alimentaires-pour-la-population-fran%C3%A7aise
- IOM AMDR: https://nap.nationalacademies.org/catalog/10490
- EFSA DRV: https://efsa.europa.eu/en/topics/topic/dietary-reference-values
- WHO: https://www.who.int/news/item/17-07-2023-who-updates-guidelines-on-fats-and-carbohydrates
