import asyncio
import base64
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
from recipe_structurer import RecipeRejectedError, PIPELINE_VERSION
from repositories import RecipeRepository
from services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_progress_service = ProgressService()


class RecipeExistsError(Exception):
    """Raised when trying to generate a recipe that already exists."""
    pass


_SUBPROCESS_BUFFER_LIMIT = 1024 * 1024  # 1 MB


class RecipeService:
    _subprocess_semaphore = asyncio.Semaphore(30)

    def __init__(self, repo: RecipeRepository) -> None:
        self.repo = repo
        self.progress_service = _progress_service
        self.generation_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_lock = asyncio.Lock()

    # ── Convenience path accessors (used by routes / image serving) ───

    @property
    def recipes_path(self) -> Path:
        return self.repo.get_recipes_path()

    @property
    def images_path(self) -> Path:
        return self.repo.get_images_path()

    @property
    def base_path(self) -> Path:
        return self.repo.get_base_path()

    @property
    def auth_presets_path(self) -> Path:
        return self.base_path / "auth_presets.json"

    # ── Recipe CRUD (delegated to repository) ─────────────────────────

    async def get_recipe(self, slug: str) -> Dict[str, Any]:
        recipe = await self.repo.get_by_slug(slug)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")

        recipe["slug"] = recipe["metadata"]["slug"]
        recipe["title"] = recipe["metadata"]["title"]
        if "totalCookingTime" in recipe["metadata"]:
            recipe["totalCookingTime"] = recipe["metadata"]["totalCookingTime"]
        return recipe

    def get_imported_urls(self) -> List[str]:
        return self.repo.get_imported_urls()

    async def list_recipes(self, include_private: bool = False) -> List[Dict[str, Any]]:
        try:
            summaries = await self.repo.list_summaries()

            if not include_private:
                config = self._load_authors_config()
                if "public" in config and config["public"]:
                    summaries = [
                        r for r in summaries
                        if self._author_matches(r.get("author", ""), config["public"])
                    ]
                elif "private" in config and config["private"]:
                    summaries = [
                        r for r in summaries
                        if not self._author_matches(r.get("author", ""), config["private"])
                    ]

            return summaries
        except Exception as e:
            logger.error(f"Error listing recipes: {e}")
            return []

    async def delete_recipe(self, slug: str) -> None:
        deleted = await self.repo.delete(slug)
        if not deleted:
            raise HTTPException(status_code=404, detail="Recipe not found")

    async def delete_all_recipes(self) -> None:
        try:
            await self.repo.delete_all()
        except Exception as e:
            logger.error(f"Error deleting all recipes: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def invalidate_list_cache(self) -> None:
        """No-op kept for backward compatibility."""
        pass

    # ── Access control ────────────────────────────────────────────────

    def _load_authors_config(self) -> Dict[str, list[str]]:
        """Load authors.json and return normalised config.

        Supports two modes (determined by which keys are present):
          • "public"  → whitelist: only recipes from these authors are visible
          • "private" → blacklist: recipes from these authors are hidden

        All keywords are lowercased for case-insensitive substring matching.
        Returns empty dict if file is missing (= everything public).
        """
        authors_file = os.path.join(os.path.dirname(self.recipes_path), "authors.json")
        try:
            if os.path.exists(authors_file):
                with open(authors_file, "r") as f:
                    data = json.load(f)
                    config: Dict[str, list[str]] = {}
                    if "public" in data:
                        config["public"] = [a.lower() for a in data["public"]]
                    if "private" in data:
                        config["private"] = [a.lower() for a in data["private"]]
                    return config
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load access config from {authors_file}: {e}")
        return {}

    @staticmethod
    def _author_matches(author: str, keywords: list[str]) -> bool:
        if not author or not keywords:
            return False
        author_lower = author.lower()
        return any(kw in author_lower for kw in keywords)

    def is_recipe_private(self, recipe: Dict[str, Any]) -> bool:
        config = self._load_authors_config()
        author = recipe.get("metadata", {}).get("author", "")
        if "public" in config:
            return not self._author_matches(author, config["public"])
        if "private" in config:
            return self._author_matches(author, config["private"])
        return False

    async def get_auth_presets(self) -> Dict[str, Any]:
        try:
            if not self.auth_presets_path.exists():
                return {}
            async with aiofiles.open(self.auth_presets_path, "r") as f:
                content = await f.read()
                raw_presets = json.loads(content)
                return {
                    domain: {
                        "type": preset["type"],
                        "domain": preset["domain"],
                        "values": preset["values"],
                        "description": preset.get("description", ""),
                    }
                    for domain, preset in raw_presets.items()
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading auth presets: {e}")

    # ── Subprocess helpers ────────────────────────────────────────────

    _SUBPROCESS_TIMEOUT_S = 600

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

                    if "Saved recipe: slug=" in message:
                        saved_slug = message.split("slug=")[1].strip()
                        current_step = "save_recipe"
                    elif "Structuring" in message:
                        current_step = "structure_recipe"
                    elif "Saving" in message or "sauvegarde" in message.lower():
                        current_step = "save_recipe"
                    elif "Fetching web content" in message:
                        current_step = "scrape_content"

                    await self.progress_service.update_step(
                        progress_id=progress_id,
                        step=current_step,
                        status="in_progress",
                        message=message,
                        details="\n".join(step_logs[current_step][-50:]),
                    )

            if not merge_stderr and process.stderr:
                stderr_data = await process.stderr.read()
                stderr_text = stderr_data.decode("utf-8").strip()
                if stderr_text:
                    logger.warning(f"CLI stderr: {stderr_text}")
                    step_logs[current_step].append(f"STDERR: {stderr_text}")
                    stderr_lines.append(stderr_text)

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
            logger.error(f"Subprocess timed out after {effective_timeout}s (PID {process.pid}), killing...")
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            raise TimeoutError(f"Recipe import subprocess exceeded {effective_timeout}s timeout")

    async def _cleanup_task(self, progress_id: str, task: asyncio.Task) -> None:
        async with self._cleanup_lock:
            self.generation_tasks.pop(progress_id, None)
            try:
                if task.done() and not task.cancelled():
                    exc = task.exception()
                    if exc:
                        await self.progress_service.set_error(progress_id, f"Task failed: {exc}")
            except asyncio.CancelledError:
                await self.progress_service.set_error(progress_id, "Generation was cancelled")

    # ── Generation pipelines ──────────────────────────────────────────

    async def _process_recipe_generation(
        self, progress_id: str, url: str, credentials: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            await self.progress_service.update_step(
                progress_id=progress_id, step="check_existence",
                status="in_progress", message="Checking if recipe already exists",
            )

            existing = await self.repo.find_by_url(url)
            if existing:
                slug = existing.get("metadata", {}).get("slug", "")
                if slug:
                    await self.progress_service.update_step(
                        progress_id=progress_id, step="check_existence",
                        status="error", message=f"Recipe already exists with slug: {slug}",
                    )
                    raise RecipeExistsError(f"Recipe from this URL already exists with slug: {slug}")

            await self.progress_service.update_step(
                progress_id=progress_id, step="check_existence",
                status="completed", progress=100, message="Recipe does not exist yet",
            )

            await self.progress_service.update_step(
                progress_id=progress_id, step="scrape_content",
                status="in_progress", message="Waiting for slot...",
            )

            async with self._subprocess_semaphore:
                credentials_file = None
                if credentials:
                    domain = url.split("//")[-1].split("/")[0]
                    tmp_dir = self.base_path / "tmp"
                    credentials_file = tmp_dir / f"temp_creds_{progress_id}.json"
                    async with aiofiles.open(credentials_file, "w") as f:
                        await f.write(json.dumps({domain: credentials}))

                cmd = [
                    "python", "-m", "recipe_scraper.cli",
                    "--mode", "url",
                    "--url", url,
                    "--recipe-output-folder", str(self.recipes_path),
                    "--image-output-folder", str(self.images_path),
                    "--verbose",
                ]
                if credentials_file:
                    cmd.extend(["--credentials", str(credentials_file)])

                await self.progress_service.update_step(
                    progress_id=progress_id, step="scrape_content",
                    status="in_progress", message="Fetching recipe content",
                )

                step_names = ["scrape_content", "structure_recipe", "save_recipe"]
                returncode, step_logs, stderr_lines, saved_slug = await self._run_cli_and_stream_logs(
                    cmd, progress_id, "scrape_content", step_names,
                )

                if credentials_file and credentials_file.exists():
                    credentials_file.unlink()

                if returncode != 0:
                    stderr_text = "\n".join(stderr_lines)
                    all_logs = [line for s in step_logs.values() for line in s]
                    error_lines = [l for l in all_logs if "ERROR" in l or "Exception" in l or "error" in l.lower()]
                    if stderr_text:
                        error_lines.append(stderr_text)
                    if error_lines:
                        error_detail = error_lines[-1]
                        for prefix in ("CLI output: ", "ERRORS: "):
                            if error_detail.startswith(prefix):
                                error_detail = error_detail[len(prefix):]
                        error_message = f"Scraper failed (exit {returncode}): {error_detail}"
                    else:
                        error_message = f"Scraper failed with exit code {returncode} (no error details)"
                    logger.error(error_message)
                    await self.progress_service.set_error(progress_id, error_message)
                    return

                slug = saved_slug or self.repo.get_latest_slug()
                if not slug:
                    await self.progress_service.set_error(progress_id, "No recipe files found after successful generation")
                    return

                self.repo.index_recipe(slug)

                for step_name in step_names:
                    await self.progress_service.update_step(
                        progress_id=progress_id, step=step_name,
                        status="completed", progress=100, details="\n".join(step_logs[step_name]),
                    )
                await self.progress_service.complete(progress_id, {"slug": slug})

        except RecipeExistsError as e:
            await self.progress_service.set_error(progress_id, f"Recipe already exists: {e}")
        except RecipeRejectedError as e:
            await self.progress_service.set_error(progress_id, f"Recipe was rejected: {e}")
        except Exception as e:
            logger.error(f"Error processing recipe: {e}", exc_info=True)
            await self.progress_service.set_error(progress_id, f"Error processing recipe: {e}")

    async def _process_text_recipe_generation(
        self, progress_id: str, recipe_text: str, image_base64: str,
    ) -> None:
        temp_image_path = None
        try:
            await self.progress_service.update_step(
                progress_id=progress_id, step="check_existence",
                status="in_progress", message="Checking if recipe already exists",
            )
            await self.progress_service.update_step(
                progress_id=progress_id, step="check_existence",
                status="completed", progress=100, message="Checking recipe existence in scraper",
            )

            await self.progress_service.update_step(
                progress_id=progress_id, step="generate_recipe",
                status="in_progress", message="Waiting for slot...",
            )

            async with self._subprocess_semaphore:
                temp_dir = self.base_path / "tmp"
                temp_dir.mkdir(parents=True, exist_ok=True)

                if image_base64:
                    try:
                        if "," in image_base64:
                            _, base64_data = image_base64.split(",", 1)
                        else:
                            base64_data = image_base64
                        image_data = base64.b64decode(base64_data)
                        ext = "jpg"
                        if image_base64.startswith("data:image/"):
                            mime_type = image_base64.split(";")[0].split(":")[1]
                            if "/" in mime_type:
                                file_ext = mime_type.split("/")[1]
                                if file_ext in ("jpeg", "jpg", "png", "gif", "webp"):
                                    ext = file_ext if file_ext != "jpeg" else "jpg"
                                elif mime_type == "image/svg+xml":
                                    ext = "svg"
                        temp_image_path = temp_dir / f"temp_image_{progress_id}.{ext}"
                        async with aiofiles.open(temp_image_path, "wb") as f:
                            await f.write(image_data)
                    except Exception as e:
                        logger.error(f"Failed to process image: {e}")

                temp_text_file = temp_dir / f"temp_recipe_{progress_id}.txt"
                async with aiofiles.open(temp_text_file, "w") as f:
                    await f.write(recipe_text)

                cmd = [
                    "python", "-m", "recipe_scraper.cli",
                    "--mode", "text",
                    "--input-file", str(temp_text_file),
                    "--recipe-output-folder", str(self.recipes_path),
                    "--image-output-folder", str(self.images_path),
                    "--verbose",
                ]
                if temp_image_path and temp_image_path.exists():
                    cmd.extend(["--image-file", str(temp_image_path)])

                await self.progress_service.update_step(
                    progress_id=progress_id, step="generate_recipe",
                    status="in_progress", message="Processing recipe text",
                )

                step_names = ["generate_recipe", "structure_recipe", "save_recipe"]
                returncode, step_logs, stderr_lines, saved_slug = await self._run_cli_and_stream_logs(
                    cmd, progress_id, "generate_recipe", step_names,
                )

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
                        error_message = (
                            "Recipe with similar content already exists"
                            if "similar content detected" in stderr_text
                            else "Recipe with identical content already exists"
                        )
                        if existing_slug:
                            error_message += f" with slug: {existing_slug}"
                        await self.progress_service.update_step(
                            progress_id=progress_id, step="check_existence",
                            status="error", progress=100, message=error_message, details=stderr_text,
                        )
                        raise RecipeExistsError(error_message)
                    else:
                        error_message = f"Recipe scraper CLI failed with return code {returncode}"
                        if stderr_text:
                            error_message += f": {stderr_text}"
                        await self.progress_service.set_error(progress_id, error_message)
                    return

                slug = saved_slug or self.repo.get_latest_slug()
                if not slug:
                    await self.progress_service.set_error(progress_id, "No recipe files found after successful generation")
                    return

                self.repo.index_recipe(slug)

                for step_name in step_names:
                    await self.progress_service.update_step(
                        progress_id=progress_id, step=step_name,
                        status="completed", progress=100, details="\n".join(step_logs[step_name]),
                    )
                await self.progress_service.complete(progress_id, {"slug": slug})

        except Exception as e:
            await self.progress_service.set_error(progress_id, f"Error processing recipe text: {e}")

    async def _process_image_recipe_generation(
        self, progress_id: str, image_base64: str,
    ) -> None:
        temp_image_path = None
        try:
            await self.progress_service.update_step(
                progress_id=progress_id, step="ocr_extract",
                status="in_progress", message="Extracting text from image (OCR)",
            )

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
            temp_image_path = temp_dir / f"temp_ocr_{progress_id}.{ext}"
            async with aiofiles.open(temp_image_path, "wb") as f:
                await f.write(image_data)

            await self.progress_service.update_step(
                progress_id=progress_id, step="ocr_extract",
                status="in_progress", message="Waiting for slot...",
            )

            async with self._subprocess_semaphore:
                cmd = [
                    "python", "-m", "recipe_scraper.cli",
                    "--mode", "image",
                    "--image-file", str(temp_image_path),
                    "--recipe-output-folder", str(self.recipes_path),
                    "--image-output-folder", str(self.images_path),
                    "--verbose",
                ]

                await self.progress_service.update_step(
                    progress_id=progress_id, step="ocr_extract",
                    status="in_progress", message="Extracting text from image (OCR)",
                )

                step_names = ["ocr_extract", "structure_recipe", "save_recipe"]
                returncode, step_logs, stderr_lines, saved_slug = await self._run_cli_and_stream_logs(
                    cmd, progress_id, "ocr_extract", step_names, merge_stderr=False,
                )

                if temp_image_path and temp_image_path.exists():
                    temp_image_path.unlink()

                if returncode != 0:
                    stderr_text = "\n".join(stderr_lines)
                    error_message = f"Recipe generation from image failed (code {returncode})"
                    if stderr_text:
                        error_message += f": {stderr_text}"
                    await self.progress_service.set_error(progress_id, error_message)
                    return

                slug = saved_slug or self.repo.get_latest_slug()
                if not slug:
                    await self.progress_service.set_error(progress_id, "No recipe files found after generation")
                    return

                self.repo.index_recipe(slug)

                for step_name in step_names:
                    await self.progress_service.update_step(
                        progress_id=progress_id, step=step_name,
                        status="completed", progress=100, details="\n".join(step_logs[step_name]),
                    )
                await self.progress_service.complete(progress_id, {"slug": slug})

        except Exception as e:
            if temp_image_path and temp_image_path.exists():
                temp_image_path.unlink()
            await self.progress_service.set_error(progress_id, f"Error processing image: {e}")

    async def generate_recipe(
        self,
        import_type: Literal["url", "text", "image"],
        url: Optional[str] = None,
        text: Optional[str] = None,
        image: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> str:
        if import_type == "url" and not url:
            raise HTTPException(status_code=400, detail="URL is required for URL import")
        elif import_type == "text" and not text:
            raise HTTPException(status_code=400, detail="Text is required for text import")
        elif import_type == "image" and not image:
            raise HTTPException(status_code=400, detail="Image is required for image import")

        progress_id = f"recipe-gen-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"
        await self.progress_service.register(progress_id, import_type=import_type)

        if import_type == "url":
            task = asyncio.create_task(self._process_recipe_generation(progress_id, url, credentials))
        elif import_type == "image":
            task = asyncio.create_task(self._process_image_recipe_generation(progress_id, image))
        else:
            task = asyncio.create_task(self._process_text_recipe_generation(progress_id, text, image))

        self.generation_tasks[progress_id] = task
        task.add_done_callback(lambda t: asyncio.create_task(self._cleanup_task(progress_id, t)))
        return progress_id

    async def get_generation_progress(self, task_id: str):
        return await self.progress_service.get_progress(task_id)

    # ── Manual recipe creation ────────────────────────────────────────

    @staticmethod
    def _generate_slug(title: str) -> str:
        normalized = unicodedata.normalize("NFD", title)
        without_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        return re.sub(r"[^a-z0-9]+", "-", without_accents.lower()).strip("-")

    async def save_manual_recipe(self, request: ManualRecipeRequest) -> str:
        slug = self._generate_slug(request.title)
        if not slug:
            raise HTTPException(status_code=400, detail="Recipe title cannot produce a valid slug.")

        existing = await self.repo.get_by_slug(slug)
        if existing is not None:
            raise RecipeExistsError(f"A recipe with slug '{slug}' already exists.")

        ingredient_id_counts: Dict[str, int] = {}
        ingredients = []
        for ing in request.ingredients:
            base_id = self._generate_slug(ing.name).replace("-", "_")
            if not base_id:
                base_id = "ingredient"
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

        ingredient_ids = [i["id"] for i in ingredients]
        steps = []
        for i, step in enumerate(request.steps):
            step_id = f"step_{i + 1}"
            is_last = i == len(request.steps) - 1
            steps.append({
                "id": step_id,
                "action": step.action,
                "duration": step.duration,
                "temperature": step.temperature,
                "stepType": step.stepType,
                "isPassive": step.stepType == "rest",
                "subRecipe": "main",
                "uses": ingredient_ids if i == 0 else [f"step_{i}_done"],
                "produces": "plat_termine" if is_last else f"step_{i + 1}_done",
                "requires": [],
                "visualCue": None,
            })

        total_time = 0.0
        total_cook = 0.0
        for time_str, is_cook in [(request.prepTime, False), (request.cookTime, True)]:
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
                "updatedAt": datetime.now().isoformat(),
                "creationMode": "manual",
                "pipelineVersion": PIPELINE_VERSION,
                "structurerModel": None,
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

        await self.repo.save(slug, recipe)
        return slug
