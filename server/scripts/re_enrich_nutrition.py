"""
Re-enrich nutrition for outlier recipes using updated portion_weights.json.

This script re-computes nutrition locally without LLM calls:
  1. Re-runs estimate_grams with updated USDA portion data
  2. Re-matches ingredients against nutrition DB
  3. Recomputes nutritionPerServing

Usage:
    python -m scripts.re_enrich_nutrition [--all] [--dry-run]
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add server packages to path
SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SERVER_ROOT / "packages" / "recipe_scraper" / "src"))

from recipe_scraper.recipe_enricher import RecipeEnricher
from recipe_scraper.services.nutrition_matcher import NutritionMatcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RECIPES_DIR = SERVER_ROOT / "data" / "recipes"
HIGH_KCAL_THRESHOLD = 1500


def find_outlier_recipes() -> list[tuple[Path, str]]:
    """Find recipes with suspicious nutrition (>1500 kcal/srv or missing)."""
    outliers = []
    for path in sorted(RECIPES_DIR.glob("*.recipe.json")):
        with open(path) as f:
            recipe = json.load(f)

        nps = recipe.get("metadata", {}).get("nutritionPerServing", {})
        kcal = nps.get("calories", 0) if nps else 0
        title = recipe.get("metadata", {}).get("title", path.stem)

        if kcal > HIGH_KCAL_THRESHOLD or kcal == 0 or not nps:
            reason = f"{kcal:.0f} kcal/srv" if kcal > 0 else "no nutrition"
            outliers.append((path, reason))

    return outliers


def re_enrich_recipe(recipe: dict, enricher: RecipeEnricher, matcher: NutritionMatcher) -> dict:
    """Re-compute nutrition for a single recipe (no LLM calls)."""
    ingredients = recipe.get("ingredients", [])
    if not ingredients:
        return recipe

    weight_cache = enricher._load_weight_cache()

    for ing in ingredients:
        name_en = ing.get("name_en", "")
        if not name_en:
            continue
        quantity = ing.get("quantity")
        unit = ing.get("unit")
        grams = NutritionMatcher.estimate_grams(quantity, unit, name_en)
        if grams is not None:
            ing["estimatedWeightGrams"] = round(grams, 1)
        elif quantity is not None:
            cache_key = RecipeEnricher._weight_cache_key(unit, name_en)
            per_unit = weight_cache.get(cache_key)
            if per_unit is not None:
                ing["estimatedWeightGrams"] = round(quantity * per_unit, 1)

    # Re-match ingredients against nutrition DB
    names_en = [ing.get("name_en", "") for ing in ingredients if ing.get("name_en")]
    nutrition_data = matcher.match_batch(names_en)

    # Re-compute nutrition profile
    servings = recipe.get("metadata", {}).get("servings", 1)
    metadata = recipe.get("metadata", {})
    profile = enricher._compute_nutrition_profile(
        ingredients, nutrition_data, servings, metadata
    )

    nutrition_issues = profile.pop("issues", [])
    recipe["metadata"]["nutritionPerServing"] = profile
    if nutrition_issues:
        recipe["metadata"]["nutritionIssues"] = nutrition_issues
    else:
        recipe["metadata"].pop("nutritionIssues", None)

    # Re-derive nutrition tags
    tags = enricher._derive_nutrition_tags(profile)
    recipe["metadata"]["nutritionTags"] = tags

    # Clean up previous auto-fix flags
    recipe["metadata"].pop("servingsSuspect", None)
    recipe["metadata"].pop("servingsOriginal", None)

    # Servings sanity check (mirrors enrich_recipe_async logic)
    cal_per_serving = profile.get("calories", 0)
    current_servings = recipe.get("metadata", {}).get("servings", 1)
    recipe_type = recipe.get("metadata", {}).get("recipeType", "")
    kcal_threshold = 2000 if recipe_type == "main_course" else 1500
    _EXTREME_THRESHOLD = 3000
    _MAX_MULTIPLIER = 4

    needs_fix = (
        isinstance(current_servings, (int, float))
        and (
            (current_servings <= 2 and cal_per_serving > kcal_threshold)
            or cal_per_serving > _EXTREME_THRESHOLD
        )
    )

    if needs_fix and current_servings > 0:
        raw_estimate = round(cal_per_serving * current_servings / 500)
        estimated_servings = min(
            max(4, raw_estimate),
            current_servings * _MAX_MULTIPLIER,
        )
        ratio = current_servings / estimated_servings
        recipe["metadata"]["servingsOriginal"] = current_servings
        recipe["metadata"]["servingsSuspect"] = True
        recipe["metadata"]["servings"] = estimated_servings
        for macro in ("calories", "protein", "fat", "carbs", "fiber"):
            if macro in profile:
                profile[macro] = round(profile[macro] * ratio, 1)
        recipe["metadata"]["nutritionPerServing"] = profile
        tags = enricher._derive_nutrition_tags(profile)
        recipe["metadata"]["nutritionTags"] = tags

    return recipe


def main():
    dry_run = "--dry-run" in sys.argv
    do_all = "--all" in sys.argv

    if do_all:
        targets = [(p, "re-enrich all") for p in sorted(RECIPES_DIR.glob("*.recipe.json"))]
        logger.info(f"Re-enriching ALL {len(targets)} recipes")
    else:
        targets = find_outlier_recipes()
        logger.info(f"Found {len(targets)} outlier recipes")

    if not targets:
        logger.info("No outliers found!")
        return

    enricher = RecipeEnricher()
    matcher = NutritionMatcher()

    updated = 0
    errors = 0

    for path_or_tuple in targets:
        if isinstance(path_or_tuple, tuple):
            path, reason = path_or_tuple
        else:
            path, reason = path_or_tuple, ""

        try:
            with open(path) as f:
                recipe = json.load(f)

            title = recipe.get("metadata", {}).get("title", path.stem)
            old_nps = recipe.get("metadata", {}).get("nutritionPerServing", {})
            old_kcal = old_nps.get("calories", 0) if old_nps else 0

            recipe = re_enrich_recipe(recipe, enricher, matcher)

            new_nps = recipe.get("metadata", {}).get("nutritionPerServing", {})
            new_kcal = new_nps.get("calories", 0) if new_nps else 0

            if dry_run:
                logger.info(
                    f"[DRY-RUN] {title}: {old_kcal:.0f} -> {new_kcal:.0f} kcal/srv "
                    f"({reason})"
                )
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(recipe, f, indent=2, ensure_ascii=False)
                logger.info(
                    f"Updated: {title}: {old_kcal:.0f} -> {new_kcal:.0f} kcal/srv"
                )

            updated += 1

        except Exception as exc:
            logger.error(f"Failed: {path.stem}: {exc}")
            errors += 1

    logger.info(f"\nDone: {updated} updated, {errors} errors")


if __name__ == "__main__":
    main()
