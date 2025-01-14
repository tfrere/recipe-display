import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ..services.recipe_structurer import RecipeStructurer
from ..models.web_content import WebContent

async def test_recipe_structurer():
    # Load environment variables
    load_dotenv()
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create a RecipeStructurer instance
    structurer = RecipeStructurer(client)
    
    # Create a sample WebContent
    web_content = WebContent(
        title="Test Recipe",
        main_content="""
        Here's a simple recipe for chocolate cake:
        
        Ingredients:
        - 2 cups flour
        - 1 cup sugar
        - 1/2 cup cocoa powder
        - 2 eggs
        - 1 cup milk
        
        Instructions:
        1. Mix dry ingredients
        2. Add wet ingredients
        3. Bake at 350°F for 30 minutes
        """,
        image_urls=["https://example.com/image.jpg"]
    )
    
    # Define a simple progress callback
    async def on_progress(content: str, progress: int):
        print(f"Progress {progress}%: {content[:100]}...")  # Print first 100 chars
    
    try:
        # Generate the structured recipe
        recipe_json = await structurer.generate_structured_recipe(
            web_content=web_content,
            source_url="https://example.com/recipe",
            image_urls=["https://example.com/image.jpg"],
            progress_service=None,
            progress_id=None
        )
        
        # Print the result
        print("\nFinal Recipe JSON:")
        print(json.dumps(recipe_json, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_recipe_structurer())
