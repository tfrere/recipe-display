"""
Pre-fetch USDA FoodData Central nutrition data for all known ingredients.

Reads the ingredient translation dictionary and looks up each English
ingredient name in the USDA FDC API, populating the local cache.

Usage:
    cd server/packages/recipe_scraper
    poetry run python scripts/prefetch_nutrition_cache.py

This can be re-run periodically to refresh the cache or after adding
new ingredients to the translation dictionary.
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

# Paths
_DATA_DIR = Path(__file__).parent.parent / "src" / "recipe_scraper" / "data"
_TRANSLATIONS_FILE = _DATA_DIR / "ingredient_translations.json"


async def prefetch():
    """Fetch nutrition data for all translated ingredients."""
    from recipe_scraper.services.nutrition_lookup import NutritionLookup

    # Load translations
    with open(_TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract unique English ingredient names
    english_names = sorted(set(
        v for k, v in data.items()
        if not k.startswith("_") and isinstance(v, str) and v
    ))

    logger.info(f"Found {len(english_names)} unique English ingredient names")

    lookup = NutritionLookup()

    # Check how many are already cached
    already_cached = sum(1 for name in english_names if lookup.get_cached(name) is not None)
    to_fetch = len(english_names) - already_cached
    logger.info(f"Already cached: {already_cached}, to fetch: {to_fetch}")

    if to_fetch == 0:
        logger.info("All ingredients already cached. Nothing to do.")
        return

    # Fetch missing ingredients
    fetched = 0
    failed = 0
    start_time = time.time()

    for i, name in enumerate(english_names, 1):
        # Skip if already cached
        if lookup.get_cached(name) is not None:
            continue

        logger.info(f"[{i}/{len(english_names)}] Looking up: '{name}'")
        result = await lookup.lookup_ingredient(name)

        if result and not result.get("not_found"):
            fetched += 1
            kcal = result.get("energy_kcal", "?")
            desc = result.get("fdc_description", "")[:50]
            logger.info(f"  -> {kcal} kcal/100g ({desc})")
        else:
            failed += 1
            logger.warning(f"  -> NOT FOUND")

        # Rate limiting: USDA allows 1000 req/hour = ~1 req/3.6s
        # Be conservative: 1 request per second
        await asyncio.sleep(1.0)

    # Save cache
    lookup.save_cache()

    elapsed = time.time() - start_time
    logger.info(f"\nDone in {elapsed:.0f}s")
    logger.info(f"Fetched: {fetched}, Not found: {failed}, Total cached: {len(lookup._cache)}")


def main():
    """Entry point."""
    load_dotenv()
    load_dotenv("../../.env")
    load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

    asyncio.run(prefetch())


if __name__ == "__main__":
    main()
