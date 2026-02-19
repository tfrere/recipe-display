#!/usr/bin/env python3
"""
Read-only analysis of recipe nutrition data.
Diagnoses whether "too fatty" trend is a recipe pool issue or algorithm issue.
"""
from pathlib import Path
import json
import statistics

RECIPES_DIR = Path(__file__).resolve().parent.parent / "server" / "data" / "recipes"
EXCLUDED_RECIPE_TYPES = ["base", "dessert", "drink", "appetizer"]
BALANCED_PROTEIN = (0.15, 0.35)
BALANCED_CARBS = (0.40, 0.65)
BALANCED_FAT = (0.20, 0.35)


def load_recipes():
    """Load all .recipe.json files."""
    recipes = []
    for f in RECIPES_DIR.glob("*.recipe.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                recipes.append(json.load(fp))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Skip {f.name}: {e}")
    return recipes


def get_nutrition(recipe):
    """Extract nutritionPerServing or None."""
    n = recipe.get("metadata", {}).get("nutritionPerServing")
    if not n or n.get("confidence") == "none":
        return None
    return {
        "calories": float(n.get("calories") or 0),
        "fat": float(n.get("fat") or 0),
        "protein": float(n.get("protein") or 0),
        "carbs": float(n.get("carbs") or 0),
        "fiber": float(n.get("fiber") or 0),
        "confidence": n.get("confidence") or "low",
    }


def get_recipe_type(recipe):
    """Extract recipeType from metadata."""
    return (recipe.get("metadata", {}).get("recipeType") or "unknown").lower()


def macro_ratios(nut):
    """Compute % calories from fat, protein, carbs. 9 cal/g fat, 4 cal/g protein, 4 cal/g carbs."""
    cal = nut["calories"]
    if cal <= 0:
        return None, None, None
    pct_fat = 100 * (nut["fat"] * 9) / cal
    pct_protein = 100 * (nut["protein"] * 4) / cal
    pct_carbs = 100 * (nut["carbs"] * 4) / cal
    return pct_fat, pct_protein, pct_carbs


def is_balanced(pct_fat, pct_protein, pct_carbs):
    """Check WHO/USDA balanced: protein 15-35%, carbs 40-65%, fat 20-35%."""
    if pct_fat is None:
        return False
    return (
        BALANCED_PROTEIN[0] * 100 <= pct_protein <= BALANCED_PROTEIN[1] * 100
        and BALANCED_CARBS[0] * 100 <= pct_carbs <= BALANCED_CARBS[1] * 100
        and BALANCED_FAT[0] * 100 <= pct_fat <= BALANCED_FAT[1] * 100
    )


def passes_meal_planner_filter(recipe):
    """Not dessert/drink/appetizer/base, high confidence nutrition."""
    rtype = get_recipe_type(recipe)
    if rtype in EXCLUDED_RECIPE_TYPES:
        return False
    nut = get_nutrition(recipe)
    return nut is not None and nut["confidence"] == "high"


def main():
    recipes = load_recipes()
    with_nutrition = []
    for r in recipes:
        nut = get_nutrition(r)
        if nut and nut["calories"] > 0:
            with_nutrition.append((r, nut))

    n_total = len(recipes)
    n_with_nutrition = len(with_nutrition)

    def safe_mean(arr):
        return statistics.mean(arr) if arr else 0

    def safe_median(arr):
        return statistics.median(arr) if arr else 0

    def safe_stdev(arr):
        return statistics.stdev(arr) if len(arr) > 1 else 0

    # 1. Calories per serving
    cals = [nut["calories"] for _, nut in with_nutrition]
    # 2. Fat, protein, carbs per serving
    fats = [nut["fat"] for _, nut in with_nutrition]
    prots = [nut["protein"] for _, nut in with_nutrition]
    carbs_list = [nut["carbs"] for _, nut in with_nutrition]

    # 5. Macro ratios
    ratios = [
        macro_ratios(nut)
        for _, nut in with_nutrition
    ]
    pct_fats = [r[0] for r in ratios if r[0] is not None]
    pct_proteins = [r[1] for r in ratios if r[1] is not None]
    pct_carbs_list = [r[2] for r in ratios if r[2] is not None]

    # 6. High fat (>40%)
    high_fat_count = sum(1 for p in pct_fats if p > 40)

    # 7. Balanced
    balanced_count = sum(
        1
        for r in ratios
        if is_balanced(r[0], r[1], r[2])
    )

    # 8. High confidence
    high_conf_count = sum(1 for _, nut in with_nutrition if nut["confidence"] == "high")

    # 9. Average calories by recipe type
    by_type = {}
    for r, nut in with_nutrition:
        t = get_recipe_type(r)
        by_type.setdefault(t, []).append(nut["calories"])
    avg_by_type = {t: safe_mean(vals) for t, vals in sorted(by_type.items())}

    # 10. Meal planner filter pass
    meal_planner_pass = sum(1 for r in recipes if passes_meal_planner_filter(r))

    # Report
    print("=" * 60)
    print("RECIPE NUTRITION ANALYSIS")
    print("Source: server/data/recipes/*.recipe.json")
    print("=" * 60)
    print()

    print("Total recipes:", n_total)
    print("Recipes with nutrition data:", n_with_nutrition)
    print()

    print("1. CALORIES PER SERVING")
    print("   Average:", round(safe_mean(cals), 1), "kcal")
    print("   Median:", round(safe_median(cals), 1), "kcal")
    print()

    print("2. FAT PER SERVING (g)")
    print("   Average:", round(safe_mean(fats), 1), "g")
    print("   Median:", round(safe_median(fats), 1), "g")
    print()

    print("3. PROTEIN PER SERVING (g)")
    print("   Average:", round(safe_mean(prots), 1), "g")
    print("   Median:", round(safe_median(prots), 1), "g")
    print()

    print("4. CARBS PER SERVING (g)")
    print("   Average:", round(safe_mean(carbs_list), 1), "g")
    print("   Median:", round(safe_median(carbs_list), 1), "g")
    print()

    print("5. MACRO RATIOS (% calories from fat, protein, carbs)")
    print("   Fat:    avg", round(safe_mean(pct_fats), 1), "%  std", round(safe_stdev(pct_fats), 1))
    print("   Protein: avg", round(safe_mean(pct_proteins), 1), "%  std", round(safe_stdev(pct_proteins), 1))
    print("   Carbs:  avg", round(safe_mean(pct_carbs_list), 1), "%  std", round(safe_stdev(pct_carbs_list), 1))
    print()

    print("6. RECIPES WITH FAT > 40% OF CALORIES (high fat):", high_fat_count)
    print("   Percentage:", round(100 * high_fat_count / n_with_nutrition, 1) if n_with_nutrition else 0, "%")
    print()

    print("7. BALANCED RECIPES (protein 15–35%, carbs 40–65%, fat 20–35%):", balanced_count)
    print("   Percentage:", round(100 * balanced_count / n_with_nutrition, 1) if n_with_nutrition else 0, "%")
    print()

    print("8. HIGH-CONFIDENCE NUTRITION DATA:", high_conf_count)
    print("   Percentage:", round(100 * high_conf_count / n_with_nutrition, 1) if n_with_nutrition else 0, "%")
    print()

    print("9. AVERAGE CALORIES BY RECIPE TYPE")
    for t, avg in sorted(avg_by_type.items(), key=lambda x: -x[1]):
        count = len(by_type[t])
        print(f"   {t}: {round(avg, 1)} kcal (n={count})")
    print()

    print("10. RECIPES PASSING MEAL PLANNER FILTER (not dessert/drink/appetizer/base, high confidence):")
    print("    Count:", meal_planner_pass)
    print("    Percentage of total:", round(100 * meal_planner_pass / n_total, 1) if n_total else 0, "%")
    print()

    # Extra: high-fat breakdown in meal planner pool
    meal_planner_recipes = [r for r in recipes if passes_meal_planner_filter(r)]
    mp_with_nut = [(r, get_nutrition(r)) for r in meal_planner_recipes]
    mp_ratios = [macro_ratios(n) for _, n in mp_with_nut]
    mp_high_fat = sum(1 for r in mp_ratios if r[0] is not None and r[0] > 40)
    mp_balanced = sum(1 for r in mp_ratios if is_balanced(r[0], r[1], r[2]))

    print("--- MEAL PLANNER POOL (candidates only) ---")
    print(f"   High fat (>40%): {mp_high_fat} / {len(mp_with_nut)} ({round(100*mp_high_fat/len(mp_with_nut),1) if mp_with_nut else 0}%)")
    print(f"   Balanced: {mp_balanced} / {len(mp_with_nut)} ({round(100*mp_balanced/len(mp_with_nut),1) if mp_with_nut else 0}%)")
    if mp_with_nut:
        mp_cals = [n["calories"] for _, n in mp_with_nut]
        mp_fats_pct = [r[0] for r in mp_ratios if r[0] is not None]
        print(f"   Avg calories: {round(safe_mean(mp_cals), 1)} kcal")
        print(f"   Avg % fat: {round(safe_mean(mp_fats_pct), 1)}%")


if __name__ == "__main__":
    main()
