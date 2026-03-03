"""Abstract interface for recipe storage.

Any storage backend (JSON files, SQLite, PostgreSQL, S3, …) implements
this interface.  The rest of the application — services, routes, CLI —
only depends on RecipeRepository, never on a concrete backend.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class RecipeRepository(ABC):

    # ── Read ──────────────────────────────────────────────────────────

    @abstractmethod
    async def list_summaries(self) -> List[Dict[str, Any]]:
        """Return lightweight metadata entries for every recipe."""
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Return the full recipe dict, or None if not found."""
        ...

    @abstractmethod
    async def find_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Return the full recipe whose sourceUrl matches *url*, or None."""
        ...

    @abstractmethod
    def get_imported_urls(self) -> List[str]:
        """Return all source URLs currently in the index."""
        ...

    @abstractmethod
    def get_latest_slug(self) -> Optional[str]:
        """Return the slug of the most recently saved recipe (for CLI fallback)."""
        ...

    # ── Write ─────────────────────────────────────────────────────────

    @abstractmethod
    async def save(self, slug: str, data: Dict[str, Any]) -> None:
        """Persist a recipe and update any internal indexes."""
        ...

    @abstractmethod
    async def delete(self, slug: str) -> bool:
        """Delete a recipe and its images.  Return True if it existed."""
        ...

    @abstractmethod
    async def delete_all(self) -> int:
        """Delete every recipe and image.  Return count of deleted recipes."""
        ...

    @abstractmethod
    def index_recipe(self, slug: str) -> None:
        """Re-index a single recipe after an external write (e.g. CLI subprocess)."""
        ...

    # ── Storage paths (needed by CLI subprocesses) ────────────────────

    @abstractmethod
    def get_recipes_path(self) -> Path:
        ...

    @abstractmethod
    def get_images_path(self) -> Path:
        ...

    @abstractmethod
    def get_base_path(self) -> Path:
        ...
