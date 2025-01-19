import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ..services.recipe_structurer import RecipeStructurer
from ..models.text_content import TextContent
from ..models.recipe import Recipe
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime

class MockProgressService:
    async def update_step(
        self,
        progress_id: str,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        if details:
            print(details, end="", flush=True)

def load_recipe_files(input_dir: str, recipe_slug: str) -> Tuple[str, Optional[bytes]]:
    """Load recipe text and image files from input directory."""
    input_path = Path(input_dir)
    
    # Load text content
    text_file = input_path / f"{recipe_slug}.txt"
    if not text_file.exists():
        raise FileNotFoundError(f"Recipe text file not found: {text_file}")
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    # Try to load image if it exists
    image_data = None
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        image_file = input_path / f"{recipe_slug}{ext}"
        if image_file.exists():
            with open(image_file, 'rb') as f:
                image_data = f.read()
            break
    
    return text_content, image_data

async def test_recipe_structurer(input_dir: str, recipe_slug: str):
    # Load environment variables
    load_dotenv()
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create a RecipeStructurer instance
    structurer = RecipeStructurer(client)
    
    try:
        # Load recipe files
        text_content, image_data = load_recipe_files(input_dir, recipe_slug)
        
        # Create a TextContent
        content = TextContent(
            main_content=text_content,
            selected_image_url=None
        )
        
        # Create a mock progress service
        progress_service = MockProgressService()
        
        # Generate the structured recipe
        recipe_json = await structurer.generate_structured_recipe(
            content=content,
            source_url="",  # No source URL for text content
            image_urls=[],  # No image URLs for text content
            progress_service=progress_service,
            progress_id="test_progress"
        )
        
        # Validate the recipe with Pydantic model
        recipe = Recipe(**recipe_json)
        
        # Basic assertions
        assert recipe.metadata.title is not None, "Recipe should have a title"
        assert recipe.metadata.description is not None, "Recipe should have a description"
        assert recipe.metadata.servings > 0, "Recipe should have servings"
        assert len(recipe.ingredients) > 0, "Recipe should have ingredients"
        assert len(recipe.subRecipes) > 0, "Recipe should have sub-recipes"
        assert recipe.metadata.totalTime > 0, "Recipe should have total time"
        
        # Create results directory if it doesn't exist
        output_dir = Path(__file__).parent.parent.parent / "data" / "tests" / "structure" / "output"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save recipe to file
        result_file = output_dir / f"{recipe_slug}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(recipe_json, f, indent=2, ensure_ascii=False)
        
        print(f"\nRecipe saved to: {result_file}")
        print("\nStructuring successful!")
        
    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # Save error to file
        output_dir = Path(__file__).parent.parent.parent / "data" / "tests" / "structure" / "output"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        error_file = output_dir / f"{recipe_slug}.error.json"
        
        error_results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_message": error_message
        }
        
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_results, f, indent=2, ensure_ascii=False)
            
        print(f"\nError saved to: {error_file}")
        raise

if __name__ == "__main__":
    # Get first txt file from cleanup/output directory
    input_directory = str(Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "output")
    
    # Get first txt file from the directory
    input_path = Path(input_directory)
    txt_files = list(input_path.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No txt files found in {input_directory}")
    
    # Get the recipe slug from the first file
    recipe_slug = txt_files[0].stem
    
    print(f"\nProcessing recipe: {recipe_slug}")
    print("=" * 80)
    
    asyncio.run(test_recipe_structurer(input_directory, recipe_slug))
