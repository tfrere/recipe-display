import json
import pytest
from pathlib import Path

from recipe_scraper.recipe_enricher import RecipeEnricher
from recipe_scraper.enrichment.times import (
    _parse_time_to_minutes,
    _minutes_to_iso8601,
    calculate_times_from_dag,
    _calculate_times_linear_fallback,
)
from recipe_scraper.enrichment.seasons import determine_seasons, SEASONAL_DATA
from recipe_scraper.enrichment.diet import determine_diets

SAMPLE_RECIPE = {
    "metadata": {
        "title": "Salade de légumes avec temps de préparation",
        "slug": "salade-legumes-temps-preparation"
    },
    "ingredients": [
        {"id": "cucumber", "name": "cucumber", "category": "produce", "quantity": "1", "unit": "piece"},
        {"id": "tomato", "name": "tomato", "category": "produce", "quantity": "2", "unit": "pieces"},
        {"id": "onion", "name": "onion", "category": "produce", "quantity": "1", "unit": "piece"},
        {"id": "olive_oil", "name": "olive oil", "category": "oils", "quantity": "2", "unit": "tbsp"},
        {"id": "salt", "name": "salt", "category": "spices", "quantity": "1", "unit": "tsp"},
        {"id": "pepper", "name": "pepper", "category": "spices", "quantity": "0.5", "unit": "tsp"},
    ],
    "steps": [
        {"id": "s1", "action": "Chop all vegetables into small cubes", "duration": "PT5M",
         "uses": ["cucumber", "tomato", "onion"], "produces": "chopped_vegetables"},
        {"id": "s2", "action": "Mix them in a bowl", "duration": "PT2M",
         "uses": ["chopped_vegetables"], "produces": "mixed_salad"},
        {"id": "s3", "action": "Add oil, salt and pepper", "duration": "PT1M",
         "uses": ["mixed_salad", "olive_oil", "salt", "pepper"], "produces": "dressed_salad"},
        {"id": "s4", "action": "Serve immediately", "duration": "PT1M",
         "uses": ["dressed_salad"], "produces": "final_salad"},
    ],
    "finalState": "final_salad",
}

SAMPLE_RECIPE_WITH_PASSIVE = {
    "metadata": {"title": "Plat complexe avec repos", "slug": "plat-complexe-repos"},
    "ingredients": [
        {"id": "chicken", "name": "chicken", "category": "meat", "quantity": "500", "unit": "g"},
        {"id": "marinade_spices", "name": "spices", "category": "spices", "quantity": "2", "unit": "tbsp"},
    ],
    "steps": [
        {"id": "s1", "action": "Mélanger les ingrédients de la marinade", "duration": "PT5M",
         "uses": ["chicken", "marinade_spices"], "produces": "marinated_chicken"},
        {"id": "s2", "action": "Laisser reposer au frigo", "duration": "PT1H", "isPassive": True,
         "uses": ["marinated_chicken"], "produces": "rested_chicken"},
        {"id": "s3", "action": "Préchauffer le four", "duration": "PT10M", "isPassive": True,
         "uses": [], "produces": "hot_oven"},
        {"id": "s4", "action": "Cuire au four", "duration": "PT30M", "isPassive": True,
         "uses": ["rested_chicken", "hot_oven"], "produces": "cooked_chicken"},
    ],
    "finalState": "cooked_chicken",
}


def test_recipe_enricher_initialization():
    enricher = RecipeEnricher()
    assert enricher is not None
    assert SEASONAL_DATA is not None
    assert "produce" in SEASONAL_DATA
    assert "vegetables" in SEASONAL_DATA["produce"]
    assert "fruits" in SEASONAL_DATA["produce"]


def test_parse_time_to_minutes():
    assert _parse_time_to_minutes("5min") == 5.0
    assert _parse_time_to_minutes("1h") == 60.0
    assert _parse_time_to_minutes("1h30min") == 90.0
    assert _parse_time_to_minutes("45 minutes") == 45.0
    assert _parse_time_to_minutes("1 hour 15 minutes") == 75.0
    assert _parse_time_to_minutes("") == 0.0
    assert _parse_time_to_minutes(None) == 0.0


def test_parse_iso8601_duration():
    assert _parse_time_to_minutes("PT5M") == 5.0
    assert _parse_time_to_minutes("PT1H") == 60.0
    assert _parse_time_to_minutes("PT1H30M") == 90.0
    assert _parse_time_to_minutes("PT45M") == 45.0
    assert _parse_time_to_minutes("PT30S") == 0.5


def test_minutes_to_iso8601():
    assert _minutes_to_iso8601(0) == "PT0M"
    assert _minutes_to_iso8601(5) == "PT5M"
    assert _minutes_to_iso8601(60) == "PT1H"
    assert _minutes_to_iso8601(90) == "PT1H30M"
    assert _minutes_to_iso8601(125) == "PT2H5M"


def test_calculate_times_from_dag_linear():
    time_info = calculate_times_from_dag(SAMPLE_RECIPE)
    assert time_info["totalTimeMinutes"] == 9.0
    assert time_info["totalActiveTimeMinutes"] == 9.0
    assert time_info["totalPassiveTimeMinutes"] == 0.0
    assert time_info["totalTime"] == "PT9M"
    assert time_info["totalActiveTime"] == "PT9M"
    assert time_info["totalPassiveTime"] == "PT0M"


def test_calculate_times_from_dag_with_passive():
    time_info = calculate_times_from_dag(SAMPLE_RECIPE_WITH_PASSIVE)
    assert time_info["totalTimeMinutes"] == 95.0
    assert time_info["totalActiveTimeMinutes"] == 5.0
    assert time_info["totalPassiveTimeMinutes"] == 90.0


def test_calculate_times_linear_fallback():
    recipe_no_dag = {
        "metadata": {"title": "Simple"},
        "steps": [
            {"id": "1", "duration": "PT10M"},
            {"id": "2", "duration": "PT20M", "isPassive": True},
            {"id": "3", "duration": "PT5M"},
        ],
    }
    time_info = _calculate_times_linear_fallback(recipe_no_dag)
    assert time_info["totalTimeMinutes"] == 35.0
    assert time_info["totalActiveTimeMinutes"] == 15.0
    assert time_info["totalPassiveTimeMinutes"] == 20.0


def test_determine_seasons():
    seasons, peak_months = determine_seasons(SAMPLE_RECIPE)
    assert seasons is not None
    assert len(seasons) > 0
    assert "summer" in seasons
    assert peak_months is not None
    assert len(peak_months) > 0


def test_determine_diets():
    diets = determine_diets(SAMPLE_RECIPE)
    assert "vegan" in diets
    assert "vegetarian" in diets
    assert "omnivorous" in diets

    diets_meat = determine_diets(SAMPLE_RECIPE_WITH_PASSIVE)
    assert "omnivorous" in diets_meat
    assert "vegan" not in diets_meat
    assert "vegetarian" not in diets_meat


# ---------------------------------------------------------------------------
# estimate_grams tests (fix 4.6 + 4.2 density)
# ---------------------------------------------------------------------------

from recipe_scraper.services.nutrition_matcher import NutritionMatcher


class TestEstimateGramsCoreLayers:
    """Tests for every resolution layer of estimate_grams."""

    # --- Layer: None quantity → None ---
    def test_none_quantity_returns_none(self):
        assert NutritionMatcher.estimate_grams(None, "g", "chicken") is None

    # --- Layer: weight units (g, kg, oz, lb) → direct ---
    def test_grams(self):
        assert NutritionMatcher.estimate_grams(250, "g", "flour") == 250.0

    def test_kilograms(self):
        assert NutritionMatcher.estimate_grams(1.5, "kg", "potatoes") == 1500.0

    def test_ounces(self):
        assert NutritionMatcher.estimate_grams(4, "oz", "cheese") == pytest.approx(113.4, abs=1)

    def test_pounds(self):
        assert NutritionMatcher.estimate_grams(2, "lb", "beef") == pytest.approx(907.2, abs=0.1)

    # --- Layer: volume units (ml, cl, dl, l) → generic (density=1.0 for unknown) ---
    def test_ml_generic(self):
        assert NutritionMatcher.estimate_grams(100, "ml", "some liquid") == 100.0

    def test_cl(self):
        assert NutritionMatcher.estimate_grams(25, "cl", "some liquid") == 250.0

    def test_dl(self):
        assert NutritionMatcher.estimate_grams(2, "dl", "some liquid") == 200.0

    def test_liters(self):
        assert NutritionMatcher.estimate_grams(1.5, "l", "some liquid") == 1500.0

    # --- Layer: household volume units (cup, tbsp, tsp) ---
    def test_cup_generic(self):
        result = NutritionMatcher.estimate_grams(1, "cup", "some ingredient")
        assert result is not None
        assert result > 0

    def test_tbsp(self):
        assert NutritionMatcher.estimate_grams(2, "tbsp", "some ingredient") == pytest.approx(30.0, abs=1)

    def test_tsp(self):
        assert NutritionMatcher.estimate_grams(3, "tsp", "some ingredient") == pytest.approx(15.0, abs=1)

    # --- Layer: French units (cs, cc) ---
    def test_cs_cuillere_a_soupe(self):
        assert NutritionMatcher.estimate_grams(2, "cs", "some ingredient") == pytest.approx(30.0, abs=1)

    def test_cc_cuillere_a_cafe(self):
        assert NutritionMatcher.estimate_grams(1, "cc", "some ingredient") == pytest.approx(5.0, abs=1)

    # --- Layer: pinch / dash ---
    def test_pinch(self):
        assert NutritionMatcher.estimate_grams(1, "pinch", "cumin") == pytest.approx(0.5, abs=0.1)

    def test_dash(self):
        assert NutritionMatcher.estimate_grams(2, "dash", "paprika") == pytest.approx(1.0, abs=0.1)

    # --- Layer: No unit → PIECE_WEIGHTS lookup ---
    def test_no_unit_egg(self):
        result = NutritionMatcher.estimate_grams(2, None, "egg")
        assert result == pytest.approx(100.0, abs=5)  # 2 × ~50g

    def test_no_unit_onion(self):
        result = NutritionMatcher.estimate_grams(1, None, "onion")
        assert result == pytest.approx(150.0, abs=10)

    def test_no_unit_cherry_tomato(self):
        """Longest-key-first: 'cherry tomato' should not match 'tomato' (150g)."""
        result = NutritionMatcher.estimate_grams(10, None, "cherry tomato")
        assert result == pytest.approx(150.0, abs=10)  # 10 × ~15g, not 10 × 150g

    def test_no_unit_unknown_returns_none(self):
        assert NutritionMatcher.estimate_grams(1, None, "xyznoexist") is None

    # --- Layer: piece-like units (clove, sprig, stalk...) ---
    def test_piece_unit_egg(self):
        result = NutritionMatcher.estimate_grams(3, "piece", "egg")
        assert result == pytest.approx(150.0, abs=10)  # 3 × ~50g

    def test_clove_garlic(self):
        result = NutritionMatcher.estimate_grams(4, "clove", "garlic")
        assert result is not None
        assert 10 <= result <= 25  # 4 cloves, USDA ~3g or PIECE_WEIGHTS ~5g

    def test_sprig_thyme(self):
        result = NutritionMatcher.estimate_grams(3, "sprig", "fresh thyme")
        assert result is not None
        assert result > 0

    # --- Layer: default unit weights (handful, knob) ---
    def test_handful(self):
        result = NutritionMatcher.estimate_grams(2, "handful", "spinach")
        assert result == pytest.approx(60.0, abs=5)  # 2 × 30g

    def test_knob(self):
        result = NutritionMatcher.estimate_grams(1, "knob", "butter")
        assert result == pytest.approx(15.0, abs=2)

    # --- Layer: unresolvable unit → None ---
    def test_unknown_unit_returns_none(self):
        assert NutritionMatcher.estimate_grams(1, "zarblfloop", "chicken") is None

    # --- Edge cases ---
    def test_zero_quantity(self):
        result = NutritionMatcher.estimate_grams(0, "g", "flour")
        assert result == 0.0

    def test_fractional_quantity(self):
        result = NutritionMatcher.estimate_grams(0.5, "kg", "sugar")
        assert result == 500.0


class TestEstimateGramsDensity:
    """Tests for FAO/INFOODS density correction in estimate_grams."""

    def test_water_ml_unchanged(self):
        """Water: 200ml → 200g (density 1.0, no correction applied)."""
        result = NutritionMatcher.estimate_grams(200, "ml", "water")
        assert result == 200.0

    def test_olive_oil_ml(self):
        """Olive oil: 100ml → 92g (density 0.92)."""
        result = NutritionMatcher.estimate_grams(100, "ml", "olive oil")
        assert result == pytest.approx(92.0, abs=1)

    def test_honey_ml(self):
        """Honey: 200ml → 284g (density 1.42)."""
        result = NutritionMatcher.estimate_grams(200, "ml", "honey")
        assert result == pytest.approx(284.0, abs=1)

    def test_milk_ml(self):
        """Milk: 500ml → 515g (density 1.03)."""
        result = NutritionMatcher.estimate_grams(500, "ml", "whole milk")
        assert result == pytest.approx(515.0, abs=1)

    def test_heavy_cream_ml(self):
        """Heavy cream: 200ml → 198g (density 0.99)."""
        result = NutritionMatcher.estimate_grams(200, "ml", "heavy cream")
        assert result == pytest.approx(198.0, abs=1)

    def test_maple_syrup_ml(self):
        """Maple syrup: 60ml → 79.2g (density 1.32)."""
        result = NutritionMatcher.estimate_grams(60, "ml", "maple syrup")
        assert result == pytest.approx(79.2, abs=1)

    def test_red_wine_cl(self):
        """Red wine: 15cl = 150ml → 148.5g (density 0.99)."""
        result = NutritionMatcher.estimate_grams(15, "cl", "red wine")
        assert result == pytest.approx(148.5, abs=1)

    def test_soy_sauce_tbsp(self):
        """Soy sauce: 2 tbsp — USDA portion data takes priority over density."""
        result = NutritionMatcher.estimate_grams(2, "tbsp", "soy sauce")
        assert result is not None
        assert result > 0

    def test_oil_cup(self):
        """Vegetable oil: 1 cup — USDA portion data takes priority (218g)."""
        result = NutritionMatcher.estimate_grams(1, "cup", "vegetable oil")
        assert result is not None
        assert 210 < result < 230

    def test_coconut_milk_ml(self):
        """Coconut milk: 400ml → 404g (density 1.01), no USDA portion for ml."""
        result = NutritionMatcher.estimate_grams(400, "ml", "coconut milk")
        assert result == pytest.approx(404.0, abs=2)

    def test_fish_sauce_ml(self):
        """Fish sauce: 30ml → 33g (density 1.10)."""
        result = NutritionMatcher.estimate_grams(30, "ml", "fish sauce")
        assert result == pytest.approx(33.0, abs=1)

    def test_cognac_ml(self):
        """Cognac: 50ml → 47.5g (density 0.95)."""
        result = NutritionMatcher.estimate_grams(50, "ml", "cognac")
        assert result == pytest.approx(47.5, abs=1)

    def test_grams_unaffected(self):
        """Weight units (g) should NOT be affected by density."""
        result = NutritionMatcher.estimate_grams(200, "g", "olive oil")
        assert result == 200.0

    def test_kg_unaffected(self):
        """Weight units (kg) should NOT be affected by density."""
        result = NutritionMatcher.estimate_grams(1, "kg", "honey")
        assert result == 1000.0

    def test_unknown_liquid_defaults_to_water(self):
        """Unknown liquid: 100ml → 100g (fallback density 1.0)."""
        result = NutritionMatcher.estimate_grams(100, "ml", "mysterious liquid")
        assert result == 100.0

    def test_balsamic_vinegar_ml(self):
        """Balsamic vinegar: 30ml → 31.5g (density 1.05)."""
        result = NutritionMatcher.estimate_grams(30, "ml", "balsamic vinegar")
        assert result == pytest.approx(31.5, abs=1)


# ---------------------------------------------------------------------------
# compute_nutrition_profile tests (fix 4.5)
# ---------------------------------------------------------------------------

from recipe_scraper.enrichment.nutrition import compute_nutrition_profile

CHICKEN_NUT = {"energy_kcal": 239, "protein_g": 27.3, "fat_g": 13.6, "carbs_g": 0, "fiber_g": 0}
RICE_NUT = {"energy_kcal": 130, "protein_g": 2.7, "fat_g": 0.3, "carbs_g": 28.2, "fiber_g": 0.4}
OLIVE_OIL_NUT = {"energy_kcal": 884, "protein_g": 0, "fat_g": 100, "carbs_g": 0, "fiber_g": 0}
BROTH_NUT = {"energy_kcal": 7, "protein_g": 1.1, "fat_g": 0.2, "carbs_g": 0.3, "fiber_g": 0}


class TestComputeNutritionProfile:

    def test_simple_two_ingredients(self):
        """Two ingredients in grams, 2 servings — basic math check."""
        ingredients = [
            {"name": "poulet", "name_en": "chicken", "quantity": 500, "unit": "g"},
            {"name": "riz", "name_en": "rice", "quantity": 300, "unit": "g"},
        ]
        nut_data = {"chicken": CHICKEN_NUT, "rice": RICE_NUT}
        result = compute_nutrition_profile(ingredients, nut_data, servings=2)

        chicken_cal = 239 * (500 / 100)  # 1195
        rice_cal = 130 * (300 / 100)     # 390
        expected_per_serving = (chicken_cal + rice_cal) / 2  # 792.5

        assert result["calories"] == pytest.approx(expected_per_serving, abs=1)
        assert result["confidence"] == "high"
        assert result["resolvedIngredients"] == 2
        assert result["totalIngredients"] == 2

    def test_negligible_ingredients_skipped(self):
        """Salt and pepper should be skipped as negligible."""
        ingredients = [
            {"name": "poulet", "name_en": "chicken", "quantity": 200, "unit": "g"},
            {"name": "sel", "name_en": "salt", "quantity": 5, "unit": "g"},
            {"name": "poivre", "name_en": "black pepper", "quantity": 1, "unit": "g"},
        ]
        nut_data = {"chicken": CHICKEN_NUT}
        result = compute_nutrition_profile(ingredients, nut_data, servings=1)

        assert result["negligibleIngredients"] == 2
        assert result["totalIngredients"] == 1
        assert result["resolvedIngredients"] == 1

    def test_missing_name_en_creates_issue(self):
        """Ingredient without name_en should be flagged as no_translation."""
        ingredients = [
            {"name": "poulet", "name_en": "chicken", "quantity": 200, "unit": "g"},
            {"name": "truc bizarre", "quantity": 100, "unit": "g"},
        ]
        nut_data = {"chicken": CHICKEN_NUT}
        result = compute_nutrition_profile(ingredients, nut_data, servings=1)

        assert result["totalIngredients"] == 2
        assert result["resolvedIngredients"] == 1
        assert any(i["issue"] == "no_translation" for i in result["issues"])

    def test_not_found_ingredient_creates_issue(self):
        """Ingredient not in nutrition_data should produce no_match issue."""
        ingredients = [
            {"name": "poulet", "name_en": "chicken", "quantity": 200, "unit": "g"},
            {"name": "truffe", "name_en": "truffle", "quantity": 20, "unit": "g"},
        ]
        nut_data = {"chicken": CHICKEN_NUT, "truffle": {"not_found": True}}
        result = compute_nutrition_profile(ingredients, nut_data, servings=1)

        assert result["resolvedIngredients"] == 1
        assert result["matchedIngredients"] == 1
        assert any(i["issue"] == "no_match" for i in result["issues"])

    def test_confidence_levels(self):
        """Confidence: high (>=90%), medium (>=50%), low (<50%), none (0 total)."""
        base_nut = {"energy_kcal": 100, "protein_g": 10, "fat_g": 5, "carbs_g": 10, "fiber_g": 1}

        def _make_ings(n_resolved, n_missing):
            ings = [
                {"name_en": f"food{i}", "quantity": 100, "unit": "g"}
                for i in range(n_resolved)
            ] + [
                {"name_en": f"missing{i}", "quantity": 100, "unit": "g"}
                for i in range(n_missing)
            ]
            data = {f"food{i}": base_nut for i in range(n_resolved)}
            for i in range(n_missing):
                data[f"missing{i}"] = {"not_found": True}
            return ings, data

        ings_high, data_high = _make_ings(9, 1)
        assert compute_nutrition_profile(ings_high, data_high, 1)["confidence"] == "high"

        ings_med, data_med = _make_ings(6, 4)
        assert compute_nutrition_profile(ings_med, data_med, 1)["confidence"] == "medium"

        ings_low, data_low = _make_ings(2, 8)
        assert compute_nutrition_profile(ings_low, data_low, 1)["confidence"] == "low"

        assert compute_nutrition_profile([], {}, 1)["confidence"] == "none"

    def test_liquid_retention_braising(self):
        """500ml broth in a non-soup should get 30% retention."""
        ingredients = [
            {"name": "poulet", "name_en": "chicken", "quantity": 500, "unit": "g"},
            {"name": "bouillon", "name_en": "chicken broth", "quantity": 500, "unit": "ml"},
        ]
        nut_data = {"chicken": CHICKEN_NUT, "chicken broth": BROTH_NUT}
        result = compute_nutrition_profile(
            ingredients, nut_data, servings=1,
            metadata={"title": "Poulet braisé", "type": "main_course"},
        )

        assert result.get("liquidRetentionApplied") is True
        broth_detail = next(
            (d for d in result["ingredientDetails"] if d["nameEn"] == "chicken broth"), None
        )
        assert broth_detail is not None
        assert broth_detail["grams"] < 500

    def test_liquid_retention_soup(self):
        """500ml broth in a soup should get 80% retention (not 30%)."""
        ingredients = [
            {"name": "bouillon", "name_en": "chicken broth", "quantity": 500, "unit": "ml"},
        ]
        nut_data = {"chicken broth": BROTH_NUT}
        result = compute_nutrition_profile(
            ingredients, nut_data, servings=1,
            metadata={"title": "Soupe de poulet", "type": "soup"},
        )

        assert result.get("liquidRetentionApplied") is True
        broth_detail = result["ingredientDetails"][0]
        assert broth_detail["grams"] == pytest.approx(500 * 0.80, abs=5)

    def test_ingredient_details_present(self):
        """Each resolved ingredient should appear in ingredientDetails."""
        ingredients = [
            {"name": "poulet", "name_en": "chicken", "quantity": 200, "unit": "g"},
        ]
        nut_data = {"chicken": CHICKEN_NUT}
        result = compute_nutrition_profile(ingredients, nut_data, servings=1)

        assert len(result["ingredientDetails"]) == 1
        detail = result["ingredientDetails"][0]
        assert detail["status"] == "resolved"
        assert detail["grams"] == 200
        assert detail["calories"] > 0
        assert detail["protein"] > 0

    def test_per_serving_division(self):
        """Total macros should be divided by servings."""
        ingredients = [
            {"name": "riz", "name_en": "rice", "quantity": 400, "unit": "g"},
        ]
        nut_data = {"rice": RICE_NUT}
        r1 = compute_nutrition_profile(ingredients, nut_data, servings=1)
        r4 = compute_nutrition_profile(ingredients, nut_data, servings=4)

        assert r1["calories"] == pytest.approx(r4["calories"] * 4, abs=1)

    def test_no_quantity_uses_piece_weight(self):
        """Ingredient with no quantity but a known piece weight should resolve."""
        ingredients = [
            {"name": "oeuf", "name_en": "egg", "quantity": None, "unit": None},
        ]
        egg_nut = {"energy_kcal": 155, "protein_g": 13, "fat_g": 11, "carbs_g": 1.1, "fiber_g": 0}
        nut_data = {"egg": egg_nut}
        result = compute_nutrition_profile(ingredients, nut_data, servings=1)

        assert result["resolvedIngredients"] == 1
        assert result["calories"] > 0


def test_enrich_recipe():
    enricher = RecipeEnricher()
    enriched = enricher.enrich_recipe(SAMPLE_RECIPE)

    assert enriched is not None
    metadata = enriched["metadata"]
    assert "diets" in metadata
    assert "seasons" in metadata
    assert "totalTime" in metadata
    assert "totalActiveTime" in metadata
    assert "totalPassiveTime" in metadata
    assert metadata["totalTime"] == "PT9M"
    assert "totalTimeMinutes" in metadata
    assert metadata["totalTimeMinutes"] == 9.0
    assert "totalCookingTime" not in metadata
    assert enriched["ingredients"] == SAMPLE_RECIPE["ingredients"]
    assert enriched["steps"] == SAMPLE_RECIPE["steps"]


# ---------------------------------------------------------------------------
# run_deterministic_assertions tests (fix 6.2)
# ---------------------------------------------------------------------------

from recipe_scraper.services.recipe_reviewer import run_deterministic_assertions

VALID_RECIPE = {
    "metadata": {"title": "Test", "servings": 4},
    "ingredients": [
        {"id": "chicken", "name": "poulet", "quantity": 500, "unit": "g"},
        {"id": "onion", "name": "oignon", "quantity": 1, "unit": "piece"},
    ],
    "steps": [
        {"id": "s1", "action": "Cut chicken", "duration": "PT10M", "stepType": "prep",
         "uses": ["chicken"], "produces": "cut_chicken"},
        {"id": "s2", "action": "Cook with onion", "duration": "PT20M", "stepType": "cook",
         "uses": ["cut_chicken", "onion"], "produces": "dish"},
    ],
}


class TestDeterministicAssertions:

    def test_valid_recipe_no_failures(self):
        result = run_deterministic_assertions(VALID_RECIPE)
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_empty_ingredients(self):
        recipe = {**VALID_RECIPE, "ingredients": []}
        result = run_deterministic_assertions(recipe)
        assert result.error_count >= 1
        assert any("no ingredients" in f.message for f in result.failures)

    def test_empty_steps(self):
        recipe = {**VALID_RECIPE, "steps": []}
        result = run_deterministic_assertions(recipe)
        assert result.error_count >= 1
        assert any("no steps" in f.message for f in result.failures)

    def test_duplicate_ingredient_ids(self):
        recipe = {
            **VALID_RECIPE,
            "ingredients": [
                {"id": "egg", "quantity": 2, "unit": "piece"},
                {"id": "egg", "quantity": 3, "unit": "piece"},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert result.error_count >= 1
        assert any("Duplicate ingredient ID" in f.message for f in result.failures)

    def test_duplicate_step_ids(self):
        recipe = {
            **VALID_RECIPE,
            "steps": [
                {"id": "s1", "action": "A", "duration": "PT5M", "uses": []},
                {"id": "s1", "action": "B", "duration": "PT5M", "uses": []},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert result.error_count >= 1
        assert any("Duplicate step ID" in f.message for f in result.failures)

    def test_negative_quantity(self):
        recipe = {
            **VALID_RECIPE,
            "ingredients": [
                {"id": "salt", "quantity": -5, "unit": "g"},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert result.error_count >= 1
        assert any("non-positive quantity" in f.message for f in result.failures)

    def test_zero_quantity(self):
        recipe = {
            **VALID_RECIPE,
            "ingredients": [
                {"id": "salt", "quantity": 0, "unit": "g"},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert any("non-positive quantity" in f.message for f in result.failures)

    def test_invalid_iso8601_duration(self):
        recipe = {
            **VALID_RECIPE,
            "steps": [
                {"id": "s1", "action": "Cook", "duration": "10 minutes", "uses": []},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert any("non-ISO-8601 duration" in f.message for f in result.failures)

    def test_missing_duration_warning(self):
        recipe = {
            **VALID_RECIPE,
            "steps": [
                {"id": "s1", "action": "Cook", "uses": []},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert result.warning_count >= 1
        assert any("no duration" in f.message for f in result.failures)

    def test_aberrant_duration_warning(self):
        """A 'prep' step of 5 hours should trigger a warning (max 120min)."""
        recipe = {
            **VALID_RECIPE,
            "steps": [
                {"id": "s1", "action": "Chop", "duration": "PT5H", "stepType": "prep", "uses": []},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert any("exceeds typical max" in f.message for f in result.failures)

    def test_broken_step_reference(self):
        recipe = {
            **VALID_RECIPE,
            "steps": [
                {"id": "s1", "action": "Cook", "duration": "PT10M",
                 "uses": ["nonexistent_ingredient"]},
            ],
        }
        result = run_deterministic_assertions(recipe)
        assert any("unknown ID" in f.message for f in result.failures)

    def test_step_referencing_produces_is_valid(self):
        """A step using another step's 'produces' should NOT be flagged."""
        result = run_deterministic_assertions(VALID_RECIPE)
        ref_failures = [f for f in result.failures if f.category == "reference"]
        assert len(ref_failures) == 0

    def test_non_positive_servings(self):
        recipe = {**VALID_RECIPE, "metadata": {"servings": 0}}
        result = run_deterministic_assertions(recipe)
        assert any("non-positive" in f.message and "Servings" in f.message for f in result.failures)

    def test_error_vs_warning_counts(self):
        """Verify error_count and warning_count properties."""
        recipe = {
            "metadata": {"servings": -1},
            "ingredients": [],
            "steps": [{"id": "s1", "action": "A", "uses": []}],
        }
        result = run_deterministic_assertions(recipe)
        assert result.error_count >= 2  # no ingredients + non-positive servings
        assert result.warning_count >= 1  # no duration on step


# ---------------------------------------------------------------------------
# _parse_nutrition_response + _atwater_check tests (fix 5.4)
# ---------------------------------------------------------------------------

from recipe_scraper.services.nutrition_resolver import (
    _atwater_check,
    NutritionResolver,
)


class TestParseNutritionResponse:

    def test_standard_format(self):
        text = "kcal=250 protein=20.5 fat=12.3 carbs=15.0 fiber=2.1 sugar=3.0 sat_fat=4.5"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is not None
        assert result["kcal"] == 250.0
        assert result["protein"] == 20.5
        assert result["fat"] == 12.3
        assert result["carbs"] == 15.0
        assert result["fiber"] == 2.1
        assert result["sugar"] == 3.0
        assert result["sat_fat"] == 4.5

    def test_colon_separator(self):
        text = "kcal: 350  protein: 25  fat: 15  carbs: 30"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is not None
        assert result["kcal"] == 350.0
        assert result["protein"] == 25.0

    def test_mixed_case(self):
        text = "Kcal=100 Protein=8 Fat=5 Carbs=10"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is not None
        assert result["kcal"] == 100.0

    def test_with_surrounding_text(self):
        text = "Based on USDA data: kcal=884 protein=0 fat=100 carbs=0 fiber=0 sugar=0 sat_fat=14"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is not None
        assert result["kcal"] == 884.0
        assert result["fat"] == 100.0

    def test_missing_kcal_returns_none(self):
        text = "protein=20 fat=10 carbs=30"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is None

    def test_partial_fields(self):
        """Only kcal + protein, missing other fields — should still parse."""
        text = "kcal=200 protein=15"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is not None
        assert result["kcal"] == 200.0
        assert result["protein"] == 15.0
        assert "fat" not in result

    def test_empty_string(self):
        assert NutritionResolver._parse_nutrition_response("") is None

    def test_garbage_text(self):
        assert NutritionResolver._parse_nutrition_response("I don't know this ingredient") is None

    def test_decimal_values(self):
        text = "kcal=52.5 protein=1.1 fat=0.2 carbs=13.8"
        result = NutritionResolver._parse_nutrition_response(text)
        assert result is not None
        assert result["kcal"] == 52.5
        assert result["carbs"] == 13.8


class TestAtwaterCheck:

    def test_valid_chicken(self):
        """Chicken: 239 kcal, 27.3g protein, 13.6g fat, 0g carbs → Atwater ≈ 231.6 → ~3% off."""
        assert _atwater_check(239, 27.3, 13.6, 0) is True

    def test_valid_rice(self):
        """Rice: 130 kcal, 2.7g protein, 0.3g fat, 28.2g carbs → Atwater ≈ 126.3 → ~3% off."""
        assert _atwater_check(130, 2.7, 0.3, 28.2) is True

    def test_valid_olive_oil(self):
        """Olive oil: 884 kcal, 0g protein, 100g fat, 0g carbs → Atwater = 900 → ~2% off."""
        assert _atwater_check(884, 0, 100, 0) is True

    def test_invalid_way_off(self):
        """100 kcal but macros suggest 500 → should fail."""
        assert _atwater_check(100, 30, 20, 30) is False

    def test_zero_everything(self):
        """Water: 0 kcal, 0 macros → valid."""
        assert _atwater_check(0, 0, 0, 0) is True

    def test_zero_kcal_with_macros_invalid(self):
        """0 kcal but has macros → invalid."""
        assert _atwater_check(0, 10, 5, 20) is False

    def test_alcohol_tolerance(self):
        """Wine: ~85 kcal, 0.1g protein, 0g fat, 2.6g carbs.
        Atwater = 10.8 vs 85 — alcohol calories aren't in macros.
        With 20% tolerance this should fail (deviation ~87%), which is correct
        because wine is a known Atwater outlier."""
        assert _atwater_check(85, 0.1, 0, 2.6) is False

    def test_boundary_19_percent(self):
        """Exactly at 19% deviation — should pass (< 20%)."""
        # Atwater = 4*10 + 9*5 + 4*20 = 40+45+80 = 165
        # 19% above: 165 * 1.19 = 196.35
        assert _atwater_check(196, 10, 5, 20) is True

    def test_boundary_above_20_percent(self):
        """Well above 20% deviation — should fail."""
        # Atwater = 4*10 + 9*5 + 4*20 = 165, kcal=210 → deviation = 45/210 = 21.4%
        assert _atwater_check(210, 10, 5, 20) is False
