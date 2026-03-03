"""
Backfill script: resolve all not_found ingredients in the nutrition cache.

Reads nutrition_cache.json, extracts non-composite not_found entries,
runs them through NutritionResolver (USDA -> Perplexity), and saves
resolved entries to resolved_ingredients.json.

After this script, run `python -m scripts.re_enrich_nutrition --all`
to recompute nutrition profiles for all recipes.

Usage:
    python -m scripts.backfill_nutrition_resolver [--dry-run] [--limit N]
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SERVER_ROOT / "packages" / "recipe_scraper" / "src"))

from dotenv import load_dotenv

load_dotenv(SERVER_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CACHE_FILE = (
    SERVER_ROOT
    / "packages"
    / "recipe_scraper"
    / "src"
    / "recipe_scraper"
    / "data"
    / "nutrition_cache.json"
)


def load_not_found_names() -> list[str]:
    """Extract non-composite not_found entries from the cache."""
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)

    names = []
    for key, entry in cache.items():
        if key.startswith("_"):
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("not_found") and entry.get("reason") != "composite":
            names.append(key)

    return sorted(names)


async def run_backfill(names: list[str], dry_run: bool = False) -> None:
    from recipe_scraper.services.nutrition_resolver import NutritionResolver

    resolver = NutritionResolver()

    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Backfilling {len(names)} not_found ingredients")

    if dry_run:
        from recipe_scraper.services.nutrition_resolver import _is_garbage
        garbage = [n for n in names if _is_garbage(n)]
        real = [n for n in names if not _is_garbage(n)]
        logger.info(f"  Garbage (will skip): {len(garbage)}")
        logger.info(f"  Real ingredients to resolve: {len(real)}")
        for name in real[:20]:
            logger.info(f"    - {name}")
        if len(real) > 20:
            logger.info(f"    ... and {len(real) - 20} more")
        return

    results = await resolver.resolve_batch(names)

    resolved = sum(1 for v in results.values() if v is not None)
    failed = sum(1 for v in results.values() if v is None)

    logger.info(f"\nBackfill complete:")
    logger.info(f"  Resolved: {resolved}")
    logger.info(f"  Failed:   {failed}")
    logger.info(f"  Total:    {len(results)}")

    if resolved > 0:
        usda = sum(
            1 for v in results.values()
            if v is not None and v.get("source") == "usda"
        )
        ppx = sum(
            1 for v in results.values()
            if v is not None and v.get("source") == "perplexity"
        )
        logger.info(f"  USDA:     {usda}")
        logger.info(f"  Perplexity: {ppx}")
        logger.info(
            "\nNext step: python -m scripts.re_enrich_nutrition --all"
        )


def main():
    dry_run = "--dry-run" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    names = load_not_found_names()
    logger.info(f"Found {len(names)} not_found entries in cache")

    if limit:
        names = names[:limit]
        logger.info(f"Limited to {limit} entries")

    asyncio.run(run_backfill(names, dry_run=dry_run))


if __name__ == "__main__":
    main()
