"""Simple format validation tests for recipe services"""
import asyncio
import os
import pytest
from dotenv import load_dotenv

from recipe_structurer.providers.deepseek_model import StreamingDeepseekModel
from recipe_structurer.providers.mistral_model import StreamingMistralModel
from recipe_structurer.models.recipe import LLMRecipeBase, LLMRecipeGraph, LLMMetadata
from recipe_structurer.services.cleanup import cleanup_recipe
from recipe_structurer.services.metadata import generate_metadata
from recipe_structurer.services.graph import generate_graph
from recipe_structurer.exceptions import RecipeRejectedError
from recipe_structurer.constants import DEFAULT_MODEL
from recipe_structurer.generator import get_model

# Sample recipe text for testing
SAMPLE_RECIPE = """
Classic Chocolate Cake

A rich and moist chocolate cake that serves 8 people.

https://www.recipe.com/images/classic-chocolate-cake.png

Ingredients:
- 200g flour
- 50g cocoa powder
- 200g sugar
- 2 eggs
- 100ml milk
- 100g butter
- 1 tsp baking powder

Instructions:
1. Preheat oven to 180°C
2. Mix dry ingredients
3. Add wet ingredients and mix well
4. Pour into cake tin
5. Bake for 30 minutes
"""

# Sample recipe with SVG image for testing
SAMPLE_RECIPE_SVG = """
Classic Chocolate Cake

A rich and moist chocolate cake that serves 8 people.

https://www.recipe.com/images/default-recipe-cover-1.svg

https://www.recipe.com/images/default-recipe-cover-2.svg
https://www.recipe.com/images/logo.svg
https://www.recipe.com/images/another-recipe-cover.svg
https://www.recipe.com/images/test.svg
https://www.recipe.com/images/test2.svg
https://www.recipe.com/images/test3.svg
https://www.recipe.com/images/test4.svg

['https://books.ottolenghi.co.uk/wp-content/uploads/…94e37f5ca9ac316a3e1d9d82d02a5875e66df67668cb1.svg', 'https://books.ottolenghi.co.uk/wp-content/uploads/2021/05/default-recipe-cover-1.svg', 'https://cdn-ukwest.onetrust.com/logos/7de3d71f-b68…ace-44c4-bef8-bd1a1620b740/ottolenghi-logo@2x.png', 'https://cdn-ukwest.onetrust.com/logos/static/powered_by_logo.svg']

Ingredients:
- 200g flour
- 50g cocoa powder
- 200g sugar
- 2 eggs
- 100ml milk
- 100g butter
- 1 tsp baking powder

Instructions:
1. Preheat oven to 180°C
2. Mix dry ingredients
3. Add wet ingredients and mix well
4. Pour into cake tin
5. Bake for 30 minutes
"""

# Sample login page content
SAMPLE_LOGIN_PAGE = """
<html>
    <body>
        <h1>Login to access recipes</h1>
        <form action="/login" method="post">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password">
            <button type="submit">Login</button>
        </form>
    </body>
</html>
"""

@pytest.fixture
async def model():
    """Fixture providing a configured model using default provider"""
    load_dotenv()
    return get_model(DEFAULT_MODEL)

@pytest.fixture
async def cleaned_text(model):
    """Fixture providing cleaned recipe text"""
    return await cleanup_recipe(model, SAMPLE_RECIPE, [])

@pytest.fixture
async def recipe_base(model, cleaned_text):
    """Fixture providing the base recipe structure"""
    return await generate_metadata(model, cleaned_text)

@pytest.mark.asyncio
async def test_cleanup(model):
    """Test that cleanup returns a properly formatted string"""
    cleaned_text = await cleanup_recipe(model, SAMPLE_RECIPE, [])
    
    # Simple format checks
    assert "TITLE:" in cleaned_text
    assert "INGREDIENTS:" in cleaned_text
    assert "INSTRUCTIONS:" in cleaned_text
    print("✅ Cleanup test passed")

@pytest.mark.asyncio
async def test_cleanup_rejects_login_page(model):
    """Test that cleanup rejects a login page"""
    with pytest.raises(RecipeRejectedError) as exc_info:
        await cleanup_recipe(model, SAMPLE_LOGIN_PAGE, [])
    
    # Verify the error message
    error_msg = str(exc_info.value)
    assert "login" in error_msg.lower() or "authentication" in error_msg.lower()
    print("✅ Login page rejection test passed")

@pytest.mark.asyncio
async def test_metadata(model, cleaned_text):
    """Test that metadata generation returns a valid LLMRecipeBase"""
    # Generate metadata directly from cleaned text
    recipe_base = await generate_metadata(model, cleaned_text)
    
    # Verify it's the right type
    assert isinstance(recipe_base, LLMRecipeBase)
    assert isinstance(recipe_base.metadata, LLMMetadata)
    assert len(recipe_base.ingredients) > 0
    print("✅ Metadata test passed")

@pytest.mark.asyncio
async def test_metadata_extracts_image_url(model):
    """Test that metadata generation correctly extracts the image URL."""
    # Sample cleaned text with a specific image URL
    cleaned_text = """
TITLE:
Yellow Split Pea Purée

NOTES:
A delicious Mediterranean dip.

---

METADATA:
NATIONALITY: Mediterranean
AUTHOR: Yotam Ottolenghi
BOOK: Ottolenghi Books
QUALITY_SCORE: 95

SELECTED IMAGE URL:
https://books.ottolenghi.co.uk/wp-content/uploads/2021/08/035_yellowpeapuree_2025-031-878x1024.jpg

SPECIAL EQUIPMENT:
- Food processor

INGREDIENTS:
- 200g yellow split peas
- 1 onion
- 2 tbsp capers

INSTRUCTIONS:
1. Cook the split peas for **25min**.
2. Fry the onions until golden.
3. Blend in food processor.
"""
    
    # Generate metadata
    recipe_base = await generate_metadata(model, cleaned_text)
    
    # Verify the image URL is correctly extracted
    assert str(recipe_base.metadata.sourceImageUrl) == "https://books.ottolenghi.co.uk/wp-content/uploads/2021/08/035_yellowpeapuree_2025-031-878x1024.jpg"
    print("✅ Image URL extraction test passed")

@pytest.mark.asyncio
async def test_metadata_rejects_missing_image(model):
    """Test that metadata generation rejects recipes without an image URL."""
    # Sample cleaned text without an image URL
    cleaned_text = """
TITLE:
Yellow Split Pea Purée

NOTES:
A delicious Mediterranean dip.

---

METADATA:
NATIONALITY: Mediterranean
AUTHOR: Yotam Ottolenghi
BOOK: Ottolenghi Books
QUALITY_SCORE: 95

SELECTED IMAGE URL:

SPECIAL EQUIPMENT:
- Food processor

INGREDIENTS:
- 200g yellow split peas
- 1 onion
- 2 tbsp capers

INSTRUCTIONS:
1. Cook the split peas for **25min**.
2. Fry the onions until golden.
3. Blend in food processor.
"""
    
    print(f"\n[DEBUG TEST] Testing rejection of empty image URL")
    
    # Test that metadata generation raises an error
    try:
        result = await generate_metadata(model, cleaned_text)
        print(f"[ERROR] generate_metadata did not raise an error!")
        assert False, "Should have raised RecipeRejectedError"
    except RecipeRejectedError as e:
        print(f"[SUCCESS] Correctly raised RecipeRejectedError: {str(e)}")
        assert "image" in str(e).lower() or "url" in str(e).lower()
        print("✅ Missing image rejection test passed")
    except Exception as e:
        print(f"[ERROR] Raised wrong exception: {type(e).__name__}: {str(e)}")

@pytest.mark.asyncio
async def test_metadata_rejects_empty_image_url(model):
    """Test that metadata generation rejects recipes with an empty image URL string."""
    # Sample cleaned text with an empty image URL
    cleaned_text = """
TITLE:
Yellow Split Pea Purée

NOTES:
A delicious Mediterranean dip.

---

METADATA:
NATIONALITY: Mediterranean
AUTHOR: Yotam Ottolenghi
BOOK: Ottolenghi Books
QUALITY_SCORE: 95

SELECTED IMAGE URL:
""

SPECIAL EQUIPMENT:
- Food processor

INGREDIENTS:
- 200g yellow split peas
- 1 onion
- 2 tbsp capers

INSTRUCTIONS:
1. Cook the split peas for **25min**.
2. Fry the onions until golden.
3. Blend in food processor.
"""
    
    print(f"\n[DEBUG TEST] Testing rejection of empty image URL string")
    
    # Test that metadata generation raises an error
    try:
        result = await generate_metadata(model, cleaned_text)
        print(f"[ERROR] generate_metadata did not raise an error!")
        assert False, "Should have raised RecipeRejectedError"
    except RecipeRejectedError as e:
        print(f"[SUCCESS] Correctly raised RecipeRejectedError: {str(e)}")
        assert "image" in str(e).lower() or "url" in str(e).lower()
        print("✅ Empty image URL rejection test passed")
    except Exception as e:
        print(f"[ERROR] Raised wrong exception: {type(e).__name__}: {str(e)}")

@pytest.mark.asyncio
async def test_metadata_extracts_svg_image_url(model):
    """Test that metadata generation correctly extracts SVG image URLs."""
    # First clean the recipe with SVG
    cleaned_text = await cleanup_recipe(model, SAMPLE_RECIPE_SVG, [])
    
    # Generate metadata
    recipe_base = await generate_metadata(model, cleaned_text)
    
    # Verify the SVG image URL is correctly extracted
    assert recipe_base.metadata.sourceImageUrl is not None
    assert str(recipe_base.metadata.sourceImageUrl).endswith('.svg'), "Should extract SVG image URL"
    print("✅ SVG image URL extraction test passed")

@pytest.mark.asyncio
async def test_graph(model, cleaned_text, recipe_base):
    """Test that graph generation returns a valid LLMRecipeGraph"""
    # Generate graph
    recipe_graph = await generate_graph(model, recipe_base, cleaned_text)
    
    # Verify it's the right type
    assert isinstance(recipe_graph, LLMRecipeGraph)
    assert len(recipe_graph.steps) > 0
    assert recipe_graph.final_state is not None
    
    # Verify subRecipe field is present in steps
    for step in recipe_graph.steps:
        assert hasattr(step, 'subRecipe'), "Step is missing subRecipe field"
        assert isinstance(step.subRecipe, str), "subRecipe must be a string"
    
    print("✅ Graph test passed")

async def run_tests():
    """Run all tests"""
    print("\n🧪 Running format validation tests...")
    
    # Créer le modèle une seule fois et le réutiliser
    load_dotenv()
    model = get_model(DEFAULT_MODEL)
    
    print("\n1️⃣ Testing cleanup service...")
    await test_cleanup(model)
    
    print("\n2️⃣ Testing login page rejection...")
    await test_cleanup_rejects_login_page(model)
    
    print("\n3️⃣ Testing metadata service...")
    # Préparer le contexte pour ce test
    cleaned_text = await cleanup_recipe(model, SAMPLE_RECIPE, [])
    await test_metadata(model, cleaned_text)
    
    print("\n4️⃣ Testing image URL extraction...")
    await test_metadata_extracts_image_url(model)
    
    print("\n5️⃣ Testing SVG image URL extraction...")
    await test_metadata_extracts_svg_image_url(model)
    
    print("\n6️⃣ Testing missing image rejection...")
    await test_metadata_rejects_missing_image(model)
    
    print("\n7️⃣ Testing empty image URL rejection...")
    await test_metadata_rejects_empty_image_url(model)
    
    print("\n8️⃣ Testing graph service...")
    # Préparer le contexte pour ce test
    cleaned_text = await cleanup_recipe(model, SAMPLE_RECIPE, [])
    recipe_base = await generate_metadata(model, cleaned_text)
    await test_graph(model, cleaned_text, recipe_base)
    
    print("\n✨ All tests passed!")

if __name__ == "__main__":
    asyncio.run(run_tests()) 