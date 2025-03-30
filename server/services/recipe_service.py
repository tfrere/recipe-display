from fastapi import HTTPException
from pathlib import Path
import json
import os
import aiofiles
import asyncio
import base64
import re
import sys
from typing import Dict, Any, Optional, List, Literal

# Import our dependencies
from recipe_structurer import RecipeRejectedError
from services.progress_service import ProgressService
from datetime import datetime
import glob
import httpx

# Create a single instance of ProgressService to be shared
_progress_service = ProgressService()

class RecipeExistsError(Exception):
    """Raised when trying to generate a recipe that already exists."""
    pass

class RecipeService:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.recipes_path = self.base_path / "recipes"  # /server/data/recipes
        self.images_path = self.recipes_path / "images"  # /server/data/recipes/images
        self.auth_presets_path = self.base_path / "auth_presets.json"
        self._ensure_directories()
        
        # Initialize progress service
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
            self.images_path.mkdir(parents=True, exist_ok=True)
            
            # Create image subdirectories
            (self.base_path / "images" / "original").mkdir(parents=True, exist_ok=True)
            for size in ["thumbnail", "small", "medium", "large"]:
                (self.base_path / "images" / size).mkdir(parents=True, exist_ok=True)
            
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
                raw_presets = json.loads(content)
                
                # Convert raw presets to AuthPreset format
                presets = {}
                for domain, preset in raw_presets.items():
                    presets[domain] = {
                        "type": preset["type"],
                        "domain": preset["domain"],
                        "values": preset["values"],
                        "description": preset.get("description", "")
                    }
                return presets
                
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
                public_authors = authors_data.get("public", [])

            # Read each recipe file
            for recipe_file in recipe_files:
                # Skip auth presets file
                if os.path.basename(recipe_file) == "auth_presets.json":
                    continue

                try:
                    with open(recipe_file, "r") as f:
                        recipe = json.load(f)
                        metadata = recipe.get("metadata", {})
                        
                        # Filter recipes by author if not include_private
                        author = metadata.get("author", "")
                        if not include_private and author not in public_authors:
                            continue
                            
                        recipes.append({
                            "id": os.path.basename(recipe_file).replace(".recipe.json", ""),
                            "title": metadata.get("title", "Untitled"),
                            "imageUrl": metadata.get("imageUrl", ""),
                            "description": metadata.get("description", ""),
                            "bookTitle": metadata.get("bookTitle", ""),
                            "author": author,
                            "diets": metadata.get("diets", []),
                            "seasons": metadata.get("seasons", []),
                            "recipeType": metadata.get("recipeType", ""),
                            "ingredients": [ing.get("name", "") for ing in recipe.get("ingredients", [])],
                            "totalTime": metadata.get("totalTime", 0.0),
                            "quick": metadata.get("quick", False),
                            "difficulty": metadata.get("difficulty", ""),
                            "slug": metadata.get("slug", os.path.basename(recipe_file).replace(".recipe.json", ""))
                        })
                except Exception as e:
                    print(f"Error reading recipe file {recipe_file}: {str(e)}")
                    continue

            return recipes

        except Exception as e:
            print(f"Error listing recipes: {str(e)}")
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
        """
        Process recipe generation from a URL using the recipe_scraper CLI.
        """
        try:
            # Update step: check_existence
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="check_existence",
                status="in_progress",
                message="Checking if recipe already exists"
            )

            # Check if recipe already exists
            existing_recipe = await self._find_recipe_by_url(url)
            if existing_recipe:
                slug = existing_recipe.get("metadata", {}).get("slug", "")
                if slug:
                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step="check_existence",
                        status="error",
                        message=f"Recipe already exists with slug: {slug}"
                    )
                    raise RecipeExistsError(f"Recipe from this URL already exists with slug: {slug}")
            
            # Mark check_existence as completed
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="check_existence",
                status="completed",
                progress=100,
                message="Recipe does not exist yet"
            )

            # Create a temporary credentials file if needed
            credentials_file = None
            if credentials:
                domain = url.split("//")[-1].split("/")[0]
                credentials_file = self.base_path / f"temp_creds_{progress_id}.json"
                
                # Create a credentials file in the format expected by the CLI
                creds_data = {domain: credentials}
                async with aiofiles.open(credentials_file, 'w') as f:
                    await f.write(json.dumps(creds_data))
                
                print(f"[DEBUG] Created temporary credentials file at: {credentials_file}")

            # Prepare the command
            cmd = [
                "python", "-m", "recipe_scraper.cli",
                "--mode", "url",
                "--url", url,
                "--recipe-output-folder", str(self.recipes_path),
                "--image-output-folder", str(self.images_path),
                "--verbose"  # Enable verbose mode for more detailed logs
            ]
            
            # Add credentials if provided
            if credentials_file:
                cmd.extend(["--credentials", str(credentials_file)])
            
            print(f"[DEBUG] Running command: {' '.join(cmd)}")
            
            # Update step: scrape_content
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="scrape_content",
                status="in_progress",
                message="Fetching recipe content"
            )
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Process output line by line
            current_step = "scrape_content"
            slug = None
            
            async for line in process.stdout:
                line_text = line.decode('utf-8').strip()
                print(f"CLI output: {line_text}")
                
                # Update progress based on log messages
                if ">>> " in line_text:
                    message = line_text.split(">>> ")[1].strip()
                    
                    if "Fetching web content" in message:
                        current_step = "scrape_content"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Structuring" in message:
                        current_step = "structure_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Downloading" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Enriching" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Saving" in message or "sauvegarde" in message.lower():
                        current_step = "save_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message="Saving recipe and image"
                        )
                
                # Extract slug from recipe file path
                if "Recipe successfully saved to:" in line_text:
                    file_path = line_text.split("Recipe successfully saved to:")[1].strip()
                    slug = Path(file_path).stem.replace(".recipe", "")
                    print(f"[DEBUG] Extracted slug: {slug}")
            
            # Read stderr in case there were errors
            stderr_data = await process.stderr.read()
            stderr_text = stderr_data.decode('utf-8').strip()
            if stderr_text:
                print(f"CLI stderr: {stderr_text}")
            
            # Wait for the process to complete
            await process.wait()
            
            # Clean up temporary credentials file
            if credentials_file and credentials_file.exists():
                credentials_file.unlink()
                print(f"[DEBUG] Removed temporary credentials file: {credentials_file}")
            
            # Check if the process succeeded
            if process.returncode != 0:
                error_message = f"Recipe scraper CLI failed with return code {process.returncode}"
                if stderr_text:
                    error_message += f": {stderr_text}"
                
                await self.progress_service.set_error(
                    progress_id,
                    error_message
                )
                return

            # Check if we got a slug
            if not slug:
                await self.progress_service.set_error(
                    progress_id,
                    "Failed to extract recipe slug from CLI output"
                )
                return
            
            # Mark steps as completed
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="scrape_content",
                status="completed",
                progress=100,
                message="Content successfully retrieved"
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="structure_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully structured"
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="save_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully saved"
            )
            
            await self.progress_service.complete(progress_id, {"slug": slug})

        except RecipeExistsError as e:
            await self.progress_service.set_error(
                progress_id, 
                f"Recipe already exists: {str(e)}"
            )
        except RecipeRejectedError as e:
            await self.progress_service.set_error(
                progress_id, 
                f"Recipe was rejected: {str(e)}"
            )
        except Exception as e:
            await self.progress_service.set_error(
                progress_id, 
                f"Error processing recipe: {str(e)}"
            )

    async def _process_text_recipe_generation(
        self,
        progress_id: str,
        recipe_text: str,
        image_url: str
    ) -> None:
        """Process a recipe generation from text input using the recipe_scraper CLI"""
        try:
            # Update step: generate_recipe
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="generate_recipe",
                status="in_progress",
                message="Preparing recipe text"
            )

            # Create a temporary file for the recipe text
            temp_text_file = self.base_path / f"temp_recipe_{progress_id}.txt"
            async with aiofiles.open(temp_text_file, 'w') as f:
                await f.write(recipe_text)
            
            print(f"[DEBUG] Created temporary recipe text file at: {temp_text_file}")
            
            # Prepare the command
            cmd = [
                "python", "-m", "recipe_scraper.cli",
                "--mode", "text",
                "--input-file", str(temp_text_file),
                "--recipe-output-folder", str(self.recipes_path),
                "--image-output-folder", str(self.images_path),
                "--verbose"  # Enable verbose mode for more detailed logs
            ]
            
            print(f"[DEBUG] Running command: {' '.join(cmd)}")
            
            # Update step to indicate we're starting processing
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="generate_recipe",
                status="in_progress",
                message="Processing recipe text"
            )
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Process output line by line
            current_step = "generate_recipe"
            slug = None
            
            async for line in process.stdout:
                line_text = line.decode('utf-8').strip()
                print(f"CLI output: {line_text}")
                
                # Update progress based on log messages
                if ">>> " in line_text:
                    message = line_text.split(">>> ")[1].strip()
                    
                    if "Processing recipe" in message or "Starting recipe" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step="generate_recipe",
                            status="in_progress",
                            message=message
                        )
                    elif "Structuring" in message:
                        current_step = "structure_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Downloading" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Enriching" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message
                        )
                    elif "Saving" in message or "sauvegarde" in message.lower():
                        current_step = "save_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message="Saving recipe and image"
                        )
                
                # Extract slug from recipe file path
                if "Recipe successfully saved to:" in line_text:
                    file_path = line_text.split("Recipe successfully saved to:")[1].strip()
                    slug = Path(file_path).stem.replace(".recipe", "")
                    print(f"[DEBUG] Extracted slug: {slug}")
            
            # Read stderr in case there were errors
            stderr_data = await process.stderr.read()
            stderr_text = stderr_data.decode('utf-8').strip()
            if stderr_text:
                print(f"CLI stderr: {stderr_text}")
            
            # Wait for the process to complete
            await process.wait()
            
            # Clean up temporary text file
            if temp_text_file.exists():
                temp_text_file.unlink()
                print(f"[DEBUG] Removed temporary text file: {temp_text_file}")
            
            # Handle image URL if provided
            if slug and image_url:
                print(f"[DEBUG] Downloading image from URL: {image_url}")
                
                try:
                    # Download the image
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        response = await client.get(image_url)
                        response.raise_for_status()
                        
                        # Determine extension from content-type
                        content_type = response.headers.get("content-type", "").lower()
                        ext = "jpg"  # Default extension
                        
                        if content_type.startswith("image/"):
                            mime_ext = content_type.split("/")[1].split(";")[0]
                            if mime_ext in ["jpeg", "jpg", "png", "gif", "webp"]:
                                ext = mime_ext if mime_ext != "jpeg" else "jpg"
                        
                        # Save image
                        image_path = self.images_path / f"{slug}.{ext}"
                        async with aiofiles.open(image_path, "wb") as f:
                            await f.write(response.content)
                        
                        print(f"[DEBUG] Image saved to: {image_path}")
                        
                        # Update the recipe JSON with the image path
                        recipe_file = self.recipes_path / f"{slug}.recipe.json"
                        if recipe_file.exists():
                            async with aiofiles.open(recipe_file, "r") as f:
                                recipe_data = json.loads(await f.read())
                            
                            # Update image path
                            if "metadata" in recipe_data:
                                recipe_data["metadata"]["image"] = f"images/{slug}.{ext}"
                                
                                # Write back the updated recipe
                                async with aiofiles.open(recipe_file, "w") as f:
                                    await f.write(json.dumps(recipe_data, indent=2))
                                
                                print(f"[DEBUG] Updated recipe file with image path: {recipe_file}")
                except Exception as e:
                    print(f"[ERROR] Failed to download and save image: {str(e)}")
            
            # Check if the process succeeded
            if process.returncode != 0:
                error_message = f"Recipe scraper CLI failed with return code {process.returncode}"
                if stderr_text:
                    error_message += f": {stderr_text}"
                
                await self.progress_service.set_error(
                    progress_id,
                    error_message
                )
                return
            
            # Check if we got a slug
            if not slug:
                await self.progress_service.set_error(
                    progress_id,
                    "Failed to extract recipe slug from CLI output"
                )
                return
            
            # Mark steps as completed
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="generate_recipe",
                status="completed",
                progress=100,
                message="Recipe text successfully processed"
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="structure_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully structured"
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="save_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully saved"
            )
            
            await self.progress_service.complete(progress_id, {"slug": slug})

        except Exception as e:
            await self.progress_service.set_error(
                progress_id,
                f"Error processing recipe text: {str(e)}"
            )

    async def generate_recipe(
        self,
        import_type: Literal["url", "text"],
        url: Optional[str] = None,
        text: Optional[str] = None,
        image: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a recipe from URL or text. Returns a progress ID.
        """
        # Validate input
        if import_type == "url" and not url:
            raise HTTPException(status_code=400, detail="URL is required for URL import")
        elif import_type == "text" and not text:
            raise HTTPException(status_code=400, detail="Text is required for text import")
        
        # Create a progress ID
        progress_id = f"recipe-gen-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"
        
        # Register the progress
        await self.progress_service.register(progress_id)
        
        # Create a task to process the recipe
        if import_type == "url":
            task = asyncio.create_task(
                self._process_recipe_generation(
                    progress_id=progress_id,
                    url=url,
                    credentials=credentials
                )
            )
        else:  # text
            task = asyncio.create_task(
                self._process_text_recipe_generation(
                    progress_id=progress_id,
                    recipe_text=text,
                    image_url=image
                )
            )
        
        # Store the task and set up cleanup
        self.generation_tasks[progress_id] = task
        task.add_done_callback(
            lambda t: asyncio.create_task(self._cleanup_task(progress_id, t))
        )
        
        return progress_id
        
    async def _save_base64_image(self, base64_str: str, slug: str) -> Optional[str]:
        """
        Save a base64 encoded image.
        """
        try:
            # Extract image data from base64 string
            if "," in base64_str:
                _, base64_data = base64_str.split(",", 1)
            else:
                base64_data = base64_str
                
            image_data = base64.b64decode(base64_data)
            
            # Ensure the images directory exists
            self.images_path.mkdir(parents=True, exist_ok=True)
            
            # Save image to the recipes/images directory
            image_path = self.images_path / f"{slug}.jpg"
            async with aiofiles.open(image_path, "wb") as f:
                await f.write(image_data)
                
            # Also save a copy to the original images directory for thumbnails
            original_path = self.base_path / "images" / "original" / f"{slug}.jpg"
            async with aiofiles.open(original_path, "wb") as f:
                await f.write(image_data)
                
            # Return the relative path to be stored in the recipe
            return f"images/{slug}.jpg"
                
        except Exception as e:
            print(f"Error saving base64 image: {e}")
            return None

    async def get_generation_progress(self, task_id: str):
        """
        Get the progress of a recipe generation task by task ID.
        """
        return await self.progress_service.get_progress(task_id)