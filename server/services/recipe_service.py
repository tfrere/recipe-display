from fastapi import HTTPException
from pathlib import Path
import json
import os
import aiofiles
import asyncio
import base64
from typing import Dict, Any, Optional, List, Literal
from recipe_generator import RecipeGenerator
from services.progress_service import ProgressService
from datetime import datetime
import glob

# Create a single instance of ProgressService to be shared
_progress_service = ProgressService()

class RecipeExistsError(Exception):
    """Raised when trying to generate a recipe that already exists."""
    pass

class RecipeService:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.recipes_path = self.base_path / "recipes"
        self.images_path = self.recipes_path / "images"
        self.auth_presets_path = self.base_path / "auth_presets.json"
        self._ensure_directories()
        
        # Initialize services
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.generator = RecipeGenerator(
            api_key=api_key,
            base_path=self.base_path,
            images_path=self.images_path,
            recipes_path=self.recipes_path
        )
        self.progress_service = _progress_service
        
        # Task management
        self.generation_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_lock = asyncio.Lock()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        try:
            # Create main directories
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.recipes_path.mkdir(parents=True, exist_ok=True)
            
            # Create image subdirectories
            images_path = self.recipes_path / "images"
            images_path.mkdir(parents=True, exist_ok=True)
            (images_path / "original").mkdir(parents=True, exist_ok=True)
            for size in ["thumbnail", "small", "medium", "large"]:
                (images_path / size).mkdir(parents=True, exist_ok=True)
            
            # Create errors directory
            (self.recipes_path / "errors").mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            raise ValueError(f"Cannot create required directories: {e}")

    async def _cleanup_task(self, progress_id: str, task: asyncio.Task) -> None:
        """Clean up a completed generation task and handle any errors."""
        async with self._cleanup_lock:
            self.generation_tasks.pop(progress_id, None)
            try:
                if task.done() and not task.cancelled():
                    exc = task.exception()
                    if exc:
                        await self.progress_service.set_error(
                            progress_id,
                            f"Task failed: {str(exc)}"
                        )
            except asyncio.CancelledError:
                await self.progress_service.set_error(
                    progress_id,
                    "Generation was cancelled"
                )

    async def _find_recipe_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Find a recipe by its source URL."""
        for file_path in self.recipes_path.glob("*.recipe.json"):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    recipe = json.loads(content)
                    if recipe.get("metadata", {}).get("sourceUrl") == url:
                        return recipe
            except Exception:
                continue
        return None

    async def get_auth_presets(self) -> Dict[str, Any]:
        """Get authentication presets."""
        try:
            if not self.auth_presets_path.exists():
                return {}
            
            async with aiofiles.open(self.auth_presets_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading auth presets: {str(e)}"
            )

    async def get_recipe(self, slug: str) -> Dict[str, Any]:
        """Get a recipe by its slug."""
        file_path = self.recipes_path / f"{slug}.recipe.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                recipe = json.loads(content)
                
            # Add slug at root level for easier access
            recipe["slug"] = recipe["metadata"]["slug"]
            recipe["title"] = recipe["metadata"]["title"]
            
            return recipe
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error reading recipe: {str(e)}"
            )

    async def list_recipes(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """Get list of all recipes with their metadata."""
        try:
            # Get list of all recipe files
            recipe_files = glob.glob(os.path.join(self.recipes_path, "*.recipe.json"))
            recipes = []

            # Get list of public authors
            authors_file = os.path.join(os.path.dirname(self.recipes_path), "authors.json")
            with open(authors_file, "r") as f:
                authors_data = json.load(f)
                public_authors = authors_data["public"]

            # Read each recipe file
            for recipe_file in recipe_files:
                # Skip auth presets file
                if os.path.basename(recipe_file) == "auth_presets.json":
                    continue

                try:
                    with open(recipe_file, "r") as f:
                        recipe = json.load(f)
                        
                        # Filter recipes by author if not include_private
                        if not include_private and recipe["metadata"]["author"] not in public_authors:
                            continue
                            
                        recipes.append({
                            "id": os.path.basename(recipe_file).replace(".recipe.json", ""),
                            "title": recipe["metadata"]["title"],
                            "imageUrl": recipe["metadata"]["imageUrl"],
                            "description": recipe["metadata"]["description"],
                            "bookTitle": recipe["metadata"].get("bookTitle", ""),
                            "author": recipe["metadata"]["author"],
                            "diets": recipe["metadata"]["diets"],
                            "seasons": recipe["metadata"]["seasons"],
                            "recipeType": recipe["metadata"]["recipeType"],
                            "ingredients": [ing["name"] for ing in recipe.get("ingredients", [])],
                            "totalTime": recipe["metadata"].get("totalTime", 0.0),
                            "quick": recipe["metadata"].get("quick", False),
                            "difficulty": recipe["metadata"].get("difficulty", ""),
                            "slug": os.path.basename(recipe_file).replace(".recipe.json", "")
                        })
                except Exception as e:
                    print(f"Error reading recipe file {recipe_file}: {str(e)}")
                    continue

            return recipes

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error listing recipes: {str(e)}"
            )

    async def delete_all_recipes(self) -> None:
        """Delete all recipes and their associated images."""
        try:
            # Delete all recipe JSON files
            for recipe_file in self.recipes_path.glob("*.json"):
                if recipe_file.name != "auth_presets.json":  # Skip auth presets file
                    recipe_file.unlink()
            
            # Delete all images in the images directory
            for image_file in self.images_path.glob("*"):
                if image_file.is_file():
                    image_file.unlink()
                    
        except Exception as e:
            print(f"Error deleting all recipes: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_recipe(self, slug: str) -> None:
        """Delete a specific recipe and its associated images."""
        try:
            # Get recipe to find image filename
            recipe_file = self.recipes_path / f"{slug}.recipe.json"
            if not recipe_file.exists():
                raise HTTPException(status_code=404, detail="Recipe not found")

            # Read recipe to get image filename
            async with aiofiles.open(recipe_file, 'r') as f:
                content = await f.read()
                recipe = json.loads(content)
                image_url = recipe.get("metadata", {}).get("imageUrl", "")
                if image_url:
                    image_filename = image_url.split("/")[-1].split(".")[0]
                    
                    # Delete all image sizes
                    for size in ["original", "thumbnail", "small", "medium", "large"]:
                        image_dir = self.images_path / size
                        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]:
                            image_path = image_dir / f"{image_filename}{ext}"
                            if image_path.exists():
                                image_path.unlink()

            # Delete recipe file
            recipe_file.unlink()

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error deleting recipe: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_recipe_generation(
        self,
        progress_id: str,
        url: str,
        credentials: Optional[Dict[str, Any]] = None
    ) -> None:
        """Process the recipe generation in background."""
        print(f"[INFO] Starting recipe generation for progress ID: {progress_id}")
        
        try:
            # Check if recipe already exists
            await self.progress_service.update_step(
                progress_id,
                "check_existence",
                "in_progress",
                0,
                "Checking if recipe already exists..."
            )
            
            existing_recipe = await self._find_recipe_by_url(url)
            if existing_recipe:
                await self.progress_service.update_step(
                    progress_id,
                    "check_existence",
                    "completed",
                    100,
                    "Recipe already exists"
                )
                raise RecipeExistsError("Recipe already exists")
            
            await self.progress_service.update_step(
                progress_id,
                "check_existence",
                "completed",
                100,
                "Recipe does not exist yet"
            )

            # Generate recipe
            recipe = await self.generator.generate_from_url(
                url,
                credentials,
                self.progress_service,
                progress_id
            )
            
            # Save recipe
            slug = recipe.get("metadata", {}).get("slug")
            if slug:
                file_path = self.recipes_path / f"{slug}.recipe.json"
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(json.dumps(recipe, indent=2))
            
            # Update progress with recipe and complete
            await self.progress_service.set_recipe(progress_id, recipe)
            await self.progress_service.update_step(
                progress_id,
                "save_recipe",
                "completed",
                100,
                "Recipe saved successfully"
            )
            
            print(f"[INFO] Recipe generation completed for progress ID: {progress_id}")
            
        except Exception as e:
            error_msg = f"Recipe generation failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            await self.progress_service.set_error(progress_id, error_msg)
            
            # Update current step status to error
            progress = await self.progress_service.get_progress(progress_id)
            if progress and progress.current_step:
                await self.progress_service.update_step(
                    progress_id,
                    progress.current_step,
                    "error",
                    0,
                    error_msg
                )
            raise

    async def generate_recipe(
        self,
        import_type: Literal["url", "text"],
        url: Optional[str] = None,
        text: Optional[str] = None,
        image: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a recipe from either a URL or text content."""
        print("[DEBUG] Starting recipe generation")
        print(f"[DEBUG] Import type: {import_type}")
        print(f"[DEBUG] URL: {url}")
        print(f"[DEBUG] Text length: {len(text) if text else 0}")
        print(f"[DEBUG] Has image: {bool(image)}")
        
        try:
            # Create progress ID with import type
            progress_id = await self.progress_service.create_progress(import_type)
            print(f"[DEBUG] Created progress ID: {progress_id}")

            # Create and start the generation task based on type
            if import_type == "url":
                if not url:
                    raise ValueError("URL is required for URL import type")
                print("[DEBUG] Starting URL import")
                task = asyncio.create_task(
                    self._process_url_recipe_generation(progress_id, url, credentials)
                )
            else:
                if not text:
                    raise ValueError("Text is required for text import type")
                print("[DEBUG] Starting text import")
                task = asyncio.create_task(
                    self._process_text_recipe_generation(progress_id, text, image)
                )

            # Store task and set up cleanup
            self.generation_tasks[progress_id] = task
            task.add_done_callback(
                lambda t: asyncio.create_task(self._cleanup_task(progress_id, t))
            )
            print(f"[DEBUG] Task created and stored with ID: {progress_id}")

            return progress_id
            
        except Exception as e:
            print(f"[ERROR] Failed to start recipe generation: {str(e)}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
            raise

    async def _process_url_recipe_generation(
        self,
        progress_id: str,
        url: str,
        credentials: Optional[Dict[str, Any]] = None
    ) -> None:
        """Process the recipe generation from URL in background."""
        try:
            # Prepare content (includes existence check, URL fetching and content extraction)
            await self.progress_service.update_step(
                progress_id,
                "prepare_content",
                "in_progress",
                0,
                "Preparing content..."
            )
            
            # Check if recipe exists
            existing_recipe = await self._find_recipe_by_url(url)
            if existing_recipe:
                raise RecipeExistsError(
                    f"Recipe from URL {url} already exists"
                )

            # Generate recipe from URL
            recipe = await self.generator.generate_from_url(
                url=url,
                credentials=credentials,
                progress_service=self.progress_service,
                progress_id=progress_id
            )

            await self.progress_service.update_step(
                progress_id,
                "prepare_content",
                "completed",
                100,
                "Content prepared successfully"
            )

            # Save recipe in progress
            await self.progress_service.set_recipe(progress_id, recipe)

        except RecipeExistsError as e:
            await self.progress_service.set_error(progress_id, str(e))
            raise
        except Exception as e:
            await self.progress_service.set_error(progress_id, str(e))
            raise

    async def _process_text_recipe_generation(
        self,
        progress_id: str,
        text: str,
        image: Optional[str] = None
    ) -> None:
        """Process the recipe generation from text in background."""
        try:
            # Check existence (based on content hash or similar)
            await self.progress_service.update_step(
                progress_id,
                "check_existence",
                "in_progress",
                0,
                "Vérification si la recette existe déjà..."
            )
            
            # TODO: Implement content-based duplicate check
            
            await self.progress_service.update_step(
                progress_id,
                "check_existence",
                "completed",
                20,
                "Vérification terminée"
            )

            # Process image if provided
            image_data = None
            if image:
                # Remove data:image/jpeg;base64, prefix if present
                if "base64," in image:
                    image = image.split("base64,")[1]
                image_data = base64.b64decode(image)

            # Generate recipe from text
            recipe = await self.generator.generate_from_text(
                text=text,
                image_data=image_data,
                progress_service=self.progress_service,
                progress_id=progress_id
            )

            # Mark progress as completed
            await self.progress_service.update_step(
                progress_id,
                "save_recipe",
                "completed",
                100,
                "Recette sauvegardée avec succès"
            )
            await self.progress_service.set_recipe(progress_id, recipe)

        except Exception as e:
            await self.progress_service.set_error(progress_id, str(e))
            raise

    async def cancel_generation(self, progress_id: str) -> None:
        """Cancel an ongoing recipe generation."""
        if progress_id in self.generation_tasks:
            task = self.generation_tasks[progress_id]
            if not task.done():
                task.cancel()
                await self.progress_service.set_error(
                    progress_id,
                    "Generation cancelled by user"
                )

    async def get_generation_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the progress of a recipe generation."""
        progress = await self.progress_service.get_progress(task_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"Progress not found for ID: {task_id}")
        
        # Check if task is still running
        task = self.generation_tasks.get(task_id)
        if task and task.done() and task.exception():
            # If task failed, update progress with error
            error = str(task.exception())
            await self.progress_service.set_error(task_id, error)
            progress = await self.progress_service.get_progress(task_id)
        
        return progress