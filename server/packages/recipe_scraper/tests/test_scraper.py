import asyncio
import os
import json
import pytest
from pathlib import Path

from recipe_scraper.scraper import RecipeScraper

TEST_RECIPE_OUTPUT_FOLDER = Path("data/recipes")
TEST_IMAGE_OUTPUT_FOLDER = Path("data/recipes/images")

TEST_URL = "https://cookieandkate.com/best-lentil-soup-recipe/"

AUTH_FILE = Path("data/auth_presets.json")

TEST_RECIPE_TEXT = """
Salade simple

Ingrédients:
- 1 concombre
- 2 tomates
- 1 oignon
- Huile d'olive
- Sel
- Poivre

Préparation:
1. Coupez tous les légumes en petits dés
2. Mélangez-les dans un bol
3. Ajoutez l'huile, le sel et le poivre
4. Servez immédiatement

Image: https://example.com/salad.jpg
"""


async def mock_progress_callback(message):
    print(f"PROGRESS: {message}")


@pytest.mark.asyncio
async def test_scrape_from_url():
    """Test scraping a public recipe URL."""
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER

    recipe_data = await scraper.scrape_from_url(
        TEST_URL,
        auth_values=None,
        progress_callback=mock_progress_callback,
    )

    assert recipe_data, "No recipe data returned"
    assert "metadata" in recipe_data
    assert "ingredients" in recipe_data
    assert "steps" in recipe_data

    metadata = recipe_data["metadata"]
    assert metadata.get("title")
    assert metadata.get("slug")


@pytest.mark.asyncio
async def test_scrape_from_text_duplicate_detection():
    """Test duplicate detection via text similarity for scrape_from_text."""
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER

    fake_recipe_data = {
        "metadata": {
            "title": "Salade simple",
            "slug": "salade-simple",
            "originalContent": TEST_RECIPE_TEXT,
        },
        "ingredients": [
            {"id": "ing1", "name": "cucumber", "category": "produce"},
            {"id": "ing2", "name": "tomatoes", "category": "produce"},
            {"id": "ing3", "name": "onion", "category": "produce"},
            {"id": "ing4", "name": "olive oil", "category": "condiment"},
            {"id": "ing5", "name": "salt", "category": "spice"},
            {"id": "ing6", "name": "pepper", "category": "spice"},
        ],
        "steps": [{"id": "step1", "action": "Cut the vegetables", "time": "5min"}],
    }

    recipe_file = TEST_RECIPE_OUTPUT_FOLDER / f"{fake_recipe_data['metadata']['slug']}.recipe.json"
    with open(recipe_file, "w") as f:
        json.dump(fake_recipe_data, f, indent=2)

    duplicate_text = TEST_RECIPE_TEXT.replace("simple", "Simple").replace("concombre", "concombre ")
    duplicate_result = await scraper.scrape_from_text(
        duplicate_text,
        file_name="test-salad-duplicate.txt",
        progress_callback=mock_progress_callback,
    )

    assert duplicate_result is None, "Duplicate detection should return None"

    significantly_modified_text = (
        TEST_RECIPE_TEXT
        + "\n\nVariation:\nVous pouvez ajouter des olives et du fromage feta.\n"
        "Saupoudrez de persil frais avant de servir."
    )

    modified_result = await scraper.scrape_from_text(
        significantly_modified_text,
        file_name="test-salad-modified.txt",
        progress_callback=mock_progress_callback,
    )

    assert modified_result is not None, "Significantly modified recipe should not be flagged as duplicate"
    assert "metadata" in modified_result

    try:
        recipe_file.unlink()
        if modified_result and "metadata" in modified_result and "slug" in modified_result["metadata"]:
            modified_file = TEST_RECIPE_OUTPUT_FOLDER / f"{modified_result['metadata']['slug']}.recipe.json"
            if modified_file.exists():
                modified_file.unlink()
    except Exception:
        pass
