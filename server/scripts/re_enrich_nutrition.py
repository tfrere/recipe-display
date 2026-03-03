"""
Re-enrich nutrition for recipes using the full pipeline.

Steps per recipe:
  1. Re-run estimate_grams with updated USDA portion data
  2. Estimate missing quantities via LLM (with confidence gating)
  3. Fill missing weights via LLM fallback
  4. Re-match ingredients against nutrition DB
  5. Recompute nutritionPerServing + tags
  6. Servings sanity check

Usage:
    cd server
    poetry run python scripts/re_enrich_nutrition.py --all          # all recipes
    poetry run python scripts/re_enrich_nutrition.py                # outliers only
    poetry run python scripts/re_enrich_nutrition.py --all --dry-run
    poetry run python scripts/re_enrich_nutrition.py --all --no-llm # skip LLM steps
    poetry run python scripts/re_enrich_nutrition.py --no-match     # only recipes with no_match ingredients
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SERVER_ROOT / "packages" / "recipe_scraper" / "src"))

from recipe_scraper.recipe_enricher import RecipeEnricher
from recipe_scraper.services.nutrition_matcher import NutritionMatcher
from recipe_scraper.enrichment.nutrition import (
    _load_weight_cache,
    _weight_cache_key,
    compute_nutrition_profile,
    derive_nutrition_tags,
    estimate_missing_quantities_llm,
    fill_missing_weights_llm,
)
from recipe_scraper.enrichment.sanitize import repair_ingredient_fractions

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


async def re_enrich_recipe(
    recipe: dict,
    matcher: NutritionMatcher,
    use_llm: bool = True,
) -> dict:
    """Re-compute nutrition for a single recipe."""
    ingredients = recipe.get("ingredients", [])
    if not ingredients:
        return recipe

    # Step 0: repair broken fractions before anything else
    n_repaired = repair_ingredient_fractions(ingredients)
    if n_repaired:
        title = recipe.get("metadata", {}).get("title", "?")
        logger.info(f"Repaired {n_repaired} broken fractions in '{title}'")

    weight_cache = _load_weight_cache()

    # Step 1: re-estimate grams from quantity + unit
    for ing in ingredients:
        name_en = ing.get("name_en", "")
        if not name_en:
            continue
        quantity = ing.get("quantity")
        unit = ing.get("unit")

        if quantity is None:
            # Clear stale weight when quantity was reset (e.g. by fraction repair)
            ing.pop("estimatedWeightGrams", None)
            continue

        grams = NutritionMatcher.estimate_grams(quantity, unit, name_en)
        if grams is not None:
            ing["estimatedWeightGrams"] = round(grams, 1)
        elif isinstance(quantity, (int, float)):
            cache_key = _weight_cache_key(unit, name_en)
            per_unit = weight_cache.get(cache_key)
            if per_unit is not None:
                ing["estimatedWeightGrams"] = round(quantity * per_unit, 1)

    # Step 2: LLM quantity estimation for ingredients with qty=None
    if use_llm:
        try:
            n_estimated = await estimate_missing_quantities_llm(
                ingredients,
                metadata=recipe.get("metadata"),
                steps=recipe.get("steps"),
            )
            if n_estimated:
                logger.info(f"  LLM estimated quantities for {n_estimated} ingredients")

                # Re-run gram estimation for newly estimated ingredients
                for ing in ingredients:
                    if ing.get("quantitySource") == "estimated" and not ing.get("estimatedWeightGrams"):
                        name_en = ing.get("name_en", "")
                        grams = NutritionMatcher.estimate_grams(
                            ing.get("quantity"), ing.get("unit"), name_en,
                        )
                        if grams is not None:
                            ing["estimatedWeightGrams"] = round(grams, 1)
        except Exception as e:
            logger.warning(f"  LLM qty estimation failed (non-blocking): {e}")

    # Step 3: match ingredients against nutrition DB
    names_en = [ing.get("name_en", "") for ing in ingredients if ing.get("name_en")]
    nutrition_data = matcher.match_batch(names_en)

    # Step 3b: resolve unknowns via NutritionResolver (USDA → Perplexity)
    unknown_names = [
        n for n in names_en
        if n.strip().lower() not in nutrition_data
        or nutrition_data.get(n.strip().lower()) is None
    ]
    if unknown_names:
        try:
            from recipe_scraper.services.nutrition_resolver import NutritionResolver
            resolver = NutritionResolver()
            resolved = await resolver.resolve_batch(unknown_names)
            for key, entry in resolved.items():
                if entry is not None:
                    nutrition_data[key] = {
                        "energy_kcal": entry.get("kcal", 0),
                        "protein_g": entry.get("protein", 0),
                        "fat_g": entry.get("fat", 0),
                        "carbs_g": entry.get("carbs", 0),
                        "fiber_g": entry.get("fiber", 0),
                        "sugar_g": entry.get("sugar", 0),
                        "saturated_fat_g": entry.get("sat_fat", 0),
                        "source": entry.get("source", "resolved"),
                        "matching": "auto-resolved",
                    }
                    logger.info(f"  Resolved '{key}' via NutritionResolver")
        except Exception as e:
            logger.warning(f"  NutritionResolver failed (non-blocking): {e}")

    # Step 4: LLM weight estimation fallback
    if use_llm:
        try:
            await fill_missing_weights_llm(ingredients, nutrition_data)
        except Exception as e:
            logger.warning(f"  LLM weight estimation failed (non-blocking): {e}")

    # Step 5: compute nutrition profile
    servings = recipe.get("metadata", {}).get("servings", 1)
    metadata = recipe.get("metadata", {})
    profile = compute_nutrition_profile(ingredients, nutrition_data, servings, metadata)

    nutrition_issues = profile.pop("issues", [])
    recipe["metadata"]["nutritionPerServing"] = profile
    if nutrition_issues:
        recipe["metadata"]["nutritionIssues"] = nutrition_issues
    else:
        recipe["metadata"].pop("nutritionIssues", None)

    tags = derive_nutrition_tags(profile)
    recipe["metadata"]["nutritionTags"] = tags

    recipe["metadata"].pop("servingsSuspect", None)
    recipe["metadata"].pop("servingsOriginal", None)

    # Step 6: servings sanity check
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
        for macro in ("calories", "protein", "fat", "carbs", "fiber", "sugar", "saturatedFat"):
            if macro in profile:
                profile[macro] = round(profile[macro] * ratio, 1)
        if "minerals" in profile:
            for mineral in ("calcium", "iron", "magnesium", "potassium", "sodium", "zinc"):
                if mineral in profile["minerals"]:
                    profile["minerals"][mineral] = round(
                        profile["minerals"][mineral] * ratio,
                        2 if mineral in ("iron", "zinc") else 1,
                    )
        recipe["metadata"]["nutritionPerServing"] = profile
        tags = derive_nutrition_tags(profile)
        recipe["metadata"]["nutritionTags"] = tags

    return recipe


def find_no_match_recipes() -> list[tuple[Path, str]]:
    """Find recipes that have ingredients with 'no_match' status in nutritionPerServing."""
    results = []
    for path in sorted(RECIPES_DIR.glob("*.recipe.json")):
        with open(path) as f:
            recipe = json.load(f)

        details = (
            recipe.get("metadata", {})
            .get("nutritionPerServing", {})
            .get("ingredientDetails", [])
        )
        no_match = [d.get("nameEn", "?") for d in details if d.get("status") == "no_match"]
        if no_match:
            results.append((path, f"{len(no_match)} no_match: {', '.join(no_match[:3])}"))

    return results


async def main():
    dry_run = "--dry-run" in sys.argv
    do_all = "--all" in sys.argv
    no_match_only = "--no-match" in sys.argv
    use_llm = "--no-llm" not in sys.argv

    if do_all:
        targets = [(p, "re-enrich all") for p in sorted(RECIPES_DIR.glob("*.recipe.json"))]
        logger.info(f"Re-enriching ALL {len(targets)} recipes (llm={use_llm})")
    elif no_match_only:
        targets = find_no_match_recipes()
        logger.info(f"Found {len(targets)} recipes with no_match ingredients (llm={use_llm})")
    else:
        targets = find_outlier_recipes()
        logger.info(f"Found {len(targets)} outlier recipes (llm={use_llm})")

    if not targets:
        logger.info("No recipes to process!")
        return

    matcher = NutritionMatcher()

    updated = 0
    errors = 0

    for path, reason in targets:
        try:
            with open(path) as f:
                recipe = json.load(f)

            title = recipe.get("metadata", {}).get("title", path.stem)
            old_nps = recipe.get("metadata", {}).get("nutritionPerServing", {})
            old_kcal = old_nps.get("calories", 0) if old_nps else 0

            recipe = await re_enrich_recipe(recipe, matcher, use_llm=use_llm)

            new_nps = recipe.get("metadata", {}).get("nutritionPerServing", {})
            new_kcal = new_nps.get("calories", 0) if new_nps else 0

            delta = new_kcal - old_kcal
            marker = f"+{delta:.0f}" if delta >= 0 else f"{delta:.0f}"

            if dry_run:
                logger.info(
                    f"[DRY-RUN] {title}: {old_kcal:.0f} → {new_kcal:.0f} kcal/srv ({marker})"
                )
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(recipe, f, indent=2, ensure_ascii=False)
                logger.info(
                    f"Updated: {title}: {old_kcal:.0f} → {new_kcal:.0f} kcal/srv ({marker})"
                )

            updated += 1

        except Exception as exc:
            logger.error(f"Failed: {path.stem}: {exc}")
            errors += 1

    logger.info(f"\nDone: {updated} updated, {errors} errors")


if __name__ == "__main__":
    asyncio.run(main())
