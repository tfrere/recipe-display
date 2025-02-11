"""Recipe generator using structured output and Deepseek"""
import asyncio
import json
import os
from dotenv import load_dotenv

from .models.recipe import LLMRecipe, LLMRecipeBase, LLMRecipeGraph, LLMMetadata
from .providers.deepseek_model import StreamingDeepseekModel
from .services.cleanup import cleanup_recipe
from .services.metadata import generate_metadata
from .services.graph import generate_graph

async def generate_recipe(recipe_text: str) -> tuple[str, LLMRecipeBase, LLMRecipeGraph]:
    """Generate a complete recipe structure from text"""
    # Load environment variables
    load_dotenv()
    
    # Create our custom streaming model
    model = StreamingDeepseekModel(
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )
    
    try:
        # Step 1: Clean up the recipe
        cleaned_text = await cleanup_recipe(model, recipe_text)
            
        # Step 2: Generate recipe base
        recipe_base = await generate_metadata(model, cleaned_text)
        
        # Step 3: Generate recipe graph
        recipe_graph = await generate_graph(model, recipe_base, cleaned_text)
        
        return cleaned_text, recipe_base, recipe_graph
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, '__cause__'):
            print(f"Caused by: {str(e.__cause__)}")
        raise

async def test_graph_generation():
    """Test the graph generation step independently"""
    # Load environment variables
    load_dotenv()
    
    # Create model
    model = StreamingDeepseekModel(
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )
    
    # Sample cleaned text from previous step
    cleaned_text = """
TITLE:
Classic Chocolate Cake

NOTES:
A rich and moist chocolate cake that serves 8 people.

---

METADATA:
NATIONALITY: 
AUTHOR: 
BOOK: 
QUALITY_SCORE: 85

SELECTED IMAGE URL:
https://www.recipe.com/images/classic-chocolate-cake.png

SPECIAL EQUIPMENT:
- Cake tin

INGREDIENTS:
- 200g flour
- 50g cocoa powder
- 200g sugar
- 2 eggs
- 100ml milk
- 100g butter
- 1 tsp baking powder

INSTRUCTIONS:
1. Preheat the oven to **180°C**.
2. Mix the flour, cocoa powder, sugar, and baking powder in a bowl.
3. Add the eggs, milk, and butter to the dry ingredients and mix well until combined.
4. Pour the batter into a greased cake tin.
5. Bake for **30min** or until a toothpick inserted into the center comes out clean.
"""
    
    # Sample recipe base from previous step
    recipe_base = LLMRecipeBase(
        metadata=LLMMetadata(
            title="Classic Chocolate Cake",
            description="A rich and moist chocolate cake that serves 8 people",
            servings=8,
            recipeType="dessert",
            sourceImageUrl="https://www.recipe.com/images/classic-chocolate-cake.png",
            notes=[],
            nationality="",
            author="",
            bookTitle=""
        ),
        ingredients=[
            {"id": "ing1", "name": "flour", "category": "pantry"},
            {"id": "ing2", "name": "cocoa powder", "category": "pantry"},
            {"id": "ing3", "name": "sugar", "category": "pantry"},
            {"id": "ing4", "name": "eggs", "category": "egg"},
            {"id": "ing5", "name": "milk", "category": "dairy"},
            {"id": "ing6", "name": "butter", "category": "dairy"},
            {"id": "ing7", "name": "baking powder", "category": "pantry"}
        ],
        tools=["cake tin"]
    )
    
    try:
        # Test graph generation
        recipe_graph = await generate_graph(model, recipe_base, cleaned_text)
        print("\nGraph generation test completed successfully!")
        print(json.dumps(recipe_graph.model_dump(), indent=2))
        
    except Exception as e:
        print(f"\nError during graph generation test: {str(e)}")
        if hasattr(e, '__cause__'):
            print(f"Caused by: {str(e.__cause__)}")
        raise

if __name__ == "__main__":
    # Run the graph generation test
    asyncio.run(test_graph_generation()) 