#!/usr/bin/env python3
"""
Recipe Import Pipeline Quality Audit
Analyzes recipe JSON files for quality metrics and systematic errors.
"""
import json
import os
from pathlib import Path
from collections import defaultdict

RECIPES_DIR = Path(__file__).resolve().parent.parent / "server" / "data" / "recipes"


def load_recipe(path: Path) -> dict | None:
    """Load a recipe JSON file, return None on parse error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def main():
    files = list(RECIPES_DIR.glob("*.recipe.json"))
    print(f"Total recipe files: {len(files)}")

    # Aggregate stats
    nutrition_confidence = defaultdict(int)
    empty_ingredients = 0
    missing_image = 0
    zero_calorie = 0
    high_calorie = 0  # >1500 kcal
    low_calorie_desserts = 0  # dessert < 200 kcal
    step_ref_errors = 0
    recipes_with_vegan_but_animal = 0
    total_with_nutrition = 0

    vegan_animal_keywords = [
        "chicken", "lamb", "beef", "pork", "fish", "cream", "cheese",
        "butter", "egg", "milk", "yogurt", "bacon", "shrimp", "tuna",
        "salmon", "honey", "parmesan", "feta", "cheddar", "mozzarella",
    ]

    for path in files:
        recipe = load_recipe(path)
        if not recipe:
            continue

        meta = recipe.get("metadata", {})
        ingredients = recipe.get("ingredients", [])
        steps = recipe.get("steps", [])

        # Empty ingredients
        if not ingredients:
            empty_ingredients += 1

        # Missing image
        if not meta.get("imageUrl") and not meta.get("image"):
            missing_image += 1

        # Nutrition
        nutrition = meta.get("nutritionPerServing")
        if nutrition:
            total_with_nutrition += 1
            conf = nutrition.get("confidence", "unknown")
            nutrition_confidence[conf] += 1

            cal = nutrition.get("calories", 0) or 0
            if cal == 0 and conf != "low":
                zero_calorie += 1
            elif cal > 1500:
                high_calorie += 1
            elif meta.get("recipeType") == "dessert" and 0 < cal < 200:
                low_calorie_desserts += 1

        # Step-ingredient refs (reference before defined)
        ingredient_ids = {ing.get("id") for ing in ingredients if ing.get("id")}
        produced_states: set[str] = set()
        for step in steps:
            for ref in step.get("uses", []):
                if ref not in ingredient_ids and ref not in produced_states:
                    step_ref_errors += 1
                    break
            prod = step.get("produces")
            if prod:
                produced_states.add(prod)

        # Diet vs ingredients: vegan + animal product
        diets = meta.get("diets", []) or []
        if "vegan" in diets:
            ing_names = " ".join(
                (ing.get("name", "") or "").lower()
                for ing in ingredients
            )
            if any(kw in ing_names for kw in vegan_animal_keywords):
                recipes_with_vegan_but_animal += 1

    print("\n--- Nutrition Confidence ---")
    for conf in ["high", "medium", "low", "unknown"]:
        if nutrition_confidence[conf]:
            pct = 100 * nutrition_confidence[conf] / len(files)
            print(f"  {conf}: {nutrition_confidence[conf]} ({pct:.1f}%)")

    print(f"\n--- Quality Issues ---")
    print(f"  Empty ingredients: {empty_ingredients}")
    print(f"  Missing image: {missing_image}")
    print(f"  Zero calories (non-low-conf): {zero_calorie}")
    print(f"  >1500 kcal per serving: {high_calorie}")
    print(f"  Dessert <200 kcal (suspicious): {low_calorie_desserts}")
    print(f"  Step refs to missing ingredient/state: {step_ref_errors}")
    print(f"  Vegan tag but animal ingredients: {recipes_with_vegan_but_animal}")

    # Low confidence percentage
    low_conf = nutrition_confidence.get("low", 0)
    print(f"\n  Nutrition confidence 'low': {100 * low_conf / len(files):.1f}%")

    # Find suspicious recipes
    print("\n--- Suspicious examples ---")
    suspicious_high_cal = []
    suspicious_low_cal = []
    for path in files:
        recipe = load_recipe(path)
        if not recipe:
            continue
        meta = recipe.get("metadata", {})
        nutrition = meta.get("nutritionPerServing")
        if not nutrition:
            continue
        cal = nutrition.get("calories", 0) or 0
        title = meta.get("title", "?")
        slug = meta.get("slug", path.stem)
        rtype = meta.get("recipeType", "")
        if cal > 1000 and rtype in ("starter", "main_course"):
            if "salad" in title.lower() or "noodles" in title.lower():
                suspicious_high_cal.append((slug, title, cal))
    for s, t, c in suspicious_high_cal[:10]:
        print(f"  High-cal light dish: {t} ({c:.0f} kcal) [{s}]")


if __name__ == "__main__":
    main()
