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
import hashlib

# Import our dependencies
from recipe_structurer import RecipeRejectedError
from services.progress_service import ProgressService
from datetime import datetime
import glob
import httpx
from models.progress import GenerationProgress, GenerationStep

# Create a single instance of ProgressService to be shared
_progress_service = ProgressService()

class RecipeExistsError(Exception):
    """Raised when trying to generate a recipe that already exists."""
    pass

class RecipeService:
    def __init__(self, base_path: str = "data"):
        # Déterminer automatiquement le chemin de base selon l'environnement
        print(f"[DEBUG] Original base_path: {base_path}")
        
        # Vérifier si nous sommes dans un environnement Docker (Railway)
        if os.path.exists('/app'):
            print("[DEBUG] Detected Docker/Railway environment (/app exists)")
            # Si /app/data/recipes existe et contient des fichiers .recipe.json
            if os.path.exists('/app/data/recipes'):
                files = glob.glob('/app/data/recipes/*.recipe.json')
                if files:
                    print(f"[DEBUG] Found {len(files)} recipe files in /app/data/recipes, using this path")
                    self.base_path = Path('/app/data')
                    self.recipes_path = Path('/app/data/recipes')
                    self.images_path = self.recipes_path / "images"
                    self.auth_presets_path = self.base_path / "auth_presets.json"
                    self._ensure_directories()
                    
                    # Initialize progress service and task management
                    self.progress_service = _progress_service
                    self.generation_tasks: Dict[str, asyncio.Task] = {}
                    self._cleanup_lock = asyncio.Lock()
                    return
        
        # Si nous arrivons ici, utiliser le chemin par défaut
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
            
            # Create tmp directory for temporary files
            (self.base_path / "tmp").mkdir(parents=True, exist_ok=True)
            
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
            
            # Ensure totalCookingTime is available at the root level if present in metadata
            if "totalCookingTime" in recipe["metadata"]:
                recipe["totalCookingTime"] = recipe["metadata"]["totalCookingTime"]
            
            return recipe
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error reading recipe: {str(e)}"
            )

    async def list_recipes(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """Get list of all recipes with their metadata."""
        try:
            # DEBUG: Print current paths
            print(f"[DEBUG] Current working directory: {os.getcwd()}")
            print(f"[DEBUG] Base path: {self.base_path} (absolute: {self.base_path.absolute()})")
            print(f"[DEBUG] Recipes path: {self.recipes_path} (absolute: {self.recipes_path.absolute()})")
            print(f"[DEBUG] Searching for recipe files in: {os.path.join(self.recipes_path, '*.recipe.json')}")
            print(f"[DEBUG] include_private parameter: {include_private}")
            
            # Get list of all recipe files
            recipe_files = glob.glob(os.path.join(self.recipes_path, "*.recipe.json"))

            recipes = []

            # Get list of private authors
            private_authors = []
            authors_file = os.path.join(os.path.dirname(self.recipes_path), "authors.json")
            try:
                if os.path.exists(authors_file):
                    with open(authors_file, "r") as f:
                        authors_data = json.load(f)
                        private_authors = authors_data.get("private", [])
                        print(f"[DEBUG] Private authors: {private_authors}")
                else:
                    print(f"Warning: authors.json not found at {authors_file}")
            except Exception as e:
                print(f"Error reading authors file: {str(e)}")
                # Continue with empty private_authors list

            # Read each recipe file
            total_read = 0
            total_private = 0
            total_included = 0
            
            for recipe_file in recipe_files:
                # Skip auth presets file
                if os.path.basename(recipe_file) == "auth_presets.json":
                    continue

                try:
                    total_read += 1
                    with open(recipe_file, "r") as f:
                        recipe_data = json.load(f)
                        metadata = recipe_data.get("metadata", {})
                        
                        # Check if recipe is private (author or sourceUrl contains any private author name)
                        author = metadata.get("author", "").lower()
                        source_url = metadata.get("sourceUrl", "")
                        source_url_lower = source_url.lower() if source_url else ""
                        
                        is_private = any(
                            private_author.lower() in author or 
                            private_author.lower() in source_url_lower 
                            for private_author in private_authors
                        )
                        
                        if is_private:
                            total_private += 1
                            # print(f"[DEBUG] Recipe '{metadata.get('title', 'Unknown')}' is marked as private (author: {author}, url: {source_url})")
                        
                        # Include recipe if it's public or if private access is granted
                        if not is_private or include_private:
                            total_included += 1
                            recipes.append({
                                "title": metadata.get("title", "Untitled"),
                                "sourceImageUrl": metadata.get("sourceImageUrl", ""),
                                "description": metadata.get("description", ""),
                                "bookTitle": metadata.get("bookTitle", ""),
                                "author": metadata.get("author", ""),
                                "diets": metadata.get("diets", []),
                                "seasons": metadata.get("seasons", []),
                                "recipeType": metadata.get("recipeType", ""),
                                "ingredients": [ing.get("name", "") for ing in recipe_data.get("ingredients", [])],
                                "totalTime": metadata.get("totalTime", 0.0),
                                "totalCookingTime": metadata.get("totalCookingTime", 0.0),
                                "quick": metadata.get("quick", False),
                                "difficulty": metadata.get("difficulty", ""),
                                "slug": metadata.get("slug", os.path.basename(recipe_file).replace(".recipe.json", ""))
                            })
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {recipe_file}: {str(e)}")
                    # Skip this file and continue with others
                except Exception as e:
                    print(f"Error processing recipe file {recipe_file}: {str(e)}")
                    # Skip this file and continue with others

            print(f"[DEBUG] Total recipe files read: {total_read}, private: {total_private}, included in results: {total_included}")
            
            # Si aucune recette n'est trouvée, on retourne une liste vide au lieu de lancer une erreur
            if not recipes and len(recipe_files) > 0:
                print(f"[WARNING] No recipes included in results despite having {len(recipe_files)} recipe files. include_private={include_private}")
                
            return recipes

        except Exception as e:
            print(f"Error listing recipes: {str(e)}")
            # Retourner une liste vide au lieu d'une erreur
            print(f"[WARNING] Error occurred but returning empty list instead of error: {str(e)}")
            return []

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
                image_url = recipe.get("metadata", {}).get("sourceImageUrl", "")
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
                tmp_dir = self.base_path / "tmp"
                credentials_file = tmp_dir / f"temp_creds_{progress_id}.json"
                
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
            
            # Pour stocker les logs complets pour chaque étape
            step_logs = {
                "scrape_content": [],
                "structure_recipe": [],
                "save_recipe": []
            }
            
            async for line in process.stdout:
                line_text = line.decode('utf-8').strip()
                print(f"CLI output: {line_text}")
                
                # Ajouter la ligne aux logs de l'étape courante
                step_logs[current_step].append(line_text)
                
                # Mettre à jour les détails de l'étape en cours avec tous les logs accumulés
                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step=current_step,
                    status="in_progress",
                    details="\n".join(step_logs[current_step])
                )
                
                # Update progress based on log messages
                if ">>> " in line_text:
                    message = line_text.split(">>> ")[1].strip()
                    
                    if "Fetching web content" in message:
                        current_step = "scrape_content"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Structuring" in message:
                        current_step = "structure_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Downloading" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Enriching" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Saving" in message or "sauvegarde" in message.lower():
                        current_step = "save_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message="Saving recipe and image",
                            details="\n".join(step_logs[current_step])
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
                # Ajouter stderr aux logs de l'étape actuelle
                step_logs[current_step].append(f"STDERR: {stderr_text}")
                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step=current_step,
                    status="in_progress",
                    details="\n".join(step_logs[current_step])
                )
            
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
                message="Content successfully retrieved",
                details="\n".join(step_logs["scrape_content"])
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="structure_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully structured",
                details="\n".join(step_logs["structure_recipe"])
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="save_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully saved",
                details="\n".join(step_logs["save_recipe"])
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
        image_base64: str
    ) -> None:
        """Process a recipe generation from text input using the recipe_scraper CLI"""
        temp_image_path = None
        try:
            # Update step: check_existence
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="check_existence",
                status="in_progress",
                message="Checking if recipe already exists"
            )
            
            # La vérification d'existence sera effectuée par le CLI recipe_scraper
            # Nous ne faisons que indiquer l'étape comme complétée
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="check_existence",
                status="completed",
                progress=100,
                message="Checking recipe existence in scraper"
            )
            
            # Continue with recipe generation
            # Update step: generate_recipe
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="generate_recipe",
                status="in_progress",
                message="Preparing recipe text"
            )

            # Create a temp directory for images if it doesn't exist
            temp_dir = self.base_path / "tmp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # If image is provided, save it to a temporary location and get the URL
            modified_recipe_text = recipe_text
            if image_base64:
                print(f"[DEBUG] Saving temporary image for recipe generation")
                try:
                    # Extract image data from base64 string
                    if "," in image_base64:
                        _, base64_data = image_base64.split(",", 1)
                    else:
                        base64_data = image_base64
                        
                    image_data = base64.b64decode(base64_data)
                    
                    # Determine image extension from the base64 header
                    ext = "jpg"  # Default
                    if image_base64.startswith("data:image/"):
                        mime_type = image_base64.split(';')[0].split(':')[1]
                        if '/' in mime_type:
                            file_ext = mime_type.split('/')[1]
                            if file_ext in ["jpeg", "jpg", "png", "gif", "webp"]:
                                ext = file_ext if file_ext != "jpeg" else "jpg"
                            elif mime_type == "image/svg+xml":
                                ext = "svg"
                    
                    # Create a unique filename
                    temp_image_filename = f"temp_image_{progress_id}.{ext}"
                    temp_image_path = temp_dir / temp_image_filename
                    
                    # Save the image
                    async with aiofiles.open(temp_image_path, "wb") as f:
                        await f.write(image_data)
                    
                    # Get the URL for the temporary image
                    base_url = os.getenv('API_URL', 'http://localhost:3001')
                    image_url = f"{base_url}/api/images/tmp/{temp_image_filename}"
                    print(f"[DEBUG] Temporary image saved at: {temp_image_path}")
                    print(f"[DEBUG] Temporary image URL: {image_url}")
                    
                    # Ne pas modifier le texte de la recette ici, le CLI s'occupera d'ajouter la référence
                    # à l'image si nécessaire
                    
                except Exception as e:
                    print(f"[ERROR] Failed to process image: {str(e)}")
                    # Continue without the image if there's an error

            # Create a temporary file for the recipe text
            temp_text_file = self.base_path / "tmp" / f"temp_recipe_{progress_id}.txt"
            async with aiofiles.open(temp_text_file, 'w') as f:
                await f.write(recipe_text)  # Utiliser le texte original sans modification
            
            print(f"[DEBUG] Created temporary recipe text file at: {temp_text_file}")
            
            # Prepare and create CLI command
            cmd = [
                "python", "-m", "recipe_scraper.cli",
                "--mode", "text",
                "--input-file", str(temp_text_file),
                "--recipe-output-folder", str(self.recipes_path),  # Important: use the correct recipe path
                "--image-output-folder", str(self.images_path),
                "--verbose"  # Enable more detailed logging
            ]
            
            # Ajouter le chemin de l'image temporaire si elle existe
            if temp_image_path and temp_image_path.exists():
                cmd.extend(["--image-file", str(temp_image_path)])
            
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
            
            # Pour stocker les logs complets pour chaque étape
            step_logs = {
                "generate_recipe": [],
                "structure_recipe": [],
                "save_recipe": []
            }
            
            async for line in process.stdout:
                line_text = line.decode('utf-8').strip()
                print(f"CLI output: {line_text}")
                
                # Ajouter la ligne aux logs de l'étape courante
                step_logs[current_step].append(line_text)
                
                # Mettre à jour les détails de l'étape en cours avec tous les logs accumulés
                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step=current_step,
                    status="in_progress",
                    details="\n".join(step_logs[current_step])
                )
                
                # Update progress based on log messages
                if ">>> " in line_text:
                    message = line_text.split(">>> ")[1].strip()
                    
                    if "Processing recipe" in message or "Starting recipe" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step="generate_recipe",
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Structuring" in message:
                        current_step = "structure_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Downloading" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Enriching" in message:
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message=message,
                            details="\n".join(step_logs[current_step])
                        )
                    elif "Saving" in message or "sauvegarde" in message.lower():
                        current_step = "save_recipe"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step=current_step,
                            status="in_progress",
                            message="Saving recipe and image",
                            details="\n".join(step_logs[current_step])
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
                # Ajouter stderr aux logs de l'étape actuelle
                step_logs[current_step].append(f"STDERR: {stderr_text}")
                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step=current_step,
                    status="in_progress",
                    details="\n".join(step_logs[current_step])
                )
            
            # Wait for the process to complete
            await process.wait()
            
            # Clean up temporary text file
            if temp_text_file.exists():
                temp_text_file.unlink()
                print(f"[DEBUG] Removed temporary text file: {temp_text_file}")
            
            # Clean up temporary image file if it exists
            if temp_image_path and temp_image_path.exists():
                # Temporairement commenté pour le débogage
                # temp_image_path.unlink()
                print(f"[DEBUG] Keeping temporary image file for debugging: {temp_image_path}")
            
            # Check if the process succeeded
            if process.returncode != 0:
                error_message = f"Recipe scraper CLI failed with return code {process.returncode}"
                if stderr_text:
                    error_message += f": {stderr_text}"
                
                # Check if the error is due to a recipe already existing (via error message or specific return code)
                recipe_exists = False
                if "Recipe already exists" in stderr_text:
                    recipe_exists = True
                elif process.returncode == 100:
                    recipe_exists = True
                
                # N'essayez pas de lire à nouveau stdout, cela provoquerait une erreur
                if recipe_exists:
                    # Extract the slug if present
                    slug_match = re.search(r"slug: ([a-zA-Z0-9\-]+)", stderr_text)
                    existing_slug = slug_match.group(1) if slug_match else None
                    
                    # Check if it's a similarity-based detection
                    if "similar content detected" in stderr_text:
                        error_message = f"Recipe with similar content already exists"
                    else:
                        error_message = f"Recipe with identical content already exists"
                        
                    if existing_slug:
                        error_message += f" with slug: {existing_slug}"
                    
                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step="check_existence",
                        status="error",
                        progress=100,
                        message=error_message,
                        details=stderr_text
                    )
                    raise RecipeExistsError(error_message)
                else:
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
                message="Recipe text successfully processed",
                details="\n".join(step_logs["generate_recipe"])
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="structure_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully structured",
                details="\n".join(step_logs["structure_recipe"])
            )
            
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="save_recipe",
                status="completed",
                progress=100,
                message="Recipe successfully saved",
                details="\n".join(step_logs["save_recipe"])
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
                    image_base64=image
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
            file_ext = "jpg"  # Default extension
            
            if "," in base64_str:
                mime_part, base64_data = base64_str.split(",", 1)
                # Detect extension from MIME type
                if "data:" in mime_part and ";base64" in mime_part:
                    mime_type = mime_part.split(";")[0].replace("data:", "")
                    if mime_type == "image/svg+xml":
                        file_ext = "svg"
                    elif mime_type == "image/png":
                        file_ext = "png"
                    elif mime_type == "image/gif":
                        file_ext = "gif"
                    elif mime_type == "image/webp":
                        file_ext = "webp"
                    # JPEG types stay as jpg
            else:
                base64_data = base64_str
                
            image_data = base64.b64decode(base64_data)
            
            # Ensure the images directory exists
            self.images_path.mkdir(parents=True, exist_ok=True)
            
            # Save image to the recipes/images directory with the correct extension
            image_path = self.images_path / f"{slug}.{file_ext}"
            async with aiofiles.open(image_path, "wb") as f:
                await f.write(image_data)
                
            # Also save a copy to the original images directory for thumbnails
            original_path = self.base_path / "images" / "original" / f"{slug}.{file_ext}"
            async with aiofiles.open(original_path, "wb") as f:
                await f.write(image_data)
                
            # Return the relative path to be stored in the recipe
            return f"images/{slug}.{file_ext}"
                
        except Exception as e:
            print(f"Error saving base64 image: {e}")
            return None

    async def get_generation_progress(self, task_id: str):
        """
        Get the progress of a recipe generation task by task ID.
        """
        return await self.progress_service.get_progress(task_id)