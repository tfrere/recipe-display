"""
Nutrition Agent — Standalone nutrition cross-validator.

Compares the computed nutritionPerServing against a reference calculation
using the OpenNutrition index. 100% deterministic, no LLM, no API cost.

This agent is read-only: it NEVER modifies recipe files.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    IngredientNutritionDetail,
    NutritionComparison,
    NutritionIssue,
    NutritionReport,
)

logger = logging.getLogger(__name__)

# ── Load reference data ──────────────────────────────────────────────

_INDEX_PATH = Path(__file__).parent.parent / "data" / "opennutrition_index.json"

_NEGLIGIBLE_INGREDIENTS = {
    "salt", "table salt", "sea salt", "fleur de sel", "coarse salt",
    "black pepper", "white pepper", "pepper", "peppercorns",
    "water", "ice", "ice water", "cold water", "hot water",
    "baking soda", "baking powder",
    "cinnamon", "nutmeg", "paprika", "cumin", "turmeric",
    "cayenne pepper", "chili powder", "curry powder",
    "cloves", "allspice", "cardamom", "star anise",
    "oregano", "thyme", "rosemary", "bay leaf",
    "basil", "fresh basil", "parsley", "fresh parsley",
    "cilantro", "fresh cilantro", "mint", "fresh mint",
    "dill", "fresh dill", "chives", "fresh chives", "tarragon",
    "vanilla extract", "vanilla paste", "vanilla bean",
    "food coloring", "gelatin",
}


def _load_index() -> Dict[str, Dict[str, Any]]:
    """Load the OpenNutrition index and build a name -> entry lookup."""
    try:
        with open(_INDEX_PATH) as f:
            entries = json.load(f)
    except FileNotFoundError:
        logger.error(f"OpenNutrition index not found: {_INDEX_PATH}")
        return {}

    index: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        name = entry.get("name", "").lower().strip()
        if name:
            index[name] = entry
        for alt in entry.get("alt", []):
            alt_lower = alt.lower().strip()
            if alt_lower and alt_lower not in index:
                index[alt_lower] = entry
    return index


_REFERENCE_INDEX = _load_index()


# ── Gram estimation (reuse existing logic) ───────────────────────────

def _estimate_grams(
    quantity: Optional[float],
    unit: Optional[str],
    name_en: str,
) -> Optional[float]:
    """Estimate weight in grams. Simplified version for the validator."""
    try:
        from recipe_scraper.services.nutrition_matcher import NutritionMatcher
        return NutritionMatcher.estimate_grams(quantity, unit, name_en)
    except ImportError:
        logger.warning("NutritionMatcher not available, using basic estimation")
        return _basic_estimate_grams(quantity, unit)


def _basic_estimate_grams(
    quantity: Optional[float], unit: Optional[str]
) -> Optional[float]:
    """Fallback gram estimation without NutritionMatcher."""
    if quantity is None or unit is None:
        return None
    unit_lower = unit.lower().strip()
    basic_conversions = {
        "g": 1.0, "kg": 1000.0, "ml": 1.0, "l": 1000.0, "cl": 10.0,
        "tbsp": 15.0, "tsp": 5.0, "cup": 240.0,
        "oz": 28.35, "lb": 453.6,
    }
    factor = basic_conversions.get(unit_lower)
    if factor:
        return quantity * factor
    return None


# ── Lookup ───────────────────────────────────────────────────────────

def _lookup_reference(name_en: str) -> Optional[Dict[str, Any]]:
    """Find an ingredient in the reference index by name."""
    key = name_en.lower().strip()
    if key in _REFERENCE_INDEX:
        return _REFERENCE_INDEX[key]

    # Try sub-phrases (longest first)
    words = key.split()
    for length in range(len(words), 0, -1):
        for start in range(len(words) - length + 1):
            candidate = " ".join(words[start : start + length])
            if candidate in _REFERENCE_INDEX:
                return _REFERENCE_INDEX[candidate]

    return None


# ── Deviation ────────────────────────────────────────────────────────

def _pct_deviation(computed: float, reference: float) -> Optional[float]:
    """Percentage deviation. Returns None if reference is 0."""
    if reference == 0:
        return None if computed == 0 else 100.0
    return round(abs(computed - reference) / reference * 100, 1)


# ── Agent ────────────────────────────────────────────────────────────


class NutritionAgent:
    """Standalone nutrition cross-validator.

    Recalculates nutrition from the recipe ingredients using the
    OpenNutrition reference index and compares with the stored
    nutritionPerServing values.

    100% deterministic — no LLM, no API, no cost.
    """

    def validate(self, recipe_data: Dict[str, Any]) -> NutritionReport:
        """Validate nutrition for a single recipe.

        Args:
            recipe_data: Full recipe dict.

        Returns:
            NutritionReport with comparison details.
        """
        metadata = recipe_data.get("metadata", {})
        slug = metadata.get("slug", "unknown")
        title = metadata.get("title", "Untitled")

        if not _REFERENCE_INDEX:
            return NutritionReport(
                slug=slug, title=title,
                error="OpenNutrition reference index not loaded",
            )

        stored_nutrition = metadata.get("nutritionPerServing")
        if not stored_nutrition:
            return NutritionReport(
                slug=slug, title=title,
                error="No nutritionPerServing in recipe metadata",
            )

        # Sanitize types (servings as string, quantity as string, etc.)
        try:
            from recipe_scraper.recipe_enricher import RecipeEnricher
            RecipeEnricher._sanitize_types(recipe_data)
        except ImportError:
            pass

        ingredients = recipe_data.get("ingredients", [])
        servings = metadata.get("servings", 1) or 1
        if not isinstance(servings, (int, float)):
            try:
                servings = int(servings)
            except (ValueError, TypeError):
                servings = 1

        # Recalculate nutrition from ingredients
        ref_total = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}
        ingredient_details: List[IngredientNutritionDetail] = []
        matched = 0
        resolved = 0

        for ing in ingredients:
            name_en = ing.get("name_en", "")
            if not name_en:
                continue

            key = name_en.lower().strip()
            if key in _NEGLIGIBLE_INGREDIENTS:
                continue

            ref_entry = _lookup_reference(name_en)
            detail = IngredientNutritionDetail(name_en=name_en)

            if ref_entry:
                detail.matched_in_ref = True
                detail.ref_kcal_100g = ref_entry.get("kcal")
                matched += 1

                grams = _estimate_grams(
                    ing.get("quantity"), ing.get("unit"), name_en
                )

                if grams and grams > 0:
                    factor = grams / 100.0
                    ref_total["calories"] += (ref_entry.get("kcal", 0) or 0) * factor
                    ref_total["protein"] += (ref_entry.get("protein", 0) or 0) * factor
                    ref_total["fat"] += (ref_entry.get("fat", 0) or 0) * factor
                    ref_total["carbs"] += (ref_entry.get("carbs", 0) or 0) * factor
                    ref_total["fiber"] += (ref_entry.get("fiber", 0) or 0) * factor
                    resolved += 1

            ingredient_details.append(detail)

        # Divide by servings
        for key in ref_total:
            ref_total[key] = round(ref_total[key] / servings, 1)

        # Build comparison
        computed = NutritionComparison(
            calories=stored_nutrition.get("calories", 0),
            protein=stored_nutrition.get("protein", 0),
            fat=stored_nutrition.get("fat", 0),
            carbs=stored_nutrition.get("carbs", 0),
            fiber=stored_nutrition.get("fiber", 0),
        )

        reference = NutritionComparison(**ref_total)

        deviation = NutritionComparison(
            calories=_pct_deviation(computed.calories, reference.calories) or 0,
            protein=_pct_deviation(computed.protein, reference.protein) or 0,
            fat=_pct_deviation(computed.fat, reference.fat) or 0,
            carbs=_pct_deviation(computed.carbs, reference.carbs) or 0,
            fiber=_pct_deviation(computed.fiber, reference.fiber) or 0,
        )

        # Flag issues
        #
        # Minimum absolute thresholds: a 60% deviation on 2g of fiber is
        # nutritionally meaningless. We only flag when BOTH the percentage
        # AND the absolute difference exceed their respective thresholds.
        _MIN_ABS_THRESHOLD = {
            "calories": 100,   # kcal
            "protein": 10,     # g
            "fat": 8,          # g
            "carbs": 15,       # g
            "fiber": 5,        # g
        }

        issues: List[NutritionIssue] = []

        for field in ["calories", "protein", "fat", "carbs", "fiber"]:
            dev = getattr(deviation, field)
            abs_diff = abs(getattr(computed, field) - getattr(reference, field))
            min_abs = _MIN_ABS_THRESHOLD.get(field, 5)

            # Only flag if BOTH percentage and absolute thresholds are exceeded
            if dev > 50 and abs_diff > min_abs:
                issues.append(NutritionIssue(
                    severity="error", field=field,
                    detail=f"{field}: {getattr(computed, field)} vs ref {getattr(reference, field)} ({dev}% deviation, diff={abs_diff:.1f})",
                ))
            elif dev > 30 and abs_diff > min_abs:
                issues.append(NutritionIssue(
                    severity="warning", field=field,
                    detail=f"{field}: {getattr(computed, field)} vs ref {getattr(reference, field)} ({dev}% deviation, diff={abs_diff:.1f})",
                ))

        # Heuristic checks
        if computed.calories > 2000:
            issues.append(NutritionIssue(
                severity="warning", field="calories",
                detail=f"Very high calories per serving: {computed.calories} kcal",
            ))

        confidence = stored_nutrition.get("confidence", "unknown")
        total_ingredients = stored_nutrition.get("totalIngredients", 0)
        resolved_ingredients = stored_nutrition.get("resolvedIngredients", 0)
        if confidence == "high" and total_ingredients > 0 and resolved_ingredients / total_ingredients < 0.5:
            issues.append(NutritionIssue(
                severity="warning", field="confidence",
                detail=f"Confidence is 'high' but only {resolved_ingredients}/{total_ingredients} ingredients resolved",
            ))

        # Verdict
        # If less than 90% of non-negligible ingredients are resolved in the
        # reference, the comparison is unreliable — verdict is "inconclusive"
        total_non_negligible = len(ingredient_details)
        resolution_pct = resolved / total_non_negligible if total_non_negligible > 0 else 0

        if total_non_negligible > 0 and resolution_pct < 0.9:
            verdict = "inconclusive"
            issues.append(NutritionIssue(
                severity="warning", field="resolution",
                detail=(
                    f"Only {resolved}/{total_non_negligible} ingredients resolved "
                    f"in reference ({resolution_pct:.0%}). Need >= 90% for reliable comparison."
                ),
            ))
        else:
            errors = [i for i in issues if i.severity == "error"]
            warnings = [i for i in issues if i.severity == "warning"]
            if errors:
                verdict = "fail"
            elif warnings:
                verdict = "warning"
            else:
                verdict = "pass"

        logger.info(f"[NutritionAgent] {title}: {verdict} ({len(issues)} issues, {matched} matched, {resolved}/{total_non_negligible} resolved)")

        return NutritionReport(
            slug=slug,
            title=title,
            computed=computed,
            reference=reference,
            deviation_pct=deviation,
            issues=issues,
            ingredient_details=ingredient_details,
            verdict=verdict,
        )
