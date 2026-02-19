import asyncio
import base64
import glob
import json
import logging
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import aiofiles
from fastapi import HTTPException

from models.requests import ManualRecipeRequest
from recipe_structurer import RecipeRejectedError
from services.progress_service import ProgressService

logger = logging.getLogger(__name__)

# Create a single instance of ProgressService to be shared
_progress_service = ProgressService()

class RecipeExistsError(Exception):
    """Raised when trying to generate a recipe that already exists."""
    pass

# Subprocess buffer size — avoids asyncio.LimitOverrunError on long log lines
# (e.g. Instructor retry exceptions > 64 KB, the default asyncio buffer).
_SUBPROCESS_BUFFER_LIMIT = 1024 * 1024  # 1 MB

class RecipeService:
    _subprocess_semaphore = asyncio.Semaphore(50)

    def __init__(self, base_path: str = "data"):
        # Déterminer automatiquement le chemin de base selon l'environnement
        logger.debug(f" Original base_path: {base_path}")
        
        # Vérifier si nous sommes dans un environnement Docker (Railway)
        if os.path.exists('/app'):
            logger.debug(" Detected Docker/Railway environment (/app exists)")
            # Si /app/data/recipes existe et contient des fichiers .recipe.json
            if os.path.exists('/app/data/recipes'):
                files = glob.glob('/app/data/recipes/*.recipe.json')
                if files:
                    logger.debug(f" Found {len(files)} recipe files in /app/data/recipes, using this path")
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

        # URL index for O(1) duplicate checks
        self._url_index: Dict[str, str] = {}  # sourceUrl → slug
        self._build_url_index()

    def _build_url_index(self) -> None:
        """Build an in-memory index of sourceUrl → slug for fast duplicate checks."""
        for file_path in self.recipes_path.glob("*.recipe.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                url = data.get("metadata", {}).get("sourceUrl")
                slug = data.get("metadata", {}).get("slug")
                if url and slug:
                    self._url_index[url] = slug
            except (json.JSONDecodeError, OSError):
                continue
        logger.info(f"URL index built: {len(self._url_index)} entries")

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
        """Find a recipe by its source URL using the in-memory index (O(1))."""
        slug = self._url_index.get(url)
        if not slug:
            return None
        file_path = self.recipes_path / f"{slug}.recipe.json"
        if not file_path.exists():
            # Index stale — remove entry
            self._url_index.pop(url, None)
            return None
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Skipping unreadable recipe file {file_path}: {e}")
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

    def _load_private_authors(self) -> List[str]:
        """Load the list of private author identifiers from authors.json."""
        authors_file = os.path.join(os.path.dirname(self.recipes_path), "authors.json")
        try:
            if os.path.exists(authors_file):
                with open(authors_file, "r") as f:
                    return json.load(f).get("private", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load private authors from {authors_file}: {e}")
        return []

    def is_recipe_private(self, recipe: Dict[str, Any]) -> bool:
        """Check if a recipe belongs to a private author/source."""
        private_authors = self._load_private_authors()
        if not private_authors:
            return False
        metadata = recipe.get("metadata", {})
        author = (metadata.get("author") or "").lower()
        source_url = (metadata.get("sourceUrl") or "").lower()
        return any(
            pa.lower() in author or pa.lower() in source_url
            for pa in private_authors
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
            logger.debug(f" Current working directory: {os.getcwd()}")
            logger.debug(f" Base path: {self.base_path} (absolute: {self.base_path.absolute()})")
            logger.debug(f" Recipes path: {self.recipes_path} (absolute: {self.recipes_path.absolute()})")
            logger.debug(f" Searching for recipe files in: {os.path.join(self.recipes_path, '*.recipe.json')}")
            logger.debug(f" include_private parameter: {include_private}")
            
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
                        logger.debug(f" Private authors: {private_authors}")
                else:
                    logger.warning(f" authors.json not found at {authors_file}")
            except Exception as e:
                logger.error(f"Error reading authors file: {str(e)}")
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
                        author = (metadata.get("author") or "").lower()
                        source_url = metadata.get("sourceUrl") or ""
                        source_url_lower = source_url.lower() if source_url else ""
                        
                        is_private = any(
                            private_author.lower() in author or 
                            private_author.lower() in source_url_lower 
                            for private_author in private_authors
                        )
                        
                        if is_private:
                            total_private += 1
                            # logger.debug(f" Recipe '{metadata.get('title', 'Unknown')}' is marked as private (author: {author}, url: {source_url})")
                        
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
                                "peakMonths": metadata.get("peakMonths", []),
                                "recipeType": metadata.get("recipeType", ""),
                                "ingredients": [
                                    {"name": ing.get("name", ""), "name_en": ing.get("name_en", "")}
                                    for ing in recipe_data.get("ingredients", [])
                                ],
                                "totalTime": metadata.get("totalTime"),
                                "totalTimeMinutes": metadata.get("totalTimeMinutes", 0.0),
                                "totalActiveTime": metadata.get("totalActiveTime"),
                                "totalActiveTimeMinutes": metadata.get("totalActiveTimeMinutes", 0.0),
                                "totalPassiveTime": metadata.get("totalPassiveTime"),
                                "totalPassiveTimeMinutes": metadata.get("totalPassiveTimeMinutes", 0.0),
                                "totalCookingTime": metadata.get("totalCookingTime"),
                                "quick": metadata.get("quick", False),
                                "difficulty": metadata.get("difficulty", ""),
                                "slug": metadata.get("slug", os.path.basename(recipe_file).replace(".recipe.json", "")),
                                "nutritionTags": metadata.get("nutritionTags", []),
                                "nutritionPerServing": metadata.get("nutritionPerServing", None),
                            })
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON in file {recipe_file}: {str(e)}")
                    # Skip this file and continue with others
                except Exception as e:
                    logger.error(f"Error processing recipe file {recipe_file}: {str(e)}")
                    # Skip this file and continue with others

            logger.debug(f" Total recipe files read: {total_read}, private: {total_private}, included in results: {total_included}")
            
            # Si aucune recette n'est trouvée, on retourne une liste vide au lieu de lancer une erreur
            if not recipes and len(recipe_files) > 0:
                logger.warning(f" No recipes included in results despite having {len(recipe_files)} recipe files. include_private={include_private}")
                
            return recipes

        except Exception as e:
            logger.error(f"Error listing recipes: {str(e)}")
            # Retourner une liste vide au lieu d'une erreur
            logger.warning(f" Error occurred but returning empty list instead of error: {str(e)}")
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
            logger.error(f"Error deleting all recipes: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_recipe(self, slug: str) -> None:
        """Delete a specific recipe and its associated images."""
        try:
            # Get recipe to find image filename
            recipe_file = self.recipes_path / f"{slug}.recipe.json"
            if not recipe_file.exists():
                raise HTTPException(status_code=404, detail="Recipe not found")

            # Delete associated image (stored flat in images/)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]:
                image_path = self.images_path / f"{slug}{ext}"
                if image_path.exists():
                    image_path.unlink()

            # Delete recipe file
            recipe_file.unlink()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting recipe: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ── Shared CLI subprocess helpers ─────────────────────────────────

    def _find_latest_recipe_slug(self) -> Optional[str]:
        """Find the slug of the most recently modified .recipe.json file."""
        recipe_files = list(self.recipes_path.glob("*.recipe.json"))
        if not recipe_files:
            return None
        latest_file = max(recipe_files, key=lambda p: p.stat().st_mtime)
        slug = latest_file.stem.replace(".recipe", "")
        logger.debug(f"Found latest recipe file: {latest_file} → slug={slug}")
        return slug

    _SUBPROCESS_TIMEOUT_S = 600  # 10 minutes max per recipe import

    async def _run_cli_and_stream_logs(
        self,
        cmd: list[str],
        progress_id: str,
        initial_step: str,
        step_names: list[str],
        *,
        merge_stderr: bool = True,
        timeout_s: int | None = None,
    ) -> tuple[int, dict[str, list[str]], list[str], str | None]:
        """
        Run a CLI subprocess and stream its log output to ProgressService.

        The subprocess is killed if it exceeds *timeout_s* (default:
        ``_SUBPROCESS_TIMEOUT_S``).

        Returns:
            (return_code, step_logs, stderr_lines, saved_slug)
        """
        effective_timeout = timeout_s if timeout_s is not None else self._SUBPROCESS_TIMEOUT_S
        stderr_mode = asyncio.subprocess.STDOUT if merge_stderr else asyncio.subprocess.PIPE

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=stderr_mode,
            limit=_SUBPROCESS_BUFFER_LIMIT,
        )

        async def _stream_and_wait() -> tuple[int, dict[str, list[str]], list[str], str | None]:
            current_step = initial_step
            stderr_lines: list[str] = []
            step_logs: dict[str, list[str]] = {s: [] for s in step_names}
            saved_slug: str | None = None

            async for line in process.stdout:
                line_text = line.decode("utf-8").strip()
                is_debug = " - DEBUG - " in line_text

                if not is_debug:
                    logger.debug(f"CLI output: {line_text}")

                if " - ERROR - " in line_text or " - WARNING - " in line_text:
                    stderr_lines.append(line_text)

                if not is_debug:
                    step_logs[current_step].append(line_text)
                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step=current_step,
                        status="in_progress",
                        details="\n".join(step_logs[current_step][-50:]),
                    )

                if ">>> " in line_text:
                    message = line_text.split(">>> ")[1].strip()

                    # Capture slug from CLI output
                    if "Saved recipe: slug=" in message:
                        saved_slug = message.split("slug=")[1].strip()
                        current_step = "save_recipe"
                    elif "Structuring" in message:
                        current_step = "structure_recipe"
                    elif "Saving" in message or "sauvegarde" in message.lower():
                        current_step = "save_recipe"
                    elif "Fetching web content" in message:
                        current_step = "scrape_content"
                    elif "Processing recipe" in message or "Starting recipe" in message:
                        pass  # stay on current step

                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step=current_step,
                        status="in_progress",
                        message=message,
                        details="\n".join(step_logs[current_step][-50:]),
                    )

            # Read separate stderr if not merged
            if not merge_stderr and process.stderr:
                stderr_data = await process.stderr.read()
                stderr_text = stderr_data.decode("utf-8").strip()
                if stderr_text:
                    logger.warning(f"CLI stderr: {stderr_text}")
                    step_logs[current_step].append(f"STDERR: {stderr_text}")
                    stderr_lines.append(stderr_text)

            # Flush merged stderr summary
            if merge_stderr and stderr_lines:
                combined = "\n".join(stderr_lines)
                logger.warning(f"CLI errors/warnings: {combined}")
                step_logs[current_step].append(f"ERRORS: {combined}")
                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step=current_step,
                    status="in_progress",
                    details="\n".join(step_logs[current_step][-50:]),
                )

            await process.wait()
            return process.returncode, step_logs, stderr_lines, saved_slug

        try:
            return await asyncio.wait_for(_stream_and_wait(), timeout=effective_timeout)
        except asyncio.TimeoutError:
            logger.error(
                f"Subprocess timed out after {effective_timeout}s (PID {process.pid}), killing..."
            )
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            raise TimeoutError(
                f"Recipe import subprocess exceeded {effective_timeout}s timeout"
            )

    # ── Generation pipelines ───────────────────────────────────────────

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

            # Wait for a subprocess slot
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="scrape_content",
                status="in_progress",
                message="En file d'attente...",
            )

            async with self._subprocess_semaphore:
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
                    
                    logger.debug(f" Created temporary credentials file at: {credentials_file}")

                # Prepare the command
                cmd = [
                    "python", "-m", "recipe_scraper.cli",
                    "--mode", "url",
                    "--url", url,
                    "--recipe-output-folder", str(self.recipes_path),
                    "--image-output-folder", str(self.images_path),
                    "--verbose"
                ]
                
                # Add credentials if provided
                if credentials_file:
                    cmd.extend(["--credentials", str(credentials_file)])
                
                logger.debug(f"Running command: {' '.join(cmd)}")

                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step="scrape_content",
                    status="in_progress",
                    message="Fetching recipe content",
                )

                step_names = ["scrape_content", "structure_recipe", "save_recipe"]
                returncode, step_logs, stderr_lines, saved_slug = await self._run_cli_and_stream_logs(
                    cmd, progress_id, "scrape_content", step_names,
                )

                # Clean up temporary credentials file
                if credentials_file and credentials_file.exists():
                    credentials_file.unlink()
                    logger.debug(f"Removed temporary credentials file: {credentials_file}")

                if returncode != 0:
                    stderr_text = "\n".join(stderr_lines)
                    all_logs = [l for s in step_logs.values() for l in s]
                    error_lines = [l for l in all_logs if "ERROR" in l or "Exception" in l or "error" in l.lower()]
                    if stderr_text:
                        error_lines.append(stderr_text)
                    if error_lines:
                        error_detail = error_lines[-1]
                        for prefix in ["CLI output: ", "ERRORS: "]:
                            if error_detail.startswith(prefix):
                                error_detail = error_detail[len(prefix):]
                        error_message = f"Scraper failed (exit {returncode}): {error_detail}"
                    else:
                        error_message = f"Scraper failed with exit code {returncode} (no error details)"
                    logger.error(error_message)
                    await self.progress_service.set_error(progress_id, error_message)
                    return

                slug = saved_slug or self._find_latest_recipe_slug()
                if not slug:
                    await self.progress_service.set_error(progress_id, "No recipe files found after successful generation")
                    return

                # Update the URL index for future duplicate checks
                self._url_index[url] = slug

                for step_name in step_names:
                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step=step_name,
                        status="completed",
                        progress=100,
                        details="\n".join(step_logs[step_name]),
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
            logger.error(f"Error processing recipe: {str(e)}", exc_info=True)
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
            
            # Wait for a subprocess slot
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="generate_recipe",
                status="in_progress",
                message="En file d'attente...",
            )

            async with self._subprocess_semaphore:
                # Create a temp directory for images if it doesn't exist
                temp_dir = self.base_path / "tmp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # If image is provided, save it to a temporary location and get the URL
                modified_recipe_text = recipe_text
                if image_base64:
                    logger.debug(f" Saving temporary image for recipe generation")
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
                        logger.debug(f" Temporary image saved at: {temp_image_path}")
                        logger.debug(f" Temporary image URL: {image_url}")
                        
                    except Exception as e:
                        logger.error(f" Failed to process image: {str(e)}")

                # Create a temporary file for the recipe text
                temp_text_file = self.base_path / "tmp" / f"temp_recipe_{progress_id}.txt"
                async with aiofiles.open(temp_text_file, 'w') as f:
                    await f.write(recipe_text)
                
                logger.debug(f" Created temporary recipe text file at: {temp_text_file}")
                
                # Prepare and create CLI command
                cmd = [
                    "python", "-m", "recipe_scraper.cli",
                    "--mode", "text",
                    "--input-file", str(temp_text_file),
                    "--recipe-output-folder", str(self.recipes_path),
                    "--image-output-folder", str(self.images_path),
                    "--verbose"
                ]
                
                # Ajouter le chemin de l'image temporaire si elle existe
                if temp_image_path and temp_image_path.exists():
                    cmd.extend(["--image-file", str(temp_image_path)])
                
                logger.debug(f"Running command: {' '.join(cmd)}")

                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step="generate_recipe",
                    status="in_progress",
                    message="Processing recipe text",
                )

                step_names = ["generate_recipe", "structure_recipe", "save_recipe"]
                returncode, step_logs, stderr_lines, saved_slug = await self._run_cli_and_stream_logs(
                    cmd, progress_id, "generate_recipe", step_names,
                )

                # Clean up temp files
                if temp_text_file.exists():
                    temp_text_file.unlink()
                if temp_image_path and temp_image_path.exists():
                    temp_image_path.unlink()

                if returncode != 0:
                    stderr_text = "\n".join(stderr_lines)
                    recipe_exists = "Recipe already exists" in stderr_text or returncode == 100
                    if recipe_exists:
                        slug_match = re.search(r"slug: ([a-zA-Z0-9\-]+)", stderr_text)
                        existing_slug = slug_match.group(1) if slug_match else None
                        if "similar content detected" in stderr_text:
                            error_message = "Recipe with similar content already exists"
                        else:
                            error_message = "Recipe with identical content already exists"
                        if existing_slug:
                            error_message += f" with slug: {existing_slug}"
                        await self.progress_service.update_step(
                            progress_id=progress_id,
                            step="check_existence",
                            status="error",
                            progress=100,
                            message=error_message,
                            details=stderr_text,
                        )
                        raise RecipeExistsError(error_message)
                    else:
                        error_message = f"Recipe scraper CLI failed with return code {returncode}"
                        if stderr_text:
                            error_message += f": {stderr_text}"
                        await self.progress_service.set_error(progress_id, error_message)
                    return

                slug = saved_slug or self._find_latest_recipe_slug()
                if not slug:
                    await self.progress_service.set_error(progress_id, "No recipe files found after successful generation")
                    return

                for step_name in step_names:
                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step=step_name,
                        status="completed",
                        progress=100,
                        details="\n".join(step_logs[step_name]),
                    )

                await self.progress_service.complete(progress_id, {"slug": slug})

        except Exception as e:
            await self.progress_service.set_error(
                progress_id,
                f"Error processing recipe text: {str(e)}"
            )

    async def _process_image_recipe_generation(
        self,
        progress_id: str,
        image_base64: str
    ) -> None:
        """Process a recipe generation from an image using OCR + text pipeline."""
        temp_image_path = None
        try:
            # Step 1: OCR — extract text from image
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="ocr_extract",
                status="in_progress",
                message="Extracting text from image (OCR)"
            )

            # Save base64 image to temp file
            temp_dir = self.base_path / "tmp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            if "," in image_base64:
                header, base64_data = image_base64.split(",", 1)
                ext = "jpg"
                if "image/png" in header:
                    ext = "png"
                elif "image/webp" in header:
                    ext = "webp"
            else:
                base64_data = image_base64
                ext = "jpg"

            image_data = base64.b64decode(base64_data)
            temp_image_filename = f"temp_ocr_{progress_id}.{ext}"
            temp_image_path = temp_dir / temp_image_filename

            async with aiofiles.open(temp_image_path, "wb") as f:
                await f.write(image_data)

            logger.debug(f" Temporary OCR image saved at: {temp_image_path}")

            # Wait for a subprocess slot
            await self.progress_service.update_step(
                progress_id=progress_id,
                step="ocr_extract",
                status="in_progress",
                message="En file d'attente...",
            )

            async with self._subprocess_semaphore:
                # Step 2: Run CLI in image mode
                cmd = [
                    "python", "-m", "recipe_scraper.cli",
                    "--mode", "image",
                    "--image-file", str(temp_image_path),
                    "--recipe-output-folder", str(self.recipes_path),
                    "--image-output-folder", str(self.images_path),
                    "--verbose"
                ]

                logger.debug(f"Running command: {' '.join(cmd)}")

                await self.progress_service.update_step(
                    progress_id=progress_id,
                    step="ocr_extract",
                    status="in_progress",
                    message="Extracting text from image (OCR)",
                )

                step_names = ["ocr_extract", "structure_recipe", "save_recipe"]
                returncode, step_logs, stderr_lines, saved_slug = await self._run_cli_and_stream_logs(
                    cmd, progress_id, "ocr_extract", step_names, merge_stderr=False,
                )

                # Cleanup temp image
                if temp_image_path and temp_image_path.exists():
                    temp_image_path.unlink()
                    logger.debug(f"Removed temporary OCR image: {temp_image_path}")

                if returncode != 0:
                    stderr_text = "\n".join(stderr_lines)
                    error_message = f"Recipe generation from image failed (code {returncode})"
                    if stderr_text:
                        error_message += f": {stderr_text}"
                    await self.progress_service.set_error(progress_id, error_message)
                    return

                slug = saved_slug or self._find_latest_recipe_slug()
                if not slug:
                    await self.progress_service.set_error(progress_id, "No recipe files found after generation")
                    return

                for step_name in step_names:
                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step=step_name,
                        status="completed",
                        progress=100,
                        details="\n".join(step_logs[step_name]),
                    )

                await self.progress_service.complete(progress_id, {"slug": slug})

        except Exception as e:
            # Cleanup on error
            if temp_image_path and temp_image_path.exists():
                temp_image_path.unlink()
            await self.progress_service.set_error(
                progress_id, f"Error processing image: {str(e)}"
            )

    async def generate_recipe(
        self,
        import_type: Literal["url", "text", "image"],
        url: Optional[str] = None,
        text: Optional[str] = None,
        image: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a recipe from URL, text, or image. Returns a progress ID.
        """
        # Validate input
        if import_type == "url" and not url:
            raise HTTPException(status_code=400, detail="URL is required for URL import")
        elif import_type == "text" and not text:
            raise HTTPException(status_code=400, detail="Text is required for text import")
        elif import_type == "image" and not image:
            raise HTTPException(status_code=400, detail="Image is required for image import")
        
        # Create a progress ID
        progress_id = f"recipe-gen-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"
        
        # Register the progress with the appropriate steps for this import type
        await self.progress_service.register(progress_id, import_type=import_type)
        
        # Create a task to process the recipe
        if import_type == "url":
            task = asyncio.create_task(
                self._process_recipe_generation(
                    progress_id=progress_id,
                    url=url,
                    credentials=credentials
                )
            )
        elif import_type == "image":
            task = asyncio.create_task(
                self._process_image_recipe_generation(
                    progress_id=progress_id,
                    image_base64=image
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
        
    async def get_generation_progress(self, task_id: str):
        """
        Get the progress of a recipe generation task by task ID.
        """
        return await self.progress_service.get_progress(task_id)

    @staticmethod
    def _generate_slug(title: str) -> str:
        """Generate a URL-friendly slug from a recipe title."""
        # Normalize unicode and strip combining characters (accents)
        normalized = unicodedata.normalize("NFD", title)
        without_accents = "".join(
            c for c in normalized if unicodedata.category(c) != "Mn"
        )
        # Lowercase, replace non-alphanum with hyphens, collapse multiple hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", without_accents.lower()).strip("-")
        return slug

    async def save_manual_recipe(self, request: ManualRecipeRequest) -> str:
        """
        Save a manually created recipe directly to a .recipe.json file.
        Returns the slug of the saved recipe.
        """
        slug = self._generate_slug(request.title)

        if not slug:
            raise HTTPException(
                status_code=400,
                detail="Le titre de la recette ne permet pas de générer un slug valide.",
            )

        # Check if a recipe with this slug already exists
        file_path = self.recipes_path / f"{slug}.recipe.json"
        if file_path.exists():
            raise RecipeExistsError(
                f"Une recette avec le slug '{slug}' existe déjà."
            )

        # Generate ingredient IDs from names
        ingredient_id_counts: Dict[str, int] = {}
        ingredients = []
        for ing in request.ingredients:
            # Create a snake_case ID from the ingredient name
            base_id = self._generate_slug(ing.name).replace("-", "_")
            if not base_id:
                base_id = "ingredient"
            # Handle duplicates by appending a counter
            if base_id in ingredient_id_counts:
                ingredient_id_counts[base_id] += 1
                ing_id = f"{base_id}_{ingredient_id_counts[base_id]}"
            else:
                ingredient_id_counts[base_id] = 0
                ing_id = base_id

            ingredients.append({
                "id": ing_id,
                "name": ing.name,
                "quantity": ing.quantity,
                "unit": ing.unit,
                "category": ing.category,
                "preparation": ing.preparation,
                "notes": None,
                "optional": ing.optional,
            })

        # Generate steps with graph relationships (linear chain)
        ingredient_ids = [i["id"] for i in ingredients]
        steps = []
        for i, step in enumerate(request.steps):
            step_id = f"step_{i + 1}"
            is_first = i == 0
            is_last = i == len(request.steps) - 1

            produces = "plat_termine" if is_last else f"step_{i + 1}_done"
            uses = ingredient_ids if is_first else [f"step_{i}_done"]

            steps.append({
                "id": step_id,
                "action": step.action,
                "duration": step.duration,
                "temperature": step.temperature,
                "stepType": step.stepType,
                "isPassive": step.stepType == "rest",
                "subRecipe": "main",
                "uses": uses,
                "produces": produces,
                "requires": [],
                "visualCue": None,
            })

        # Calculate total time from prep + cook
        total_time = 0.0
        total_cook = 0.0
        for time_str, is_cook in [
            (request.prepTime, False),
            (request.cookTime, True),
        ]:
            if time_str:
                minutes = 0.0
                h_match = re.search(r"(\d+)H", time_str)
                m_match = re.search(r"(\d+)M", time_str)
                if h_match:
                    minutes += int(h_match.group(1)) * 60
                if m_match:
                    minutes += int(m_match.group(1))
                total_time += minutes
                if is_cook:
                    total_cook += minutes

        # Build the full recipe object
        recipe = {
            "metadata": {
                "title": request.title,
                "description": request.description,
                "servings": request.servings,
                "prepTime": request.prepTime,
                "cookTime": request.cookTime,
                "difficulty": request.difficulty,
                "recipeType": request.recipeType,
                "tags": request.tags,
                "imageUrl": None,
                "nationality": request.nationality,
                "author": request.author,
                "source": request.source,
                "notes": [n for n in request.notes if n.strip()],
                "slug": slug,
                "sourceImageUrl": None,
                "sourceUrl": None,
                "image": None,
                "createdAt": datetime.now().isoformat(),
                "creationMode": "manual",
                "diets": [],
                "seasons": [],
                "totalTime": total_time,
                "totalCookingTime": total_cook,
            },
            "ingredients": ingredients,
            "tools": [],
            "steps": steps,
            "finalState": "plat_termine",
        }

        # Save to file
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(recipe, ensure_ascii=False, indent=2))

        logger.debug(f" Manual recipe saved: {file_path} (slug: {slug})")
        return slug