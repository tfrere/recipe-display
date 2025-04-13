from fastapi import APIRouter, Depends
from services.recipe_service import RecipeService
import os

async def get_recipe_service():
    # Utiliser la variable d'environnement DATA_PATH si elle existe
    data_path = os.getenv("DATA_PATH", "data")
    print(f"[DEBUG] Auth route - Initializing RecipeService with base_path: {data_path}")
    return RecipeService(base_path=data_path)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/presets")
async def get_auth_presets(service: RecipeService = Depends(get_recipe_service)):
    """Get authentication presets."""
    return await service.get_auth_presets() 