"""JSON-on-disk implementation of RecipeRepository.

Recipes are stored as individual ``{slug}.recipe.json`` files.
A persistent ``_index.json`` provides O(1) listing and URL deduplication
without reading every file on startup.
"""

import glob as glob_module
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from .recipe_repository import RecipeRepository

logger = logging.getLogger(__name__)


class JsonFileRepository(RecipeRepository):

    _INDEX_FILENAME = "_index.json"

    def __init__(self, base_path: str = "data") -> None:
        self._resolve_paths(base_path)
        self._ensure_directories()

        self._url_index: Dict[str, str] = {}
        self._recipes_cache: Optional[List[Dict[str, Any]]] = None
        self._load_or_rebuild_index()

    # ── Path resolution ───────────────────────────────────────────────

    def _resolve_paths(self, base_path: str) -> None:
        if os.path.exists("/app"):
            if os.path.exists("/app/data/recipes"):
                files = glob_module.glob("/app/data/recipes/*.recipe.json")
                if files:
                    logger.debug(f"Docker env: {len(files)} recipes in /app/data/recipes")
                    self._base_path = Path("/app/data")
                    self._recipes_path = Path("/app/data/recipes")
                    self._images_path = self._recipes_path / "images"
                    return

        self._base_path = Path(base_path)
        self._recipes_path = self._base_path / "recipes"
        self._images_path = self._recipes_path / "images"

    def _ensure_directories(self) -> None:
        try:
            self._base_path.mkdir(parents=True, exist_ok=True)
            self._recipes_path.mkdir(parents=True, exist_ok=True)
            self._images_path.mkdir(parents=True, exist_ok=True)
            (self._base_path / "images" / "original").mkdir(parents=True, exist_ok=True)
            for size in ("thumbnail", "small", "medium", "large"):
                (self._base_path / "images" / size).mkdir(parents=True, exist_ok=True)
            (self._recipes_path / "errors").mkdir(parents=True, exist_ok=True)
            (self._base_path / "tmp").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create required directories: {e}")

    # ── Public — paths ────────────────────────────────────────────────

    def get_recipes_path(self) -> Path:
        return self._recipes_path

    def get_images_path(self) -> Path:
        return self._images_path

    def get_base_path(self) -> Path:
        return self._base_path

    # ── Public — read ─────────────────────────────────────────────────

    async def list_summaries(self) -> List[Dict[str, Any]]:
        if self._recipes_cache is None:
            self._load_or_rebuild_index()
        self._refresh_stale_entries()
        return self._recipes_cache or []

    async def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        file_path = self._recipes_path / f"{slug}.recipe.json"
        if not file_path.exists():
            return None
        try:
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
            return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Unreadable recipe file {file_path}: {e}")
            return None

    def get_imported_urls(self) -> List[str]:
        return list(self._url_index.keys())

    async def find_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        slug = self._url_index.get(url)
        if not slug:
            return None
        file_path = self._recipes_path / f"{slug}.recipe.json"
        if not file_path.exists():
            self._url_index.pop(url, None)
            return None
        try:
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
            return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Skipping unreadable recipe file {file_path}: {e}")
            return None

    def get_latest_slug(self) -> Optional[str]:
        recipe_files = list(self._recipes_path.glob("*.recipe.json"))
        if not recipe_files:
            return None
        latest = max(recipe_files, key=lambda p: p.stat().st_mtime)
        slug = latest.stem.replace(".recipe", "")
        logger.debug(f"Latest recipe file: {latest} -> slug={slug}")
        return slug

    # ── Public — write ────────────────────────────────────────────────

    async def save(self, slug: str, data: Dict[str, Any]) -> None:
        file_path = self._recipes_path / f"{slug}.recipe.json"
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        self._add_to_index(data, file_path)
        logger.debug(f"Recipe saved: {file_path}")

    async def delete(self, slug: str) -> bool:
        recipe_file = self._recipes_path / f"{slug}.recipe.json"
        if not recipe_file.exists():
            return False

        for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
            image_path = self._images_path / f"{slug}{ext}"
            if image_path.exists():
                image_path.unlink()

        recipe_file.unlink()
        self._remove_from_index(slug)
        return True

    async def delete_all(self) -> int:
        count = 0
        for recipe_file in self._recipes_path.glob("*.json"):
            if recipe_file.name not in ("auth_presets.json", self._INDEX_FILENAME):
                recipe_file.unlink()
                count += 1

        for image_file in self._images_path.glob("*"):
            if image_file.is_file():
                image_file.unlink()

        self._recipes_cache = []
        self._url_index = {}
        self._persist_index()
        return count

    def index_recipe(self, slug: str) -> None:
        file_path = self._recipes_path / f"{slug}.recipe.json"
        if not file_path.exists():
            logger.warning(f"Cannot index {slug}: file not found")
            return
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            self._add_to_index(data, file_path)
            logger.debug(f"Indexed recipe: {slug}")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to index {slug}: {e}")

    # ── Index internals ───────────────────────────────────────────────

    @property
    def _index_path(self) -> Path:
        return self._recipes_path / self._INDEX_FILENAME

    def _load_or_rebuild_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r") as f:
                    index_data = json.load(f)
                self._recipes_cache = index_data.get("recipes", [])
                self._url_index = index_data.get("url_index", {})
                logger.info(
                    f"Index loaded: {len(self._recipes_cache)} recipes, "
                    f"{len(self._url_index)} URL entries"
                )
                return
            except (json.JSONDecodeError, OSError, KeyError) as e:
                logger.warning(f"Index file corrupt, rebuilding: {e}")
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        t0 = time.monotonic()
        recipe_files = list(self._recipes_path.glob("*.recipe.json"))
        recipes: List[Dict[str, Any]] = []
        url_index: Dict[str, str] = {}

        for file_path in recipe_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                entry = self._extract_list_entry(data, file_path)
                if entry:
                    recipes.append(entry)
                url = data.get("metadata", {}).get("sourceUrl")
                slug = data.get("metadata", {}).get("slug")
                if url and slug:
                    url_index[url] = slug
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Skipping {file_path}: {e}")

        self._recipes_cache = recipes
        self._url_index = url_index
        self._persist_index()

        elapsed = time.monotonic() - t0
        logger.info(
            f"Index rebuilt from {len(recipe_files)} files in {elapsed:.1f}s "
            f"({len(recipes)} recipes, {len(url_index)} URLs)"
        )

    def _persist_index(self) -> None:
        index_data = {
            "recipes": self._recipes_cache or [],
            "url_index": self._url_index,
        }
        tmp_path = self._index_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))
            tmp_path.replace(self._index_path)
        except OSError as e:
            logger.error(f"Failed to persist index: {e}")
            tmp_path.unlink(missing_ok=True)

    def _refresh_stale_entries(self) -> None:
        """Re-read any recipe files that changed since the index was built."""
        if not self._recipes_cache:
            return

        indexed_slugs = {r["slug"] for r in self._recipes_cache}
        on_disk = set()
        stale_files: List[Path] = []
        mtime_by_slug = {r["slug"]: r.get("_mtime", 0) for r in self._recipes_cache}

        for fp in self._recipes_path.glob("*.recipe.json"):
            slug = fp.stem.replace(".recipe", "")
            on_disk.add(slug)
            try:
                disk_mtime = fp.stat().st_mtime
            except OSError:
                continue
            if slug not in indexed_slugs or disk_mtime > mtime_by_slug.get(slug, 0):
                stale_files.append(fp)

        removed = indexed_slugs - on_disk
        if not stale_files and not removed:
            return

        dirty = False

        if removed:
            self._recipes_cache = [r for r in self._recipes_cache if r["slug"] not in removed]
            self._url_index = {u: s for u, s in self._url_index.items() if s not in removed}
            dirty = True

        for fp in stale_files:
            try:
                with open(fp, "r") as f:
                    data = json.load(f)
                entry = self._extract_list_entry(data, fp)
                if entry:
                    slug = entry["slug"]
                    self._recipes_cache = [r for r in self._recipes_cache if r["slug"] != slug]
                    self._recipes_cache.append(entry)
                    url = data.get("metadata", {}).get("sourceUrl")
                    if url and slug:
                        self._url_index[url] = slug
                    dirty = True
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to refresh index for {fp}: {e}")

        if dirty:
            self._persist_index()
            logger.info(
                f"Index refreshed: {len(stale_files)} updated, "
                f"{len(removed)} removed"
            )

    def _add_to_index(self, recipe_data: Dict[str, Any], file_path: Path) -> None:
        entry = self._extract_list_entry(recipe_data, file_path)
        if not entry:
            return
        slug = entry["slug"]
        if self._recipes_cache is None:
            self._recipes_cache = []
        self._recipes_cache = [r for r in self._recipes_cache if r["slug"] != slug]
        self._recipes_cache.append(entry)

        url = recipe_data.get("metadata", {}).get("sourceUrl")
        if url and slug:
            self._url_index[url] = slug
        self._persist_index()

    def _remove_from_index(self, slug: str) -> None:
        if self._recipes_cache is not None:
            self._recipes_cache = [r for r in self._recipes_cache if r["slug"] != slug]
        self._url_index = {u: s for u, s in self._url_index.items() if s != slug}
        self._persist_index()

    # ── List entry extraction ─────────────────────────────────────────

    @staticmethod
    def _slim_nutrition(nutrition: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not nutrition:
            return None
        keep = ("confidence", "calories", "protein", "fat", "carbs", "fiber", "sugar", "saturatedFat")
        return {k: nutrition[k] for k in keep if k in nutrition}

    @staticmethod
    def _extract_list_entry(recipe_data: Dict[str, Any], file_path: Path) -> Optional[Dict[str, Any]]:
        metadata = recipe_data.get("metadata", {})
        slug = metadata.get("slug", file_path.stem.replace(".recipe", ""))

        total_time_raw = metadata.get("totalTime")
        if isinstance(total_time_raw, (int, float)):
            hours, mins = divmod(int(total_time_raw), 60)
            total_time_raw = f"PT{hours}H{mins}M" if hours else f"PT{mins}M"

        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            mtime = 0.0

        return {
            "title": metadata.get("title", "Untitled"),
            "sourceImageUrl": metadata.get("sourceImageUrl", ""),
            "description": metadata.get("description", ""),
            "bookTitle": metadata.get("bookTitle", ""),
            "author": metadata.get("author", ""),
            "diets": metadata.get("diets") or [],
            "seasons": metadata.get("seasons") or [],
            "peakMonths": metadata.get("peakMonths") or [],
            "recipeType": metadata.get("recipeType", ""),
            "ingredients": [
                {"name": ing.get("name") or "", "name_en": ing.get("name_en") or ""}
                for ing in recipe_data.get("ingredients", [])
            ],
            "totalTime": total_time_raw,
            "totalTimeMinutes": metadata.get("totalTimeMinutes", 0.0),
            "totalActiveTime": metadata.get("totalActiveTime"),
            "totalActiveTimeMinutes": metadata.get("totalActiveTimeMinutes", 0.0),
            "totalPassiveTime": metadata.get("totalPassiveTime"),
            "totalPassiveTimeMinutes": metadata.get("totalPassiveTimeMinutes", 0.0),
            "totalCookingTime": metadata.get("totalCookingTime"),
            "quick": metadata.get("quick", False),
            "difficulty": metadata.get("difficulty", ""),
            "slug": slug,
            "nutritionTags": metadata.get("nutritionTags") or [],
            "nutritionPerServing": JsonFileRepository._slim_nutrition(
                metadata.get("nutritionPerServing")
            ),
            "_mtime": mtime,
        }
