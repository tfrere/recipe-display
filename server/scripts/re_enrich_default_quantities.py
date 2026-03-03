"""
Re-enrich nutrition for all recipes to apply default quantities.

Only recomputes nutritionPerServing — does NOT touch servings, title, steps, etc.
Preserves servingsCorrected flags from fix_servings.py.

Usage:
    python -m scripts.re_enrich_default_quantities [--dry-run] [--limit N]
"""

import json
import logging
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SERVER_ROOT / "packages" / "recipe_scraper" / "src"))

from recipe_scraper.enrichment.nutrition import (
    compute_nutrition_profile,
    derive_nutrition_tags,
)
from recipe_scraper.services.nutrition_matcher import NutritionMatcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RECIPES_DIR = SERVER_ROOT / "data" / "recipes_old"


def main():
    dry_run = "--dry-run" in sys.argv
    limit = 0
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        limit = int(sys.argv[idx + 1])

    matcher = NutritionMatcher()
    paths = sorted(RECIPES_DIR.glob("*.recipe.json"))
    if limit:
        paths = paths[:limit]

    logger.info(f"Re-enriching {len(paths)} recipes (dry_run={dry_run})")

    changed = 0
    unchanged = 0
    errors = 0

    for path in paths:
        try:
            with open(path) as f:
                recipe = json.load(f)

            ingredients = recipe.get("ingredients", [])
            if not ingredients:
                continue

            meta = recipe.get("metadata", {})
            servings = meta.get("servings", 1)
            old_nps = meta.get("nutritionPerServing", {})
            old_cal = old_nps.get("calories", 0) if old_nps else 0

            names_en = [
                ing.get("name_en", "") for ing in ingredients if ing.get("name_en")
            ]
            nutrition_data = matcher.match_batch(names_en)

            profile = compute_nutrition_profile(
                ingredients, nutrition_data, servings, meta
            )

            new_cal = profile.get("calories", 0)
            delta = abs(new_cal - old_cal)

            if delta < 1:
                unchanged += 1
                continue

            title = meta.get("title", path.stem)

            if dry_run:
                logger.info(
                    f"  [DRY] {title}: {old_cal:.0f} → {new_cal:.0f} kcal/srv "
                    f"(+{delta:.0f})"
                )
            else:
                nutrition_issues = profile.pop("issues", [])
                meta["nutritionPerServing"] = profile
                if nutrition_issues:
                    meta["nutritionIssues"] = nutrition_issues
                else:
                    meta.pop("nutritionIssues", None)

                tags = derive_nutrition_tags(profile)
                meta["nutritionTags"] = tags

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(recipe, f, indent=2, ensure_ascii=False)
                logger.info(
                    f"  {title}: {old_cal:.0f} → {new_cal:.0f} kcal/srv (+{delta:.0f})"
                )

            changed += 1

        except Exception as e:
            logger.error(f"  Error {path.stem}: {e}")
            errors += 1

    logger.info(
        f"\nDone: {changed} changed, {unchanged} unchanged, {errors} errors"
    )


if __name__ == "__main__":
    main()
