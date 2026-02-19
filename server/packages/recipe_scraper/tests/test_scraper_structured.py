"""Tests for Recipe Scraper (Instructor + DeepSeek)"""

import asyncio
import os
import json
import pytest
from pathlib import Path
from dotenv import load_dotenv

from recipe_scraper.scraper import RecipeScraper

# Load environment variables
load_dotenv()
load_dotenv('../../.env')

# Test output folders
TEST_RECIPE_OUTPUT_FOLDER = Path("data/recipes_test")
TEST_IMAGE_OUTPUT_FOLDER = Path("data/recipes_test/images")

# Sample recipe texts
SAMPLE_RECIPE_SIMPLE = """
Crêpes Bretonnes

Ingrédients:
- 250g de farine
- 4 oeufs
- 50cl de lait
- 2 cuillères à soupe de sucre
- 1 pincée de sel
- 30g de beurre fondu

Préparation:
1. Versez la farine dans un saladier et creusez un puits
2. Ajoutez les oeufs, le sucre et le sel
3. Mélangez en incorporant progressivement le lait
4. Ajoutez le beurre fondu et laissez reposer 1h
5. Faites chauffer une poêle et graissez-la légèrement
6. Versez une louche de pâte et faites cuire 2 minutes de chaque côté
7. Servez avec du sucre ou de la confiture
"""

SAMPLE_RECIPE_COMPLEX = """
Boeuf Bourguignon
Par Julia Child

Pour 6 personnes
Préparation: 30 minutes
Cuisson: 3 heures

Ingrédients:
- 1.5 kg de boeuf à braiser
- 200g de lardons
- 24 petits oignons grelots
- 250g de champignons de Paris
- 1 bouteille de vin rouge de Bourgogne
- 2 carottes
- 2 gousses d'ail
- 1 bouquet garni
- 2 cuillères à soupe de farine
- Sel, poivre
- Huile d'olive

Instructions:
1. Faites revenir les lardons dans une cocotte
2. Faites dorer la viande coupée en cubes sur toutes les faces (5 min)
3. Ajoutez les carottes coupées et l'ail
4. Saupoudrez de farine et mélangez
5. Versez le vin rouge et ajoutez le bouquet garni
6. Laissez mijoter à feu doux pendant 2h30
7. Faites revenir les oignons et champignons séparément (10 min)
8. Ajoutez-les à la cocotte 30 minutes avant la fin
9. Rectifiez l'assaisonnement et servez
"""


@pytest.fixture(scope="module")
def setup_folders():
    """Create test folders"""
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup after tests (optional)


@pytest.fixture(scope="module")
def scraper(setup_folders):
    """Create a scraper instance for tests"""
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY") and not (
        os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your-deepseek-api-key-here"
    ):
        pytest.skip("No API key configured (OPENROUTER_API_KEY or DEEPSEEK_API_KEY)")
    
    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER
    return scraper


async def mock_progress_callback(message):
    """Capture progress messages"""
    print(f"PROGRESS: {message}")


@pytest.mark.asyncio
class TestScraperFormat:
    """Test that scraper produces valid structure"""
    
    async def test_simple_recipe_structure(self, scraper):
        """Test that a simple recipe produces valid structure"""
        recipe_data = await scraper.scrape_from_text(
            SAMPLE_RECIPE_SIMPLE,
            file_name="test-crepes.txt",
            progress_callback=mock_progress_callback
        )
        
        assert recipe_data is not None, "Recipe data should not be None"
        
        # Check structure
        assert "metadata" in recipe_data
        assert "ingredients" in recipe_data
        assert "steps" in recipe_data
        assert "finalState" in recipe_data, "Should have finalState"
        
        # Check metadata
        metadata = recipe_data["metadata"]
        assert "title" in metadata
        assert "slug" in metadata
        assert "servings" in metadata
        assert "difficulty" in metadata
        
        # Check time format (ISO 8601)
        if metadata.get("prepTime"):
            assert metadata["prepTime"].startswith("PT"), f"prepTime should be ISO 8601: {metadata['prepTime']}"
        if metadata.get("cookTime"):
            assert metadata["cookTime"].startswith("PT"), f"cookTime should be ISO 8601: {metadata['cookTime']}"
        
        print(f"✅ Recipe generated: {metadata['title']}")
        print(f"   Servings: {metadata['servings']}")
        print(f"   Difficulty: {metadata['difficulty']}")
    
    async def test_ingredients_format(self, scraper):
        """Test that ingredients have correct format"""
        recipe_data = await scraper.scrape_from_text(
            SAMPLE_RECIPE_SIMPLE,
            file_name="test-crepes-ing.txt",
            progress_callback=mock_progress_callback
        )
        
        assert recipe_data is not None
        ingredients = recipe_data.get("ingredients", [])
        
        assert len(ingredients) >= 4, f"Should have at least 4 ingredients, got {len(ingredients)}"
        
        # Check ingredient format
        for ing in ingredients:
            assert "id" in ing, "Ingredient should have id"
            assert "name" in ing, "Ingredient should have name"
            assert "category" in ing, "Ingredient should have category"
            
            # Has quantity and unit on ingredient (not in steps)
            # They are optional but should be present when applicable
            if ing.get("quantity"):
                assert isinstance(ing["quantity"], (int, float)), "quantity should be numeric"
        
        print(f"✅ Ingredients validated: {len(ingredients)} ingredients")
        for ing in ingredients[:3]:
            print(f"   - {ing['name']}: {ing.get('quantity')} {ing.get('unit', '')}")
    
    async def test_steps_format(self, scraper):
        """Test that steps have correct format with uses/produces"""
        recipe_data = await scraper.scrape_from_text(
            SAMPLE_RECIPE_COMPLEX,
            file_name="test-bourguignon.txt",
            progress_callback=mock_progress_callback
        )
        
        assert recipe_data is not None
        steps = recipe_data.get("steps", [])
        
        assert len(steps) >= 5, f"Should have at least 5 steps, got {len(steps)}"
        
        # Check step format
        for step in steps:
            assert "id" in step, "Step should have id"
            assert "action" in step, "Step should have action"
            assert "uses" in step, "Step should have uses array"
            assert "produces" in step, "Step should have produces string"
            assert "stepType" in step, "Step should have stepType"
            
            # Check uses is a list
            assert isinstance(step["uses"], list), "uses should be a list"
            
            # Check produces is a string
            assert isinstance(step["produces"], str), "produces should be a string"
            
            # Uses isPassive (bool) not stepMode (string)
            if "isPassive" in step:
                assert isinstance(step["isPassive"], bool), "isPassive should be boolean"
            
            # Check duration is ISO 8601 if present
            if step.get("duration"):
                assert step["duration"].startswith("PT"), f"duration should be ISO 8601: {step['duration']}"
        
        # Check finalState references a produced state
        final_state = recipe_data.get("finalState")
        produced_states = {s["produces"] for s in steps}
        assert final_state in produced_states, f"finalState '{final_state}' should be in produced states"
        
        print(f"✅ Steps validated: {len(steps)} steps")
        print(f"   Final state: {final_state}")
    
    async def test_enrichment(self, scraper):
        """Test that enrichment works with the recipe format"""
        recipe_data = await scraper.scrape_from_text(
            SAMPLE_RECIPE_COMPLEX,
            file_name="test-bourguignon-enrich.txt",
            progress_callback=mock_progress_callback
        )
        
        assert recipe_data is not None
        metadata = recipe_data.get("metadata", {})
        
        # Check enrichment fields
        assert "diets" in metadata, "Should have diets from enrichment"
        assert "seasons" in metadata, "Should have seasons from enrichment"
        assert "totalTime" in metadata, "Should have totalTime from enrichment"
        assert "totalActiveTime" in metadata, "Should have totalActiveTime from enrichment"
        
        # Boeuf Bourguignon should be omnivorous (has meat)
        assert "omnivorous" in metadata["diets"], f"Expected omnivorous diet, got {metadata['diets']}"
        
        print(f"✅ Enrichment validated:")
        print(f"   Diets: {metadata['diets']}")
        print(f"   Seasons: {metadata['seasons']}")
        print(f"   Total time: {metadata['totalTime']}")
        print(f"   Active time: {metadata['totalActiveTime']}")


async def run_tests():
    """Run tests manually"""
    load_dotenv()
    load_dotenv('../../.env')
    
    print("\n🧪 Running Scraper Tests...")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY") and not (
        os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your-deepseek-api-key-here"
    ):
        print("⚠️  Skipping tests - no API key configured")
        return
    
    # Setup
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER
    
    tests = TestScraperFormat()
    
    print("\n1️⃣ Testing simple recipe structure...")
    await tests.test_simple_recipe_structure(scraper)
    
    print("\n2️⃣ Testing ingredients format...")
    await tests.test_ingredients_format(scraper)
    
    print("\n3️⃣ Testing steps format (uses/produces)...")
    await tests.test_steps_format(scraper)
    
    print("\n4️⃣ Testing enrichment...")
    await tests.test_enrichment(scraper)
    
    print("\n" + "=" * 60)
    print("✨ All Scraper tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())
