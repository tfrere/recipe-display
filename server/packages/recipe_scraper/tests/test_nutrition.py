"""
Tests for the nutrition enrichment pipeline.

Tests the ingredient translation, USDA FDC lookup, and nutrition
profile computation.
"""

import asyncio
import json
import os
import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample recipe data
SAMPLE_RECIPE_FR = {
    "metadata": {
        "title": "Blanquette de veau",
        "description": "Une blanquette de veau traditionnelle.",
        "servings": 4,
        "difficulty": "medium",
        "recipeType": "main_course",
        "nationality": "French",
    },
    "ingredients": [
        {"id": "veal", "name": "veau", "quantity": 1000, "unit": "g", "category": "meat"},
        {"id": "carrots", "name": "carottes", "quantity": 4, "unit": "piece", "category": "produce"},
        {"id": "onions", "name": "oignons", "quantity": 2, "unit": "piece", "category": "produce"},
        {"id": "butter", "name": "beurre", "quantity": 60, "unit": "g", "category": "dairy"},
        {"id": "flour", "name": "farine", "quantity": 60, "unit": "g", "category": "pantry"},
        {"id": "cream", "name": "crème liquide", "quantity": 200, "unit": "ml", "category": "dairy"},
        {"id": "thyme", "name": "thym frais", "quantity": 2, "unit": "piece", "category": "spice"},
        {"id": "salt", "name": "sel", "quantity": None, "unit": None, "category": "spice"},
        {"id": "pepper", "name": "poivre", "quantity": None, "unit": None, "category": "spice"},
    ],
    "steps": [],
    "finalState": "blanquette",
}

SAMPLE_RECIPE_EN = {
    "metadata": {
        "title": "Classic Chocolate Chip Cookies",
        "description": "Crispy edges, chewy centers.",
        "servings": 24,
        "difficulty": "easy",
        "recipeType": "dessert",
        "nationality": "American",
    },
    "ingredients": [
        {"id": "flour", "name": "all-purpose flour", "quantity": 2.25, "unit": "cup", "category": "pantry"},
        {"id": "baking_soda", "name": "baking soda", "quantity": 1, "unit": "tsp", "category": "pantry"},
        {"id": "salt", "name": "salt", "quantity": 1, "unit": "tsp", "category": "spice"},
        {"id": "butter", "name": "butter", "quantity": 1, "unit": "cup", "category": "dairy"},
        {"id": "sugar", "name": "granulated sugar", "quantity": 0.75, "unit": "cup", "category": "pantry"},
        {"id": "brown_sugar", "name": "brown sugar", "quantity": 0.75, "unit": "cup", "category": "pantry"},
        {"id": "eggs", "name": "large eggs", "quantity": 2, "unit": "piece", "category": "egg"},
        {"id": "vanilla", "name": "vanilla extract", "quantity": 1, "unit": "tsp", "category": "spice"},
        {"id": "chocolate_chips", "name": "chocolate chips", "quantity": 2, "unit": "cup", "category": "pantry"},
    ],
    "steps": [],
    "finalState": "cookies",
}


async def test_ingredient_translator():
    """Test the ingredient translator with French ingredients."""
    from recipe_scraper.services.ingredient_translator import IngredientTranslator

    print("\n" + "=" * 60)
    print("TEST 1: Ingredient Translation")
    print("=" * 60)

    translator = IngredientTranslator()

    # Test dictionary lookup
    print("\n--- Dictionary lookups ---")
    for name in ["beurre", "oignon", "crème liquide", "thym frais", "veau"]:
        result = translator.lookup(name)
        status = "OK" if result else "MISS"
        print(f"  [{status}] '{name}' -> '{result}'")

    # Test batch translation (includes LLM fallback for unknowns)
    print("\n--- Batch translation (FR recipe) ---")
    translated = await translator.translate_ingredients(SAMPLE_RECIPE_FR["ingredients"])
    for ing, name_en in translated:
        print(f"  '{ing['name']}' -> '{name_en}'")

    print("\n--- Batch translation (EN recipe) ---")
    translated_en = await translator.translate_ingredients(SAMPLE_RECIPE_EN["ingredients"])
    for ing, name_en in translated_en:
        print(f"  '{ing['name']}' -> '{name_en}'")

    return True


async def test_nutrition_lookup():
    """Test USDA FDC nutrition lookup."""
    from recipe_scraper.services.nutrition_lookup import NutritionLookup

    print("\n" + "=" * 60)
    print("TEST 2: USDA Nutrition Lookup")
    print("=" * 60)

    lookup = NutritionLookup()

    if not lookup._api_key:
        print("  SKIPPED: No USDA_API_KEY in environment")
        return False

    # Test individual lookups
    test_ingredients = ["chicken", "butter", "all-purpose flour", "carrot", "heavy cream"]

    for name in test_ingredients:
        print(f"\n  Looking up: '{name}'")
        result = await lookup.lookup_ingredient(name)
        if result and not result.get("not_found"):
            print(f"    FDC ID: {result.get('fdc_id')}")
            print(f"    Description: {result.get('fdc_description', '')[:60]}")
            print(f"    Calories: {result.get('energy_kcal', '?')} kcal/100g")
            print(f"    Protein: {result.get('protein_g', '?')} g/100g")
            print(f"    Fat: {result.get('fat_g', '?')} g/100g")
            print(f"    Carbs: {result.get('carbs_g', '?')} g/100g")
            print(f"    Fiber: {result.get('fiber_g', '?')} g/100g")
        else:
            print(f"    NOT FOUND")

    # Save cache
    lookup.save_cache()
    print(f"\n  Cache saved ({len(lookup._cache)} entries)")

    return True


async def test_full_enrichment():
    """Test the full enrichment pipeline on a French recipe."""
    from recipe_scraper.recipe_enricher import RecipeEnricher

    print("\n" + "=" * 60)
    print("TEST 3: Full Nutrition Enrichment")
    print("=" * 60)

    enricher = RecipeEnricher()

    print(f"\n  Enriching: '{SAMPLE_RECIPE_FR['metadata']['title']}'")
    enriched = await enricher.enrich_recipe_async(SAMPLE_RECIPE_FR)

    # Check name_en on ingredients
    print("\n  --- Ingredients with name_en ---")
    for ing in enriched.get("ingredients", []):
        name_en = ing.get("name_en", "")
        print(f"    {ing['name']} -> {name_en}")

    # Check nutrition profile
    profile = enriched.get("metadata", {}).get("nutritionPerServing")
    if profile:
        print(f"\n  --- Nutrition per serving ---")
        print(f"    Calories: {profile.get('calories', 0)} kcal")
        print(f"    Protein: {profile.get('protein', 0)} g")
        print(f"    Fat: {profile.get('fat', 0)} g")
        print(f"    Carbs: {profile.get('carbs', 0)} g")
        print(f"    Fiber: {profile.get('fiber', 0)} g")
        print(f"    Confidence: {profile.get('confidence', 'none')}")
        print(f"    Resolved: {profile.get('resolvedIngredients', 0)}/{profile.get('totalIngredients', 0)}")
    else:
        print("\n  No nutrition profile generated")

    # Check tags
    tags = enriched.get("metadata", {}).get("nutritionTags", [])
    print(f"\n  --- Nutrition tags ---")
    print(f"    {tags if tags else '(none)'}")

    # Now test with EN recipe
    print(f"\n  Enriching: '{SAMPLE_RECIPE_EN['metadata']['title']}'")
    enriched_en = await enricher.enrich_recipe_async(SAMPLE_RECIPE_EN)

    profile_en = enriched_en.get("metadata", {}).get("nutritionPerServing")
    if profile_en:
        print(f"\n  --- Nutrition per serving (cookies, 24 servings) ---")
        print(f"    Calories: {profile_en.get('calories', 0)} kcal")
        print(f"    Protein: {profile_en.get('protein', 0)} g")
        print(f"    Fat: {profile_en.get('fat', 0)} g")
        print(f"    Carbs: {profile_en.get('carbs', 0)} g")
        print(f"    Fiber: {profile_en.get('fiber', 0)} g")
        print(f"    Confidence: {profile_en.get('confidence', 'none')}")

    tags_en = enriched_en.get("metadata", {}).get("nutritionTags", [])
    print(f"    Tags: {tags_en if tags_en else '(none)'}")

    return True


async def main():
    """Run all nutrition tests."""
    load_dotenv()
    load_dotenv("../../.env")  # Server .env
    load_dotenv("../../../../.env")  # Alt path

    print("\nNutrition Enrichment Pipeline Tests")
    print("=" * 60)

    # Test 1: Translation
    await test_ingredient_translator()

    # Test 2: USDA Lookup
    await test_nutrition_lookup()

    # Test 3: Full enrichment
    await test_full_enrichment()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
