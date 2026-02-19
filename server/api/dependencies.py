"""Shared FastAPI dependencies — singleton services."""

from services.recipe_service import RecipeService

_recipe_service: RecipeService | None = None


def get_recipe_service() -> RecipeService:
    """Provide a shared RecipeService singleton across all routes."""
    global _recipe_service
    if _recipe_service is None:
        _recipe_service = RecipeService()
    return _recipe_service
