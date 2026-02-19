"""
Tests for IngredientTranslator entry validation.

Ensures that polluted entries (LLM refusals, prompt fragments) are
rejected before being persisted to the translation dictionary.
"""

import pytest
from recipe_scraper.services.ingredient_translator import IngredientTranslator


class TestTranslationValidation:
    """Tests for the ingredient translation entry validation."""

    def test_valid_entries(self):
        assert IngredientTranslator._is_valid_ingredient_entry("abricots", "apricots")
        assert IngredientTranslator._is_valid_ingredient_entry("crème fraîche", "cream")
        assert IngredientTranslator._is_valid_ingredient_entry("4 épices", "Allspice")
        assert IngredientTranslator._is_valid_ingredient_entry("100% pumpkin", "pumpkin")

    def test_rejects_dash_key(self):
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "-",
            "I cannot translate the ingredient names as the list provided is empty."
        )

    def test_rejects_llm_refusals_in_value(self):
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "some ingredient",
            "I cannot translate the ingredient names."
        )
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "[note: the core ingredient list is missing]",
            "I notice that the actual list is missing from your request."
        )

    def test_rejects_bracket_keys(self):
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "[unable to extract]",
            "[Unable to extract]"
        )
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "[this is a menu/compilation",
            "Tomato"
        )
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "[ingredients not listed in provided text. cannot extract.]",
            "[Ingredients not listed in provided text. Cannot extract.]"
        )

    def test_rejects_long_sentence_values(self):
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "some ingredient",
            "The provided content is not a complete recipe it lacks the essential structured components"
        )

    def test_rejects_please_provide_in_value(self):
        assert not IngredientTranslator._is_valid_ingredient_entry(
            "[no ingredients listed]",
            "Please provide the ingredient names you would like translated."
        )

    def test_allows_normal_compound_names(self):
        """Multi-word ingredient names that are valid should pass."""
        assert IngredientTranslator._is_valid_ingredient_entry(
            "pâte feuilletée", "puff pastry"
        )
        assert IngredientTranslator._is_valid_ingredient_entry(
            "huile d'olive vierge extra", "extra virgin olive oil"
        )
