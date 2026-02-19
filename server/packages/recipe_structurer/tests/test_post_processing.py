"""
Tests for the post-processing pipeline (Pass 1.5 → ingredient replacement → reference correction).

These tests validate that:
- Empty CRF results preserve LLM ingredients
- CRF results correctly replace LLM ingredients
- Invalid references are dropped (not kept)
- Re-validation catches broken graphs after post-processing
- Deduplicated IDs (flour, flour_1) are handled
"""

import pytest
from recipe_structurer.models.recipe import Recipe, Metadata, Ingredient, Step
from recipe_structurer.services.ingredient_parser import (
    correct_step_references,
    fuzzy_match_id,
    make_ingredient_id,
    normalize_unit,
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
    """Tests for the fuzzy reference correction function."""

    def test_valid_references_unchanged(self):
        """References that already exist should be left as-is."""
        steps = [
            _make_step("s1", uses=["flour", "sugar"], produces="dry_mix"),
            _make_step("s2", uses=["dry_mix"], produces="dough"),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix", "dough"}

        correct_step_references(steps, ingredient_ids, produced_states)

        assert steps[0].uses == ["flour", "sugar"]
        assert steps[1].uses == ["dry_mix"]

    def test_fuzzy_match_corrects_typos(self):
        """Close typos should be auto-corrected via Levenshtein distance."""
        steps = [
            _make_step("s1", uses=["flor"], produces="dry_mix"),  # typo: flor → flour
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states)

        assert steps[0].uses == ["flour"]

    def test_invalid_ref_dropped_when_no_match(self):
        """References with no close match should be dropped, not kept."""
        steps = [
            _make_step("s1", uses=["flour", "completely_invented_id"], produces="dry_mix"),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states)

        assert steps[0].uses == ["flour"]
        assert "completely_invented_id" not in steps[0].uses

    def test_invalid_requires_dropped_when_no_match(self):
        """Invalid requires references should also be dropped."""
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

        correct_step_references(steps, ingredient_ids, produced_states)

        assert steps[0].requires == []

    def test_mixed_valid_and_invalid(self):
        """Only invalid refs are dropped; valid ones are preserved."""
        steps = [
            _make_step(
                "s1",
                uses=["flour", "fake_id", "sugar"],
                produces="dry_mix",
            ),
        ]
        ingredient_ids = {"flour", "sugar"}
        produced_states = {"dry_mix"}

        correct_step_references(steps, ingredient_ids, produced_states)

        assert steps[0].uses == ["flour", "sugar"]


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
        assert make_ingredient_id("crème fraîche") == "crme_frache"

    def test_normalize_unit(self):
        assert normalize_unit("tablespoons") == "tbsp"
        assert normalize_unit("grams") == "g"
        assert normalize_unit("cups") == "cup"
        assert normalize_unit(None) is None
        assert normalize_unit("") is None
        assert normalize_unit("kg") == "kg"

    def test_fuzzy_match_exact(self):
        valid = {"flour", "sugar", "butter"}
        assert fuzzy_match_id("flour", valid) == "flour"

    def test_fuzzy_match_close(self):
        valid = {"flour", "sugar", "butter"}
        assert fuzzy_match_id("flor", valid) == "flour"

    def test_fuzzy_match_no_match(self):
        valid = {"flour", "sugar", "butter"}
        assert fuzzy_match_id("completely_different_thing", valid) is None


# ═══════════════════════════════════════════════════════════════════
# NOTE: Translation validation tests are in the recipe_scraper package
# (server/packages/recipe_scraper/tests/test_translation_validation.py)
# because IngredientTranslator lives there, not in recipe_structurer.
# ═══════════════════════════════════════════════════════════════════
