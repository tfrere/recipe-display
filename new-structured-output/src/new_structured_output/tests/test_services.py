"""Simple format validation tests for recipe services"""
import asyncio
import os
from dotenv import load_dotenv

from ..providers.deepseek_model import StreamingDeepseekModel
from ..models.recipe import LLMRecipeBase, LLMRecipeGraph, LLMMetadata
from ..services.cleanup import cleanup_recipe
from ..services.metadata import generate_metadata
from ..services.graph import generate_graph

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

async def test_cleanup():
    """Test that cleanup returns a properly formatted string"""
    load_dotenv()
    model = StreamingDeepseekModel(api_key=os.getenv("DEEPSEEK_API_KEY"))
    
    cleaned_text = await cleanup_recipe(model, SAMPLE_RECIPE)
    
    # Simple format checks
    assert "TITLE:" in cleaned_text
    assert "INGREDIENTS:" in cleaned_text
    assert "INSTRUCTIONS:" in cleaned_text
    print("✅ Cleanup test passed")
    return cleaned_text, model

async def test_metadata(cleaned_text: str, model: StreamingDeepseekModel):
    """Test that metadata generation returns a valid LLMRecipeBase"""
    # Generate metadata directly from cleaned text
    recipe_base = await generate_metadata(model, cleaned_text)
    
    # Verify it's the right type
    assert isinstance(recipe_base, LLMRecipeBase)
    assert isinstance(recipe_base.metadata, LLMMetadata)
    assert len(recipe_base.ingredients) > 0
    print("✅ Metadata test passed")
    return recipe_base

async def test_graph(cleaned_text: str, model: StreamingDeepseekModel, recipe_base: LLMRecipeBase):
    """Test that graph generation returns a valid LLMRecipeGraph"""
    # Generate graph
    recipe_graph = await generate_graph(model, recipe_base, cleaned_text)
    
    # Verify it's the right type
    assert isinstance(recipe_graph, LLMRecipeGraph)
    assert len(recipe_graph.steps) > 0
    assert recipe_graph.final_state is not None
    print("✅ Graph test passed")

async def run_tests():
    """Run all tests"""
    print("\n🧪 Running format validation tests...")
    
    print("\n1️⃣ Testing cleanup service...")
    cleaned_text, model = await test_cleanup()
    
    print("\n2️⃣ Testing metadata service...")
    recipe_base = await test_metadata(cleaned_text, model)
    
    print("\n3️⃣ Testing graph service...")
    await test_graph(cleaned_text, model, recipe_base)
    
    print("\n✨ All tests passed!")

if __name__ == "__main__":
    asyncio.run(run_tests()) 