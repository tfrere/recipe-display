import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ..services.content_cleaner import ContentCleaner
from ..models.text_content import TextContent
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

async def test_cleanup_recipe(input_dir: str, recipe_slug: str):
    # Load environment variables
    load_dotenv()
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create a ContentCleaner instance
    cleaner = ContentCleaner(client)
    
    try:
        # Load recipe files
        text_content, image_data = load_recipe_files(input_dir, recipe_slug)
        
        # Create a mock progress service
        progress_service = MockProgressService()
        
        # Define progress callback
        async def on_progress(content: str):
            await progress_service.update_step(
                progress_id="test_progress",
                step="cleanup_content",
                status="in_progress",
                progress=50,
                details=content
            )
        
        print("\nStarting cleanup...")
        print("=" * 80)
        
        # Clean the recipe content
        cleaned_content = await cleaner.clean_text_content(
            text=text_content,
            on_progress=on_progress
        )
        
        print("\n" + "=" * 80)
        
        # Create output directory if it doesn't exist
        output_dir = Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "output"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save cleaned content to file
        output_file = output_dir / f"{recipe_slug}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content.main_content)
        
        print(f"\nCleaned recipe saved to: {output_file}")
        print("\nCleanup successful!")
        
    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # Save error to file
        output_dir = Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "output"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        error_file = output_dir / f"{recipe_slug}.error.txt"
        
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Error occurred at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Error message: {error_message}\n")
            
        print(f"\nError saved to: {error_file}")
        raise

if __name__ == "__main__":
    # Example usage
    input_directory = str(Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "input")  # Chemin vers le dossier contenant les recettes
    recipe_slug = "blanquette-de-veau"  # Slug de la recette à tester
    
    asyncio.run(test_cleanup_recipe(input_directory, recipe_slug)) 