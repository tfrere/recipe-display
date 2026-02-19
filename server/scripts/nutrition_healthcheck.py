"""
Nutrition healthcheck — fast, deterministic audit of all recipe nutrition data.

Reads all *.recipe.json files and reports:
  - Distribution of kcal/serving (median, P5–P95, outliers)
  - Confidence breakdown (high / medium / low)
  - Aggregated issues from enrichment (no_translation, no_match, no_weight)
  - Top unresolved ingredients (the ones that hurt accuracy the most)
  - Metadata validity (difficulty, recipeType)

100% local, no LLM, no API cost. Runs in <5s on 5000 recipes.

Usage:
    cd server
    poetry run python scripts/nutrition_healthcheck.py [--json]
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RECIPES_DIR = Path(__file__).parent.parent / "data" / "recipes"

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_RECIPE_TYPES = {"appetizer", "starter", "main_course", "dessert", "drink", "base"}
VALID_CATEGORIES = {
    "meat", "poultry", "seafood", "produce", "dairy", "egg",
    "grain", "legume", "nuts_seeds", "oil", "herb",
    "pantry", "spice", "condiment", "beverage", "other",
}


def load_all_recipes() -> list[tuple[Path, dict[str, Any]]]:
    recipes = []
    for path in sorted(RECIPES_DIR.glob("*.recipe.json")):
        with open(path) as f:
            recipes.append((path, json.load(f)))
    return recipes


def run_healthcheck(recipes: list[tuple[Path, dict]]) -> dict[str, Any]:
    """Run the healthcheck and return structured results."""
    total = len(recipes)
    cal_values = []
    confidence = Counter()
    issue_types = Counter()
    unresolved_ingredients: Counter = Counter()
    zero_kcal = []
    high_kcal = []
    invalid_difficulty = []
    invalid_recipe_type = []
    invalid_categories: Counter = Counter()

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

        # Aggregate enrichment issues
        for issue in meta.get("nutritionIssues", []):
            issue_type = issue.get("issue", "unknown")
            issue_types[issue_type] += 1
            if issue_type in ("no_match", "no_weight"):
                unresolved_ingredients[issue.get("ingredient", "?")] += 1

        # Metadata validity
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


def print_report(report: dict[str, Any]) -> None:
    total = report["total_recipes"]
    cal = report["calories"]
    conf = report["confidence"]
    zero = report["zero_kcal"]
    high = report["high_kcal"]
    issues = report["enrichment_issues"]
    meta = report["metadata_issues"]

    print("=" * 60)
    print("  NUTRITION HEALTHCHECK")
    print("=" * 60)
    print(f"  Recipes:           {total}")
    print(f"  Median kcal/srv:   {cal['median']}")
    print(f"  Mean kcal/srv:     {cal['mean']}")
    print(f"  P5–P95:            {cal['p5']}–{cal['p95']}")
    print()
    print("  Confidence breakdown:")
    for level in ("high", "medium", "low", "none", "unknown"):
        count = conf.get(level, 0)
        if count:
            print(f"    {level:10s}  {count:>5}  ({100 * count / total:.1f}%)")
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
        print("  Enrichment issues (aggregated across all recipes):")
        for issue_type, count in issues.items():
            print(f"    {issue_type:20s}  {count}")

    top_unresolved = report["top_unresolved_ingredients"]
    if top_unresolved:
        print()
        print("  Top unresolved ingredients (most frequent):")
        for ing, count in list(top_unresolved.items())[:15]:
            print(f"    {count:>4}x  {ing}")

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

    print()
    print("=" * 60)


def main():
    recipes = load_all_recipes()
    report = run_healthcheck(recipes)

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
