"""Recipe generator using structured output and LLMs"""
import asyncio
import json
import os
from pathlib import Path
from typing import Literal, List, Optional, Callable, Awaitable, Tuple
from dotenv import load_dotenv

from .models.recipe import LLMRecipe, LLMRecipeBase, LLMRecipeGraph, LLMMetadata
from .providers.deepseek_model import StreamingDeepseekModel
from .providers.mistral_model import StreamingMistralModel
from .providers.huggingface_model import StreamingHuggingFaceModel
from .services.cleanup import cleanup_recipe
from .services.metadata import generate_metadata
from .services.graph import generate_graph
from .constants import DEFAULT_MODEL

def get_model(provider: Literal["deepseek", "mistral", "huggingface"]) -> StreamingDeepseekModel | StreamingMistralModel | StreamingHuggingFaceModel:
    """Get the appropriate model based on provider"""
    if provider == "deepseek":
        return StreamingDeepseekModel(
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
    elif provider == "huggingface":
        return StreamingHuggingFaceModel(
            api_key=os.getenv("HF_TOKEN")
        )
    else:  # mistral
        return StreamingMistralModel(
            api_key=os.getenv("MISTRAL_API_KEY")
        )

async def generate_recipe(
    recipe_text: str,
    image_urls: Optional[List[str]] = None,
    provider: str = DEFAULT_MODEL,
    progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> Tuple[str, LLMRecipeBase, LLMRecipeGraph]:
    """
    Generate a complete recipe structure from text.
    
    Args:
        recipe_text: The raw text of the recipe
        image_urls: Optional list of image URLs
        provider: The model provider to use (e.g. "deepseek" or "mistral")
        progress_callback: Optional callback for streaming progress updates
        
    Returns:
        Tuple of (cleaned_recipe_text, recipe_base, recipe_graph)
    """
    if progress_callback:
        await progress_callback("Cleaning up recipe text")
    
    print(f"[DEBUG] generate_recipe called with provider: {provider}")
    print(f"[DEBUG] Recipe text length: {len(recipe_text)}")
    print(f"[DEBUG] Recipe text preview: {recipe_text[:200]}...")
    print(f"[DEBUG] Number of images: {len(image_urls or [])}")
    
    # Create our custom streaming model
    model = get_model(provider)
    print(f"[DEBUG] Model created: {type(model)}")
    
    try:
        # Step 1: Clean up the recipe
        if progress_callback:
            await progress_callback("Cleaning up recipe text")
        
        print("[DEBUG] Starting recipe cleanup...")
        cleaned_text = await cleanup_recipe(model, recipe_text, image_urls)
        print(f"[DEBUG] Cleanup completed, result length: {len(cleaned_text)}")
        print(f"[DEBUG] Cleaned text preview: {cleaned_text[:200]}...")
            
        # Step 2: Generate recipe base
        if progress_callback:
            await progress_callback("Génération des métadonnées et des ingrédients")
        
        print("[DEBUG] Starting metadata generation...")
        recipe_base = await generate_metadata(model, cleaned_text)
        print("[DEBUG] Metadata generation completed")
        
        # Step 3: Generate recipe graph
        if progress_callback:
            await progress_callback("Génération des étapes et des états d'ingrédients")
        
        print("[DEBUG] Starting graph generation...")
        recipe_graph = await generate_graph(model, recipe_base, cleaned_text)
        print("[DEBUG] Graph generation completed")
        
        return cleaned_text, recipe_base, recipe_graph
        
    except Exception as e:
        print(f"\n[ERROR] Error in generate_recipe: {str(e)}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        print(f"[ERROR] Error location: {e.__traceback__.tb_frame.f_code.co_filename}:{e.__traceback__.tb_lineno}")
        if hasattr(e, '__cause__'):
            print(f"[ERROR] Caused by: {str(e.__cause__)}")
        raise

async def test_graph_generation():
    """Test the graph generation step independently"""
    # Load environment variables
    load_dotenv()
    
    # Create model using default provider
    model = get_model(DEFAULT_MODEL)
    
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