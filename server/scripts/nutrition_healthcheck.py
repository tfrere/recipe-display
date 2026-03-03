"""
Nutrition healthcheck — fast, deterministic audit of all recipe nutrition data.

Scans every *.recipe.json and runs two layers of checks:

Layer 1 — Recipe-level (unchanged from v1):
  - Distribution of kcal/serving (median, P5–P95, outliers)
  - Confidence breakdown (high / medium / low)
  - Aggregated enrichment issues (no_match, no_weight)
  - Top unresolved ingredients
  - Metadata validity (difficulty, recipeType)

Layer 2 — Deep checks (new):
  - Atwater consistency:   protein*4 + carbs*4 + fat*9 ≈ reported kcal?
  - Per-ingredient sanity: any single ingredient > 5 kg or > 8 000 kcal?
  - Weight conversion:     oz/lb → g conversion matches expected ratio?
  - Broken fractions:      unit starting with "/" or qty > 50 with cup/tbsp/tsp?
  - Calorie density:       ingredient matched to a food > 1 000 kcal/100 g?

Each deep check produces actionable diagnostics: which recipe, which
ingredient, what the computed value is, and why it's suspicious.

100 % local, no LLM, no API cost. Runs in < 5 s on 5 000 recipes.

Usage:
    cd server
    poetry run python scripts/nutrition_healthcheck.py [--json]
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────

RECIPES_DIR = Path(__file__).parent.parent / "data" / "recipes"
NUTRITION_CACHE_PATH = (
    Path(__file__).parent.parent
    / "packages"
    / "recipe_scraper"
    / "src"
    / "recipe_scraper"
    / "data"
    / "nutrition_cache.json"
)

# ── Constants ────────────────────────────────────────────────────────

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_RECIPE_TYPES = {
    "appetizer", "starter", "main_course", "dessert", "drink", "base",
}
VALID_CATEGORIES = {
    "meat", "poultry", "seafood", "produce", "dairy", "egg",
    "grain", "legume", "nuts_seeds", "oil", "herb",
    "pantry", "spice", "condiment", "beverage", "other",
}

# Atwater factors:  protein → 4 kcal/g,  carbs → 4 kcal/g,  fat → 9 kcal/g
ATWATER_TOLERANCE_PCT = 25  # allow 25 % deviation
ATWATER_TOLERANCE_ABS = 50  # and at least 50 kcal absolute

# Per-ingredient guardrails
MAX_INGREDIENT_GRAMS = 5_000       # 5 kg — no single ingredient should exceed this
MAX_INGREDIENT_KCAL = 8_000        # 8 000 kcal total for one ingredient
MAX_KCAL_DENSITY = 1_000           # 1 000 kcal / 100 g (only pure fats/oils exceed this)

# Volume units that are commonly broken by fraction bugs
VOLUME_UNITS_SMALL = {"cup", "cups", "tbsp", "tsp"}
FRACTION_UNIT_PATTERN = re.compile(r"^/\d+\s+")
IMPLAUSIBLE_QTY_THRESHOLD = 50

# oz → g  expected ratio (28.35 g/oz). Flag if > 3× off.
OZ_GRAMS_RATIO = 28.35
OZ_TOLERANCE_FACTOR = 3

# High-density exceptions: these legitimately exceed 1 000 kcal/100 g
HIGH_DENSITY_EXCEPTIONS = {"oil", "shortening", "lard", "ghee", "butter"}


# ── Loaders ──────────────────────────────────────────────────────────

def load_all_recipes() -> list[tuple[Path, dict[str, Any]]]:
    recipes = []
    for path in sorted(RECIPES_DIR.glob("*.recipe.json")):
        with open(path) as f:
            recipes.append((path, json.load(f)))
    return recipes


def load_nutrition_cache() -> dict[str, Any]:
    if not NUTRITION_CACHE_PATH.exists():
        return {}
    with open(NUTRITION_CACHE_PATH) as f:
        cache = json.load(f)
    cache.pop("_meta", None)
    return cache


# ── Layer 1 — Recipe-level checks ───────────────────────────────────

def run_layer1(recipes: list[tuple[Path, dict]]) -> dict[str, Any]:
    """Original healthcheck: distributions, confidence, issues."""
    total = len(recipes)
    cal_values: list[float] = []
    confidence: Counter[str] = Counter()
    issue_types: Counter[str] = Counter()
    unresolved_ingredients: Counter[str] = Counter()
    zero_kcal: list[dict] = []
    high_kcal: list[dict] = []
    invalid_difficulty: list[dict] = []
    invalid_recipe_type: list[dict] = []
    invalid_categories: Counter[str] = Counter()

    for path, recipe in recipes:
        meta = recipe.get("metadata", {})
        nps = meta.get("nutritionPerServing", {})
        kcal = nps.get("calories", 0) if nps else 0
        title = meta.get("title", path.stem)
        cal_values.append(kcal)

        conf = nps.get("confidence", "unknown") if nps else "none"
        confidence[conf] += 1

        if kcal == 0:
            ings = recipe.get("ingredients", [])
            no_qty = sum(1 for i in ings if i.get("quantity") is None)
            zero_kcal.append({
                "title": title,
                "reason": "no_qty" if no_qty > len(ings) * 0.5 else "other",
                "ingredients": len(ings),
            })
        elif kcal > 1500:
            high_kcal.append({
                "title": title,
                "kcal": round(kcal),
                "servings": meta.get("servings", 1),
            })

        for issue in meta.get("nutritionIssues", []):
            issue_type = issue.get("issue", "unknown")
            issue_types[issue_type] += 1
            if issue_type in ("no_match", "no_weight"):
                unresolved_ingredients[issue.get("ingredient", "?")] += 1

        d = meta.get("difficulty")
        if d and d not in VALID_DIFFICULTIES:
            invalid_difficulty.append({"title": title, "value": d})
        rt = meta.get("recipeType")
        if rt and rt not in VALID_RECIPE_TYPES:
            invalid_recipe_type.append({"title": title, "value": rt})
        for ing in recipe.get("ingredients", []):
            cat = ing.get("category")
            if cat and cat not in VALID_CATEGORIES:
                invalid_categories[cat] += 1

    cal_values.sort()

    return {
        "total_recipes": total,
        "calories": {
            "median": cal_values[total // 2] if total else 0,
            "mean": round(sum(cal_values) / total) if total else 0,
            "p5": cal_values[int(total * 0.05)] if total else 0,
            "p95": cal_values[int(total * 0.95)] if total else 0,
        },
        "confidence": dict(confidence.most_common()),
        "zero_kcal": {
            "count": len(zero_kcal),
            "pct": round(100 * len(zero_kcal) / total, 2) if total else 0,
            "recipes": zero_kcal,
        },
        "high_kcal": {
            "count": len(high_kcal),
            "pct": round(100 * len(high_kcal) / total, 2) if total else 0,
            "recipes": sorted(high_kcal, key=lambda x: -x["kcal"]),
        },
        "enrichment_issues": dict(issue_types.most_common()),
        "top_unresolved_ingredients": dict(unresolved_ingredients.most_common(30)),
        "metadata_issues": {
            "invalid_difficulty": invalid_difficulty,
            "invalid_recipe_type": invalid_recipe_type,
            "invalid_categories": dict(invalid_categories.most_common()),
        },
    }


# ── Layer 2 — Deep checks ───────────────────────────────────────────
#
# Each check function receives a single recipe and returns a list of
# diagnostic dicts with a consistent schema:
#
#   {
#     "check":      str,   # check identifier
#     "title":      str,   # recipe title
#     "ingredient": str,   # ingredient name (if applicable)
#     "detail":     str,   # human-readable explanation
#     "computed":   float, # the suspicious value
#     "expected":   float, # what would be reasonable
#   }

def check_atwater(meta: dict, nps: dict) -> list[dict]:
    """Verify protein*4 + carbs*4 + fat*9 ≈ reported calories.

    The Atwater general factor system is the standard method for
    estimating food energy from macronutrients:
      Energy = (protein × 4) + (carbs × 4) + (fat × 9)

    Alcohol contributes 7 kcal/g but we don't track it, so drink recipes
    are expected to under-estimate and are excluded.
    """
    title = meta.get("title", "?")
    kcal = nps.get("calories", 0)
    protein = nps.get("protein", 0)
    fat = nps.get("fat", 0)
    carbs = nps.get("carbs", 0)

    if kcal == 0:
        return []

    atwater_kcal = protein * 4 + carbs * 4 + fat * 9
    if atwater_kcal == 0:
        return []

    deviation_pct = abs(kcal - atwater_kcal) / atwater_kcal * 100
    deviation_abs = abs(kcal - atwater_kcal)

    if deviation_pct > ATWATER_TOLERANCE_PCT and deviation_abs > ATWATER_TOLERANCE_ABS:
        recipe_type = meta.get("recipeType", "")
        if recipe_type == "drink":
            return []  # alcohol gap expected

        return [{
            "check": "atwater_consistency",
            "title": title,
            "ingredient": None,
            "detail": (
                f"Reported {kcal:.0f} kcal but Atwater estimates "
                f"{atwater_kcal:.0f} kcal (P={protein:.1f} C={carbs:.1f} "
                f"F={fat:.1f}). Deviation: {deviation_pct:.0f}%"
            ),
            "computed": round(kcal, 1),
            "expected": round(atwater_kcal, 1),
        }]

    return []


def check_ingredient_sanity(
    meta: dict, nps: dict, ingredients: list[dict],
) -> list[dict]:
    """Flag ingredients with implausible weight (> 5 kg) or calories (> 8 000 kcal).

    A single ingredient contributing 5 kg or 8 000 kcal to a recipe almost
    certainly indicates a unit conversion bug, not a legitimate quantity.
    """
    title = meta.get("title", "?")
    details = nps.get("ingredientDetails", [])
    issues: list[dict] = []

    for det in details:
        name = det.get("nameEn") or det.get("name") or "?"
        grams = det.get("grams") or 0
        cal = det.get("calories") or 0

        if grams > MAX_INGREDIENT_GRAMS:
            issues.append({
                "check": "ingredient_weight",
                "title": title,
                "ingredient": name,
                "detail": (
                    f"{name}: {grams:.0f} g ({grams / 1000:.1f} kg) — "
                    f"exceeds {MAX_INGREDIENT_GRAMS / 1000:.0f} kg limit"
                ),
                "computed": grams,
                "expected": MAX_INGREDIENT_GRAMS,
            })

        if cal > MAX_INGREDIENT_KCAL:
            issues.append({
                "check": "ingredient_calories",
                "title": title,
                "ingredient": name,
                "detail": (
                    f"{name}: {cal:.0f} kcal total — "
                    f"exceeds {MAX_INGREDIENT_KCAL} kcal limit"
                ),
                "computed": cal,
                "expected": MAX_INGREDIENT_KCAL,
            })

    return issues


def check_weight_conversion(
    meta: dict, ingredients: list[dict],
) -> list[dict]:
    """Detect oz/lb → gram conversions that are wildly off.

    Expected: 1 oz ≈ 28.35 g, 1 lb ≈ 453.6 g.
    If estimatedWeightGrams / (quantity × expected_factor) > 3× off, flag it.
    This catches bad entries in portion_weights.json that override direct
    unit conversion.
    """
    title = meta.get("title", "?")
    issues: list[dict] = []

    for ing in ingredients:
        unit = (ing.get("unit") or "").strip().lower()
        qty = ing.get("quantity")
        weight = ing.get("estimatedWeightGrams")

        if not isinstance(qty, (int, float)) or not isinstance(weight, (int, float)):
            continue
        if qty <= 0 or weight <= 0:
            continue

        if unit in ("oz", "ounce", "ounces"):
            expected = qty * OZ_GRAMS_RATIO
            ratio = weight / expected
            if ratio > OZ_TOLERANCE_FACTOR or ratio < 1 / OZ_TOLERANCE_FACTOR:
                name = ing.get("name_en") or ing.get("name") or "?"
                issues.append({
                    "check": "oz_conversion",
                    "title": title,
                    "ingredient": name,
                    "detail": (
                        f"{name}: {qty} oz → {weight:.0f} g "
                        f"(expected ~{expected:.0f} g, ratio {ratio:.1f}×)"
                    ),
                    "computed": round(weight, 1),
                    "expected": round(expected, 1),
                })
        elif unit in ("lb", "lbs", "pound", "pounds"):
            expected = qty * 453.6
            ratio = weight / expected
            if ratio > OZ_TOLERANCE_FACTOR or ratio < 1 / OZ_TOLERANCE_FACTOR:
                name = ing.get("name_en") or ing.get("name") or "?"
                issues.append({
                    "check": "lb_conversion",
                    "title": title,
                    "ingredient": name,
                    "detail": (
                        f"{name}: {qty} lb → {weight:.0f} g "
                        f"(expected ~{expected:.0f} g, ratio {ratio:.1f}×)"
                    ),
                    "computed": round(weight, 1),
                    "expected": round(expected, 1),
                })

    return issues


def check_broken_fractions(
    meta: dict, ingredients: list[dict],
) -> list[dict]:
    """Detect malformed fractions left by the recipe parser.

    Two patterns:
    1. unit = "/2 cup" (the "1" was parsed as quantity, "/" stuck on unit)
    2. quantity > 50 with a small volume unit (e.g. "120 cups") — almost
       certainly a broken fraction like "1/20" that became "120".
    """
    title = meta.get("title", "?")
    issues: list[dict] = []

    for ing in ingredients:
        unit = ing.get("unit") or ""
        qty = ing.get("quantity")
        name = ing.get("name_en") or ing.get("name") or "?"

        if FRACTION_UNIT_PATTERN.match(unit):
            issues.append({
                "check": "broken_fraction_unit",
                "title": title,
                "ingredient": name,
                "detail": (
                    f"{name}: unit=\"{unit}\" looks like a broken fraction "
                    f"(qty={qty})"
                ),
                "computed": qty or 0,
                "expected": None,
            })

        if (
            isinstance(qty, (int, float))
            and qty > IMPLAUSIBLE_QTY_THRESHOLD
            and unit.strip().lower() in VOLUME_UNITS_SMALL
        ):
            issues.append({
                "check": "broken_fraction_qty",
                "title": title,
                "ingredient": name,
                "detail": (
                    f"{name}: {qty} {unit} is implausible — "
                    f"likely a broken fraction"
                ),
                "computed": qty,
                "expected": None,
            })

    return issues


def check_calorie_density(
    meta: dict,
    nps: dict,
    nutrition_cache: dict[str, Any],
) -> list[dict]:
    """Flag ingredients matched to foods with > 1 000 kcal/100 g.

    Only pure fats and oils legitimately exceed this density. Anything
    else (flour matched to "oil", coffee matched to "instant powder") is
    a bad nutritional match from the embedding lookup.
    """
    title = meta.get("title", "?")
    details = nps.get("ingredientDetails", [])
    issues: list[dict] = []

    for det in details:
        name_en = (det.get("nameEn") or "").lower().strip()
        if not name_en:
            continue

        cache_entry = nutrition_cache.get(name_en)
        if not cache_entry:
            continue

        density = cache_entry.get("energy_kcal", 0) or 0
        if density <= MAX_KCAL_DENSITY:
            continue

        # Skip legitimate high-density foods
        is_exception = any(exc in name_en for exc in HIGH_DENSITY_EXCEPTIONS)
        if is_exception:
            continue

        matched_to = cache_entry.get("on_description", "?")
        sim_score = cache_entry.get("similarity_score", 0)
        issues.append({
            "check": "calorie_density",
            "title": title,
            "ingredient": name_en,
            "detail": (
                f"\"{name_en}\" matched to \"{matched_to}\" at "
                f"{density:.0f} kcal/100g (similarity={sim_score:.3f}). "
                f"Threshold: {MAX_KCAL_DENSITY} kcal/100g."
            ),
            "computed": density,
            "expected": MAX_KCAL_DENSITY,
        })

    return issues


def run_layer2(
    recipes: list[tuple[Path, dict]],
    nutrition_cache: dict[str, Any],
) -> dict[str, Any]:
    """Run all deep checks and aggregate results."""
    all_issues: list[dict] = []
    counts: Counter[str] = Counter()

    for _path, recipe in recipes:
        meta = recipe.get("metadata", {})
        nps = meta.get("nutritionPerServing") or {}
        ingredients = recipe.get("ingredients", [])

        for check_fn, args in [
            (check_atwater, (meta, nps)),
            (check_ingredient_sanity, (meta, nps, ingredients)),
            (check_weight_conversion, (meta, ingredients)),
            (check_broken_fractions, (meta, ingredients)),
            (check_calorie_density, (meta, nps, nutrition_cache)),
        ]:
            issues = check_fn(*args)
            for issue in issues:
                counts[issue["check"]] += 1
            all_issues.extend(issues)

    return {
        "total_issues": len(all_issues),
        "by_check": dict(counts.most_common()),
        "issues": all_issues,
    }


# ── Printing ─────────────────────────────────────────────────────────

CHECK_LABELS = {
    "atwater_consistency": "Atwater mismatch (macros ≠ kcal)",
    "ingredient_weight": "Ingredient > 5 kg",
    "ingredient_calories": "Ingredient > 8 000 kcal",
    "oz_conversion": "oz → g conversion off",
    "lb_conversion": "lb → g conversion off",
    "broken_fraction_unit": "Broken fraction in unit",
    "broken_fraction_qty": "Implausible quantity",
    "calorie_density": "Match > 1 000 kcal/100g",
}


def print_layer1(report: dict[str, Any]) -> None:
    total = report["total_recipes"]
    cal = report["calories"]
    conf = report["confidence"]
    zero = report["zero_kcal"]
    high = report["high_kcal"]
    issues = report["enrichment_issues"]
    meta = report["metadata_issues"]

    print("=" * 72)
    print("  NUTRITION HEALTHCHECK — Layer 1: Overview")
    print("=" * 72)
    print(f"  Recipes:           {total}")
    print(f"  Median kcal/srv:   {cal['median']}")
    print(f"  Mean kcal/srv:     {cal['mean']}")
    print(f"  P5–P95:            {cal['p5']}–{cal['p95']}")
    print()
    print("  Confidence breakdown:")
    for level in ("high", "medium", "low", "none", "unknown"):
        count = conf.get(level, 0)
        if count:
            pct = 100 * count / total
            bar = "█" * int(pct / 2)
            print(f"    {level:10s}  {count:>5}  ({pct:.1f}%)  {bar}")
    print()
    print(f"  Zero kcal:         {zero['count']} ({zero['pct']}%)")
    print(f"  >1500 kcal/srv:    {high['count']} ({high['pct']}%)")

    if high["recipes"]:
        print()
        print("  High-calorie outliers:")
        for r in high["recipes"][:10]:
            print(f"    {r['kcal']:>5} kcal | srv={r['servings']} | {r['title']}")
        if len(high["recipes"]) > 10:
            print(f"    ... and {len(high['recipes']) - 10} more")

    if issues:
        print()
        print("  Enrichment issues (aggregated):")
        for issue_type, count in issues.items():
            print(f"    {issue_type:20s}  {count}")

    top_unresolved = report["top_unresolved_ingredients"]
    if top_unresolved:
        print()
        print("  Top unresolved ingredients:")
        for ing, count in list(top_unresolved.items())[:15]:
            print(f"    {count:>4}×  {ing}")

    invalid_d = meta["invalid_difficulty"]
    invalid_rt = meta["invalid_recipe_type"]
    invalid_cat = meta["invalid_categories"]
    if invalid_d or invalid_rt or invalid_cat:
        print()
        print("  Metadata issues:")
        if invalid_d:
            print(f"    Invalid difficulty:   {len(invalid_d)}")
        if invalid_rt:
            print(f"    Invalid recipeType:   {len(invalid_rt)}")
        if invalid_cat:
            print(f"    Invalid categories:   {sum(invalid_cat.values())}")


def print_layer2(deep: dict[str, Any]) -> None:
    total = deep["total_issues"]
    by_check = deep["by_check"]
    issues = deep["issues"]

    print()
    print("=" * 72)
    print("  NUTRITION HEALTHCHECK — Layer 2: Deep Checks")
    print("=" * 72)

    if total == 0:
        print("  No issues found. All deep checks passed.")
        return

    print(f"  Total issues: {total}")
    print()
    print("  Summary by check:")
    for check_id, count in by_check.items():
        label = CHECK_LABELS.get(check_id, check_id)
        print(f"    {count:>4}  {label}")

    grouped: dict[str, list[dict]] = {}
    for issue in issues:
        grouped.setdefault(issue["check"], []).append(issue)

    for check_id in by_check:
        label = CHECK_LABELS.get(check_id, check_id)
        group = grouped.get(check_id, [])
        print()
        print(f"  ── {label} ({len(group)}) ──")
        for item in group[:15]:
            print(f"    • {item['detail']}")
        if len(group) > 15:
            print(f"    ... and {len(group) - 15} more")


def print_report(layer1: dict, deep: dict) -> None:
    print_layer1(layer1)
    print_layer2(deep)
    print()
    print("=" * 72)
    print("  END OF REPORT")
    print("=" * 72)


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    recipes = load_all_recipes()
    nutrition_cache = load_nutrition_cache()

    layer1 = run_layer1(recipes)
    deep = run_layer2(recipes, nutrition_cache)

    if "--json" in sys.argv:
        combined = {"layer1": layer1, "layer2": deep}
        print(json.dumps(combined, indent=2, ensure_ascii=False, default=str))
    else:
        print_report(layer1, deep)


if __name__ == "__main__":
    main()
