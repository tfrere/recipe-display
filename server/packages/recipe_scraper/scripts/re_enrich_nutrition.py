"""
Re-enrich all existing recipes with updated nutrition data.

This script re-runs the async nutrition enrichment pipeline on all
.recipe.json files, applying the latest heuristics (liquid retention, etc.).

Usage:
    cd server/packages/recipe_scraper
    poetry run python scripts/re_enrich_nutrition.py
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Locate the recipes directory
# scripts/ -> recipe_scraper/ -> packages/ -> server/ -> data/recipes
_RECIPES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "recipes"


async def re_enrich_all():
    """Re-enrich all recipes with nutrition data (async)."""
    from recipe_scraper.recipe_enricher import RecipeEnricher

    enricher = RecipeEnricher()

    if not _RECIPES_DIR.exists():
        logger.error(f"Recipes directory not found: {_RECIPES_DIR}")
        return

    recipe_files = sorted(_RECIPES_DIR.glob("*.recipe.json"))
    logger.info(f"Found {len(recipe_files)} recipes in {_RECIPES_DIR}")

    results = []
    start_time = time.time()

    for i, recipe_file in enumerate(recipe_files, 1):
        logger.info(f"\n[{i}/{len(recipe_files)}] {recipe_file.name}")

        try:
            with open(recipe_file, "r", encoding="utf-8") as f:
                recipe_data = json.load(f)

            title = recipe_data.get("metadata", {}).get("title", recipe_file.stem)
            old_cal = recipe_data.get("metadata", {}).get("nutritionPerServing", {}).get("calories", "N/A")

            # Run full async enrichment (includes nutrition)
            enriched = await enricher.enrich_recipe_async(recipe_data)

            new_profile = enriched.get("metadata", {}).get("nutritionPerServing", {})
            new_cal = new_profile.get("calories", "N/A")
            liquid_adj = new_profile.get("liquidRetentionApplied", False)

            results.append({
                "title": title,
                "old_cal": old_cal,
                "new_cal": new_cal,
                "liquid_adjusted": liquid_adj,
                "tags": enriched.get("metadata", {}).get("nutritionTags", []),
            })

            # Save enriched recipe
            with open(recipe_file, "w", encoding="utf-8") as f:
                json.dump(enriched, f, ensure_ascii=False, indent=2)

            marker = " [LIQUID ADJ]" if liquid_adj else ""
            logger.info(f"  {title}: {old_cal} -> {new_cal} kcal{marker}")

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            results.append({
                "title": recipe_file.stem,
                "error": str(e),
            })

    elapsed = time.time() - start_time

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Re-enrichment complete in {elapsed:.0f}s")
    logger.info(f"{'='*60}")
    logger.info(f"{'Recipe':<45} {'Before':>8} {'After':>8} {'Liquid':>6}")
    logger.info(f"{'-'*45} {'-'*8} {'-'*8} {'-'*6}")

    for r in results:
        if "error" in r:
            logger.info(f"{r['title']:<45} {'ERROR':>8}")
            continue
        liq = "Yes" if r.get("liquid_adjusted") else ""
        logger.info(f"{r['title']:<45} {str(r['old_cal']):>8} {str(r['new_cal']):>8} {liq:>6}")


def main():
    """Entry point."""
    # Load env files (try multiple locations)
    load_dotenv()
    load_dotenv("../../.env")
    # scripts/ -> recipe_scraper/ -> packages/ -> server/.env
    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

    asyncio.run(re_enrich_all())


if __name__ == "__main__":
    main()
