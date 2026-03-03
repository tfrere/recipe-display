"""
Tests for the post-processing pipeline (Pass 1.5 → ingredient replacement → reference correction).

These tests validate that:
- Empty CRF results preserve LLM ingredients
- CRF results correctly replace LLM ingredients
- Invalid references are dropped (not kept)
- Re-validation catches broken graphs after post-processing
- Deduplicated IDs (flour, flour_1) are handled
- Suffix strip resolves _N mismatches
- Name lookup resolves original-language refs to English IDs
"""

import pytest
from recipe_structurer.models.recipe import Recipe, Metadata, Ingredient, Step
from recipe_structurer.services.ingredient_parser import (
    correct_step_references,
    resolve_ref,
    make_ingredient_id,
    normalize_unit,
    parse_ingredient_line,
    parse_ingredients_from_preformat,
)


# ═══════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════

def _make_ingredient(id: str, name: str, **kwargs) -> Ingredient:
    """Create a test ingredient with sensible defaults."""
    defaults = {
        "name_en": name,
        "quantity": 100,
        "unit": "g",
        "category": "produce",
    }
    defaults.update(kwargs)
    return Ingredient(id=id, name=name, **defaults)


def _make_step(id: str, uses: list[str], produces: str, **kwargs) -> Step:
    """Create a test step with sensible defaults."""
    defaults = {
        "action": f"Process {id}",
        "stepType": "prep",
        "subRecipe": "main",
        "requires": [],
    }
    defaults.update(kwargs)
    return Step(id=id, uses=uses, produces=produces, **defaults)


def _make_recipe(
    ingredients: list[Ingredient],
    steps: list[Step],
    final_state: str,
) -> Recipe:
    """Create a minimal valid recipe for testing."""
    return Recipe(
        metadata=Metadata(
            title="Test Recipe",
            description="A test recipe",
            servings=4,
            difficulty="easy",
            recipeType="main_course",
        ),
        ingredients=ingredients,
        steps=steps,
        finalState=final_state,
    )


# ═══════════════════════════════════════════════════════════════════
# TESTS: correct_step_references
# ═══════════════════════════════════════════════════════════════════

class TestCorrectStepReferences:
    """Tests for the deterministic reference correction function."""

    def test_valid_references_unchanged(self):
        """References that already exist should be left as-is."""
        ingredients = [
            _make_ingredient("flour", "Farine"),
            _make_ingredient("sugar", "Sucre"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "sugar"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix", "dough"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].uses == ["flour", "sugar"]
        assert steps[1].uses == ["dry_mix"]

    def test_suffix_strip_corrects_dedup_mismatch(self):
        """salt_1 should resolve to salt when salt exists but salt_1 doesn't."""
        ingredients = [
            _make_ingredient("salt", "Sel"),
            _make_ingredient("flour", "Farine"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "salt_1"], produces="dry_mix"),
        ]
        ingredient_ids = {"salt", "flour"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].uses == ["flour", "salt"]

    def test_name_lookup_resolves_french_ref(self):
        """A French ref like 'oignon' should resolve to 'onions' via name lookup."""
        ingredients = [
            _make_ingredient("onions", "oignon", name_en="onions"),
            _make_ingredient("garlic", "ail", name_en="garlic"),
        ]
        steps = [
            _make_step("s1", uses=["oignon", "garlic"], produces="base"),
        ]
        ingredient_ids = {"onions", "garlic"}
        produced_states = {"base"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].uses == ["onions", "garlic"]

    def test_typo_not_corrected_without_name_match(self):
        """Pure typos (flor → flour) are NOT corrected — no more Levenshtein."""
        ingredients = [
            _make_ingredient("flour", "Farine"),
            _make_ingredient("sugar", "Sucre"),
        ]
        steps = [
            _make_step("s1", uses=["flor"], produces="dry_mix"),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].uses == []  # dropped, not fuzzy-matched

    def test_invalid_ref_dropped_when_no_match(self):
        """References with no match should be dropped, not kept."""
        ingredients = [
            _make_ingredient("flour", "Farine"),
            _make_ingredient("sugar", "Sucre"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "completely_invented_id"], produces="dry_mix"),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].uses == ["flour"]
        assert "completely_invented_id" not in steps[0].uses

    def test_invalid_requires_dropped_when_no_match(self):
        """Invalid requires references should also be dropped."""
        ingredients = [_make_ingredient("flour", "Farine")]
        steps = [
            _make_step(
                "s1",
                uses=["flour"],
                produces="dry_mix",
                requires=["nonexistent_state"],
            ),
        ]
        ingredient_ids = {"flour"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].requires == []

    def test_mixed_valid_and_invalid(self):
        """Only invalid refs are dropped; valid ones are preserved."""
        ingredients = [
            _make_ingredient("flour", "Farine"),
            _make_ingredient("sugar", "Sucre"),
        ]
        steps = [
            _make_step(
                "s1",
                uses=["flour", "fake_id", "sugar"],
                produces="dry_mix",
            ),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert steps[0].uses == ["flour", "sugar"]

    def test_no_lemon_to_onion(self):
        """The old fuzzy matching would map lemon→onion (d=3). This must NOT happen."""
        ingredients = [
            _make_ingredient("onion", "Oignon"),
            _make_ingredient("garlic", "Ail"),
        ]
        steps = [
            _make_step("s1", uses=["lemon", "garlic"], produces="base"),
        ]
        ingredient_ids = {"onion", "garlic"}
        produced_states = {"base"}

        correct_step_references(steps, ingredient_ids, produced_states, ingredients=ingredients)

        assert "onion" not in steps[0].uses  # lemon must NOT become onion
        assert steps[0].uses == ["garlic"]


# ═══════════════════════════════════════════════════════════════════
# TESTS: Re-validation after post-processing
# ═══════════════════════════════════════════════════════════════════

class TestRevalidationAfterPostProcessing:
    """Tests that re-validating a recipe after post-processing catches issues."""

    def test_valid_recipe_passes_revalidation(self):
        """A correctly post-processed recipe should pass re-validation."""
        ingredients = [
            _make_ingredient("flour", "Flour"),
            _make_ingredient("sugar", "Sugar"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "sugar"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]
        recipe = _make_recipe(ingredients, steps, "dough")

        # Should not raise
        Recipe.model_validate(recipe.model_dump())

    def test_empty_ingredients_fails_validation(self):
        """A recipe with empty ingredients but step references should fail."""
        ingredients: list[Ingredient] = []
        steps = [
            _make_step("s1", uses=["flour"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]

        with pytest.raises(ValueError, match="Graph validation failed"):
            _make_recipe(ingredients, steps, "dough")

    def test_broken_ref_after_ingredient_replacement(self):
        """Simulates CRF replacing ingredients with different IDs, breaking refs."""
        # Original recipe has flour, sugar
        # CRF produces "all_purpose_flour", "white_sugar" (different IDs)
        ner_ingredients = [
            _make_ingredient("all_purpose_flour", "All-purpose flour"),
            _make_ingredient("white_sugar", "White sugar"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "sugar"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]

        # Correct references first
        ingredient_ids = {ing.id for ing in ner_ingredients}
        produced_states = {step.produces for step in steps}
        correct_step_references(steps, ingredient_ids, produced_states)

        # The original "flour" and "sugar" are too far from "all_purpose_flour" / "white_sugar"
        # so they should be dropped. Re-validation should catch the empty uses.
        with pytest.raises(ValueError, match="Graph validation failed"):
            _make_recipe(ner_ingredients, steps, "dough")


# ═══════════════════════════════════════════════════════════════════
# TESTS: CRF empty → keep LLM ingredients
# ═══════════════════════════════════════════════════════════════════

class TestCRFEmptyFallback:
    """Tests that simulate the CRF-empty fallback behavior."""

    def test_llm_ingredients_produce_valid_recipe(self):
        """When CRF returns [], LLM ingredients should work as-is."""
        llm_ingredients = [
            _make_ingredient("flour", "Farine", category="pantry"),
            _make_ingredient("sugar", "Sucre", category="pantry"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "sugar"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]

        ner_ingredients: list[Ingredient] = []
        use_ner = len(ner_ingredients) > 0

        # Simulate the generator logic: don't replace if CRF empty
        recipe = _make_recipe(llm_ingredients, steps, "dough")
        if use_ner:
            recipe.ingredients = ner_ingredients
        # else: keep llm_ingredients

        assert len(recipe.ingredients) == 2
        assert recipe.ingredients[0].id == "flour"

    def test_ner_ingredients_replace_llm_when_available(self):
        """When CRF returns results, they should replace LLM ingredients."""
        llm_ingredients = [
            _make_ingredient("flour", "Farine"),
            _make_ingredient("sugar", "Sucre"),
        ]
        ner_ingredients = [
            _make_ingredient("flour", "Flour", quantity=250, unit="g"),
            _make_ingredient("sugar", "Sugar", quantity=100, unit="g"),
        ]
        steps = [
            _make_step("s1", uses=["flour", "sugar"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]

        recipe = _make_recipe(llm_ingredients, steps, "dough")

        use_ner = len(ner_ingredients) > 0
        if use_ner:
            recipe.ingredients = ner_ingredients

        # Re-validate
        Recipe.model_validate(recipe.model_dump())

        assert recipe.ingredients[0].quantity == 250


# ═══════════════════════════════════════════════════════════════════
# TESTS: Deduplicated IDs
# ═══════════════════════════════════════════════════════════════════

class TestDeduplicatedIds:
    """Tests that deduplicated IDs (flour, flour_1) work correctly."""

    def test_deduplicated_ids_in_recipe(self):
        """Recipe with flour and flour_1 should be valid if steps reference both."""
        ingredients = [
            _make_ingredient("flour", "All-purpose flour"),
            _make_ingredient("flour_1", "Bread flour"),
        ]
        steps = [
            _make_step("s1", uses=["flour"], produces="cake_base"),
            _make_step("s2", uses=["flour_1"], produces="bread_dough"),
            _make_step("s3", uses=["cake_base", "bread_dough"], produces="combined"),
        ]

        recipe = _make_recipe(ingredients, steps, "combined")
        Recipe.model_validate(recipe.model_dump())


# ═══════════════════════════════════════════════════════════════════
# TESTS: Utility functions
# ═══════════════════════════════════════════════════════════════════

class TestUtilityFunctions:
    """Tests for helper functions in ingredient_parser."""

    def test_make_ingredient_id(self):
        assert make_ingredient_id("All-Purpose Flour") == "allpurpose_flour"
        assert make_ingredient_id("egg") == "egg"
        assert make_ingredient_id("crème fraîche") == "creme_fraiche"
        assert make_ingredient_id("börek") == "borek"
        assert make_ingredient_id("jalapeño") == "jalapeno"
        assert make_ingredient_id("pâte brisée") == "pate_brisee"

    def test_normalize_unit(self):
        assert normalize_unit("tablespoons") == "tbsp"
        assert normalize_unit("grams") == "g"
        assert normalize_unit("cups") == "cup"
        assert normalize_unit(None) is None
        assert normalize_unit("") is None
        assert normalize_unit("kg") == "kg"


class TestResolveRef:
    """Tests for the deterministic resolve_ref function."""

    def test_exact_match(self):
        valid = {"flour", "sugar", "butter"}
        assert resolve_ref("flour", valid, {}) == "flour"

    def test_suffix_strip(self):
        valid = {"salt", "flour"}
        assert resolve_ref("salt_1", valid, {}) == "salt"

    def test_suffix_strip_to_sibling(self):
        valid = {"salt_1", "flour"}
        assert resolve_ref("salt_2", valid, {}) == "salt_1"

    def test_name_lookup_french(self):
        valid = {"onions", "garlic"}
        name_to_id = {"oignon": "onions", "ail": "garlic"}
        assert resolve_ref("oignon", valid, name_to_id) == "onions"

    def test_name_lookup_partial(self):
        valid = {"grana_padano_cheese"}
        name_to_id = {"grana padano": "grana_padano_cheese"}
        assert resolve_ref("grana_padano", valid, name_to_id) == "grana_padano_cheese"

    def test_no_match_returns_none(self):
        valid = {"flour", "sugar"}
        assert resolve_ref("completely_different_thing", valid, {}) is None

    def test_lemon_does_not_match_onion(self):
        valid = {"onion", "garlic"}
        name_to_id = {"oignon": "onion", "ail": "garlic"}
        assert resolve_ref("lemon", valid, name_to_id) is None


# ═══════════════════════════════════════════════════════════════════
# shared.py — ISO 8601 parsing and utilities
# ═══════════════════════════════════════════════════════════════════

from recipe_structurer.shared import (
    parse_iso8601_minutes,
    minutes_to_iso8601,
    is_valid_iso8601_duration,
    EQUIPMENT_KEYWORDS,
)


class TestParseISO8601:
    def test_minutes_only(self):
        assert parse_iso8601_minutes("PT5M") == 5.0

    def test_hours_only(self):
        assert parse_iso8601_minutes("PT2H") == 120.0

    def test_hours_and_minutes(self):
        assert parse_iso8601_minutes("PT1H30M") == 90.0

    def test_seconds(self):
        assert parse_iso8601_minutes("PT45S") == 0.75

    def test_full_hms(self):
        assert parse_iso8601_minutes("PT1H15M30S") == 75.5

    def test_none_returns_none(self):
        assert parse_iso8601_minutes(None) is None

    def test_empty_returns_none(self):
        assert parse_iso8601_minutes("") is None

    def test_invalid_returns_none(self):
        assert parse_iso8601_minutes("5 minutes") is None

    def test_case_insensitive(self):
        assert parse_iso8601_minutes("pt30m") == 30.0


class TestMinutesToISO8601:
    def test_minutes_only(self):
        assert minutes_to_iso8601(5) == "PT5M"

    def test_hours_and_minutes(self):
        assert minutes_to_iso8601(90) == "PT1H30M"

    def test_hours_only(self):
        assert minutes_to_iso8601(120) == "PT2H"

    def test_zero(self):
        assert minutes_to_iso8601(0) == "PT0M"


class TestIsValidISO8601:
    def test_valid(self):
        assert is_valid_iso8601_duration("PT30M") is True

    def test_invalid(self):
        assert is_valid_iso8601_duration("30 minutes") is False

    def test_none(self):
        assert is_valid_iso8601_duration(None) is False


class TestEquipmentKeywords:
    def test_contains_preheat(self):
        assert "preheat" in EQUIPMENT_KEYWORDS

    def test_contains_prechauffer(self):
        assert "préchauffer" in EQUIPMENT_KEYWORDS

    def test_is_frozenset(self):
        assert isinstance(EQUIPMENT_KEYWORDS, frozenset)


# ═══════════════════════════════════════════════════════════════════
# TESTS: parse_ingredient_line (Pass 1.5 CRF parsing)
# ═══════════════════════════════════════════════════════════════════

class TestParseIngredientLine:
    """Tests for parsing individual ingredient lines from preformatted text."""

    def test_french_with_all_annotations(self):
        line = '- 250g «champignons de Paris» [250g mushrooms, sliced] {produce}, émincés'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.name == "champignons de Paris"
        assert ing.category == "produce"
        assert ing.name_en is not None
        assert "mushroom" in ing.name_en.lower()

    def test_english_basic(self):
        line = '- 2 tbsp «olive oil» [2 tablespoons olive oil] {oil}'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.name == "olive oil"
        assert ing.category == "oil"

    def test_french_dairy(self):
        line = '- 200ml «crème fraîche» [200ml heavy cream] {dairy}'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.name == "crème fraîche"
        assert ing.category == "dairy"
        assert ing.id == "creme_fraiche" or "cream" in ing.id

    def test_optional_ingredient(self):
        line = '- «coriandre fraîche» [fresh cilantro] {herb} (optional)'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.optional is True

    def test_no_quantity_spice(self):
        line = '- «sel» [salt, to taste] {spice}'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.category == "spice"

    def test_english_with_preparation(self):
        line = '- 6 cloves «garlic» [6 cloves garlic, minced] {produce}, minced'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.name == "garlic"
        assert ing.category == "produce"

    def test_grain_category(self):
        line = '- 200g «riz basmati» [200g basmati rice] {grain}'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.category == "grain"

    def test_legume_category(self):
        line = '- 400g «pois chiches» [400g chickpeas, drained] {legume}, égouttés'
        ing = parse_ingredient_line(line)
        assert ing is not None
        assert ing.category == "legume"

    def test_line_without_annotations_returns_none(self):
        line = 'Vous pouvez substituer le beurre par de la margarine'
        ing = parse_ingredient_line(line)
        assert ing is None

    def test_empty_line_returns_none(self):
        ing = parse_ingredient_line("")
        assert ing is None


class TestParseIngredientsFromPreformat:
    """Tests for extracting all ingredients from a preformatted block."""

    SAMPLE_PREFORMAT = """TITLE: Salade César
DESCRIPTION: Une salade classique

INGREDIENTS:
**Salade:**
- 1 «laitue romaine» [1 romaine lettuce] {produce}
- 100g «parmesan» [100g parmesan cheese] {dairy}, râpé
- 50g «croûtons» [50g croutons] {grain}

**Sauce:**
- 2 c-à-s «huile d'olive» [2 tablespoons olive oil] {oil}
- 1 «ail» [1 clove garlic] {produce}
- «sel» [salt, to taste] {spice}

INSTRUCTIONS:
1. Laver la laitue
"""

    def test_extracts_all_ingredients(self):
        result = parse_ingredients_from_preformat(self.SAMPLE_PREFORMAT)
        assert len(result) == 6

    def test_skips_sub_recipe_headers(self):
        result = parse_ingredients_from_preformat(self.SAMPLE_PREFORMAT)
        names = [ing.name for ing in result]
        assert "Salade:" not in names
        assert "Sauce:" not in names

    def test_no_ingredients_section(self):
        text = "TITLE: Test\nINSTRUCTIONS:\n1. Do something"
        result = parse_ingredients_from_preformat(text)
        assert result == []

    def test_rejects_lines_without_annotations(self):
        text = """INGREDIENTS:
- 100g «farine» [100g flour] {pantry}
Note: vous pouvez utiliser de la farine complète
- 50g «sucre» [50g sugar] {pantry}

INSTRUCTIONS:
1. Mélanger
"""
        result = parse_ingredients_from_preformat(text)
        assert len(result) == 2
        names = [ing.name for ing in result]
        assert "farine" in names
        assert "sucre" in names

    def test_dedup_ids(self):
        text = """INGREDIENTS:
- 100g «farine» [100g all-purpose flour] {pantry}
- 50g «farine» [50g bread flour] {pantry}

INSTRUCTIONS:
1. Mélanger
"""
        result = parse_ingredients_from_preformat(text)
        ids = [ing.id for ing in result]
        assert len(set(ids)) == 2
