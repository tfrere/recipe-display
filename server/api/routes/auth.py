from fastapi import APIRouter, Depends
from services.recipe_service import RecipeService

router = APIRouter(prefix="/api/auth", tags=["auth"])

async def get_recipe_service():
    return RecipeService()

@router.get("/presets")
async def get_auth_presets(service: RecipeService = Depends(get_recipe_service)):
    """Récupère les presets d'authentification."""
    return await service.get_auth_presets() 