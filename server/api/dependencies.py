"""Shared FastAPI dependencies — singleton services."""

from repositories import JsonFileRepository
from services.recipe_service import RecipeService

_recipe_service: RecipeService | None = None


def get_recipe_service() -> RecipeService:
    """Provide a shared RecipeService singleton across all routes."""
    global _recipe_service
    if _recipe_service is None:
        repo = JsonFileRepository()
        _recipe_service = RecipeService(repo)
    return _recipe_service
