import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_recipe_service
from services.recipe_service import RecipeService

router = APIRouter(prefix="/api/auth", tags=["auth"])

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(request: LoginRequest):
    """Validate password and return access token."""
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    if request.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"token": ADMIN_PASSWORD}


@router.get("/presets")
async def get_auth_presets(service: RecipeService = Depends(get_recipe_service)):
    """Récupère les presets d'authentification."""
    return await service.get_auth_presets()