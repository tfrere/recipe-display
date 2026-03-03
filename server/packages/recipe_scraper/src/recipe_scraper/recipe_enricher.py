"""
Recipe enricher — thin orchestrator.

Delegates to:
  enrichment.diet      – diet classification
  enrichment.seasons   – seasonal availability
  enrichment.times     – DAG-based time calculation
  enrichment.nutrition – nutritional profile (async)
  enrichment.sanitize  – type coercion
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .observability import observe, langfuse_context
from .enrichment.diet import determine_diets
from .enrichment.seasons import determine_seasons
from .enrichment.times import calculate_times_from_dag, _parse_time_to_minutes
from .enrichment.nutrition import (
    compute_nutrition_profile,
    derive_nutrition_tags,
    fill_missing_weights_llm,
    estimate_missing_quantities_llm,
)
from .enrichment.sanitize import sanitize_types

logger = logging.getLogger(__name__)


class RecipeEnricher:
    """Orchestrates all enrichment steps for a recipe."""

    def __init__(self, data_folder: Optional[Path] = None):
        self._data_folder = data_folder or Path(__file__).parent / "data"

    # ── Synchronous enrichment (diets, seasons, DAG times) ──

    def enrich_recipe(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        recipe_title = recipe_data.get("metadata", {}).get("title", "Untitled recipe")
        logger.info(f'Enriching recipe: "{recipe_title}"')

        enriched_recipe = recipe_data.copy()
        sanitize_types(enriched_recipe)

        # Diets
        diets: List[str] = []
        try:
            diets = determine_diets(recipe_data)
        except Exception as exc:
            logger.error(f"[Enrichment] Diet detection failed: {exc}", exc_info=True)

        # Seasons
        seasons: List[str] = ["all"]
        peak_months: List[str] = []
        try:
            seasons, peak_months = determine_seasons(recipe_data)
        except Exception as exc:
            logger.error(f"[Enrichment] Season detection failed: {exc}", exc_info=True)

        # DAG times
        _EMPTY_TIMES = {
            "totalTime": "PT0M", "totalActiveTime": "PT0M", "totalPassiveTime": "PT0M",
            "totalTimeMinutes": 0.0, "totalActiveTimeMinutes": 0.0, "totalPassiveTimeMinutes": 0.0,
        }
        time_info = _EMPTY_TIMES.copy()
        try:
            time_info = calculate_times_from_dag(recipe_data)

            schema_data = recipe_data.get("metadata", {}).get("_schema_data")
            if schema_data:
                schema_total = schema_data.get("totalTime")
                if schema_total:
                    schema_minutes = _parse_time_to_minutes(schema_total)
                    dag_minutes = time_info.get("totalTimeMinutes", 0)
                    if schema_minutes > 0 and dag_minutes > 0:
                        divergence = abs(dag_minutes - schema_minutes) / schema_minutes
                        if divergence > 0.3:
                            logger.warning(
                                f"[Time divergence] DAG={dag_minutes:.0f}min vs "
                                f"schema.org={schema_minutes:.0f}min ({divergence:.0%} off). "
                                f"Using schema.org totalTime as ground truth."
                            )
                            time_info["totalTime"] = schema_total
                            time_info["totalTimeMinutes"] = schema_minutes
                for schema_field, meta_field in [("prepTime", "prepTime"), ("cookTime", "cookTime")]:
                    val = schema_data.get(schema_field)
                    if val:
                        enriched_recipe.setdefault("metadata", {})[meta_field] = val
        except Exception as exc:
            logger.error(f"[Enrichment] DAG time calculation failed: {exc}", exc_info=True)

        # Assemble metadata
        meta = enriched_recipe.setdefault("metadata", {})
        if "createdAt" not in meta:
            meta["createdAt"] = datetime.now().isoformat()
        meta["updatedAt"] = datetime.now().isoformat()
        if "creationMode" not in meta:
            if "contentHash" in meta:
                meta["creationMode"] = "text"
            elif meta.get("sourceUrl"):
                meta["creationMode"] = "url"
            else:
                meta["creationMode"] = "unknown"

        meta["diets"] = diets
        meta["seasons"] = seasons
        meta["totalTime"] = time_info["totalTime"]
        meta["totalActiveTime"] = time_info["totalActiveTime"]
        meta["totalPassiveTime"] = time_info["totalPassiveTime"]
        meta["totalTimeMinutes"] = time_info["totalTimeMinutes"]
        meta["totalActiveTimeMinutes"] = time_info["totalActiveTimeMinutes"]
        meta["totalPassiveTimeMinutes"] = time_info["totalPassiveTimeMinutes"]
        meta.pop("totalCookingTime", None)

        logger.info(
            f'Recipe "{recipe_title}" enriched with: {", ".join(diets)} diets, '
            f'{", ".join(seasons)} seasons, DAG times: {time_info["totalTime"]} total '
            f'({time_info["totalActiveTime"]} active + {time_info["totalPassiveTime"]} passive)'
        )
        return enriched_recipe

    # ── Async enrichment (adds nutrition) ──

    @observe(name="enrich_recipe")
    async def enrich_recipe_async(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        enriched = self.enrich_recipe(recipe_data)
        recipe_title = enriched.get("metadata", {}).get("title", "Untitled recipe")
        ingredients = enriched.get("ingredients", [])
        if not ingredients:
            logger.warning(f'No ingredients to enrich for "{recipe_title}"')
            return enriched

        try:
            logger.info(f'Starting async nutrition enrichment for "{recipe_title}"')

            from .services.nutrition_matcher import NutritionMatcher
            import asyncio as _aio

            if not hasattr(self, '_nutrition_matcher'):
                self._nutrition_matcher = NutritionMatcher()
            matcher = self._nutrition_matcher

            names_en = [ing.get("name_en", "") for ing in ingredients if ing.get("name_en")]

            async def _seasons_task():
                return determine_seasons(enriched)

            async def _nutrition_task():
                loop = _aio.get_running_loop()
                return await loop.run_in_executor(None, matcher.match_batch, names_en)

            (seasons_peak, nutrition_data) = await _aio.gather(_seasons_task(), _nutrition_task())
            seasons, peak_months = seasons_peak
            enriched["metadata"]["seasons"] = seasons
            if peak_months:
                enriched["metadata"]["peakMonths"] = peak_months

            # Auto-resolve unknowns (USDA → Perplexity)
            unknown_names = [
                name for name in names_en
                if name.strip().lower() not in nutrition_data
                or nutrition_data.get(name.strip().lower()) is None
            ]
            if unknown_names:
                try:
                    from .services.nutrition_resolver import NutritionResolver
                    if not hasattr(self, '_nutrition_resolver'):
                        self._nutrition_resolver = NutritionResolver()
                    resolved = await self._nutrition_resolver.resolve_batch(unknown_names)
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
                except Exception as e:
                    logger.warning(f"Nutrition resolver failed (non-blocking): {e}")

            # Layer 2: LLM quantity estimation for ingredients with qty=None
            try:
                n_estimated = await estimate_missing_quantities_llm(
                    enriched["ingredients"],
                    metadata=enriched.get("metadata"),
                    steps=enriched.get("steps"),
                )
                if n_estimated:
                    logger.info(f"[Enrichment] Estimated quantities for {n_estimated} ingredients via LLM")
            except Exception as e:
                logger.warning(f"[Enrichment] LLM quantity estimation failed (non-blocking): {e}")

            # LLM weight estimation fallback
            await fill_missing_weights_llm(enriched["ingredients"], nutrition_data)

            # Per-serving profile
            servings = enriched.get("metadata", {}).get("servings", 1)
            metadata = enriched.get("metadata", {})
            profile = compute_nutrition_profile(enriched["ingredients"], nutrition_data, servings, metadata)

            nutrition_issues = profile.pop("issues", [])
            enriched["metadata"]["nutritionPerServing"] = profile
            if nutrition_issues:
                enriched["metadata"]["nutritionIssues"] = nutrition_issues

            tags = derive_nutrition_tags(profile)
            enriched["metadata"]["nutritionTags"] = tags

            # Servings sanity-check
            cal_per_serving = profile.get("calories", 0)
            current_servings = enriched["metadata"].get("servings", 1)
            recipe_type = enriched.get("metadata", {}).get("recipeType", "")
            kcal_threshold = 2000 if recipe_type == "main_course" else 1500

            needs_fix = (
                isinstance(current_servings, (int, float))
                and (
                    (current_servings <= 2 and cal_per_serving > kcal_threshold)
                    or cal_per_serving > 3000
                )
            )
            if needs_fix:
                raw_estimate = round(cal_per_serving * current_servings / 500)
                estimated_servings = min(max(4, raw_estimate), current_servings * 4)
                logger.warning(
                    f"[Servings auto-fix] '{recipe_title}': {cal_per_serving:.0f} kcal/serving "
                    f"with servings={current_servings} → auto-correcting to {estimated_servings}"
                )
                enriched["metadata"]["servingsOriginal"] = current_servings
                enriched["metadata"]["servingsSuspect"] = True
                enriched["metadata"]["servings"] = estimated_servings

                ratio = current_servings / estimated_servings
                for macro in ("calories", "protein", "fat", "carbs", "fiber"):
                    if macro in profile:
                        profile[macro] = round(profile[macro] * ratio, 1)
                enriched["metadata"]["nutritionPerServing"] = profile
                tags = derive_nutrition_tags(profile)
                enriched["metadata"]["nutritionTags"] = tags

            logger.info(
                f'Nutrition enrichment complete for "{recipe_title}": '
                f'{profile.get("calories", 0)} kcal/serving, '
                f'confidence={profile.get("confidence", "unknown")}, tags={tags}'
            )
        except Exception as exc:
            logger.error(
                f'[Enrichment] Nutrition pipeline failed for "{recipe_title}": {exc}. '
                f"Recipe will be saved without nutrition data.",
                exc_info=True,
            )

        return enriched


# ── CLI re-enrichment ──

def re_enrich_all_recipes(recipes_dir: str, output_dir: Optional[str] = None, should_backup: bool = True) -> int:
    if output_dir is None:
        output_dir = recipes_dir

    recipes_path = Path(recipes_dir)
    if not recipes_path.is_dir():
        logger.error(f"Le répertoire {recipes_dir} n'existe pas")
        return 0

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    backup_dir = None
    if should_backup and output_dir == recipes_dir:
        backup_dir = recipes_path.parent / f"{recipes_path.name}_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)

    enricher = RecipeEnricher()
    processed_count = 0
    recipe_files = list(recipes_path.glob('**/*.recipe.json'))
    total_files = len(recipe_files)
    logger.info(f"Début du traitement de {total_files} fichiers de recettes")

    for i, recipe_file in enumerate(recipe_files):
        logger.info(f"[{i+1}/{total_files}] Traitement de {recipe_file.name}")
        try:
            with open(recipe_file, 'r', encoding='utf-8') as f:
                recipe_data = json.load(f)
            if backup_dir:
                with open(backup_dir / recipe_file.name, 'w', encoding='utf-8') as f:
                    json.dump(recipe_data, f, ensure_ascii=False, indent=2)

            enriched_data = enricher.enrich_recipe(recipe_data)

            if output_dir == recipes_dir:
                output_file = recipe_file
            else:
                rel_path = recipe_file.relative_to(recipes_path)
                output_file = Path(output_dir) / rel_path
                output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)

            processed_count += 1
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {recipe_file}: {str(e)}")

    logger.info(f"Terminé: {processed_count} recettes traitées sur {total_files}")
    return processed_count


def configure_logger():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def main():
    import argparse
    import sys

    configure_logger()

    package_parent = Path(__file__).parent.parent.parent.parent.parent
    server_data_path = package_parent / 'data' / 'recipes'

    default_recipes_dir = str(server_data_path) if server_data_path.exists() else './server/data/recipes'

    parser = argparse.ArgumentParser(description="Outil d'enrichissement de recettes")
    parser.add_argument('--recipes_dir', type=str, default=default_recipes_dir)
    parser.add_argument('--output_dir', type=str, default=None)
    parser.add_argument('--no-backup', action='store_true')
    args = parser.parse_args()

    count = re_enrich_all_recipes(args.recipes_dir, args.output_dir, not args.no_backup)
    logger.info(f"Enrichissement terminé: {count} recettes traitées")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
