import asyncio
import json
import logging
import os
import traceback
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from starlette.responses import StreamingResponse

from models.progress import GenerationProgress
from models.requests import GenerateRecipeRequest, ManualRecipeRequest
from models.responses import RecipeListItem, GenerateRecipeResponse, ManualRecipeResponse
from api.dependencies import get_recipe_service
from services.recipe_service import RecipeService, RecipeExistsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

PRIVATE_ACCESS_SECRET = os.getenv("PRIVATE_ACCESS_SECRET", "")

def _has_valid_private_token(token: Optional[str]) -> bool:
    """Check if the provided token matches the private access secret."""
    if not PRIVATE_ACCESS_SECRET:
        return False
    return token == PRIVATE_ACCESS_SECRET


@router.get("/progress/{task_id}", response_model=GenerationProgress)
async def get_generation_progress(task_id: str, service: RecipeService = Depends(get_recipe_service)):
    """Get the progress of a recipe generation."""
    progress = await service.get_generation_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Progress not found for ID: {task_id}")
    return progress


@router.get("/progress/{task_id}/stream")
async def stream_generation_progress(task_id: str, service: RecipeService = Depends(get_recipe_service)):
    """Stream progress updates via Server-Sent Events."""
    progress_service = service.progress_service
    queue = progress_service.subscribe(task_id)

    async def event_generator():
        try:
            # Send initial state immediately
            initial = await progress_service.get_progress(task_id)
            if initial:
                yield f"data: {initial.model_dump_json(by_alias=True)}\n\n"
                if initial.status in ("completed", "error"):
                    return
            else:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                return

            # Stream updates from the subscriber queue
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {data}\n\n"
                    parsed = json.loads(data)
                    if parsed.get("status") in ("completed", "error"):
                        return
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        finally:
            progress_service.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("", response_model=List[RecipeListItem])
async def list_recipes(
    include_private: bool = False,
    service: RecipeService = Depends(get_recipe_service),
    x_private_token: Optional[str] = Header(None),
):
    """Get list of all recipes with their metadata."""
    allow_private = include_private and _has_valid_private_token(x_private_token)
    try:
        recipes = await service.list_recipes(allow_private)
        return recipes
    except HTTPException as e:
        if e.status_code == 404 and "Recipe not found" in str(e.detail):
            return []
        raise

@router.options("")
async def options_recipes():
    """Handle OPTIONS request for CORS."""
    return {"detail": "OK"}

@router.post("", response_model=GenerateRecipeResponse)
async def generate_recipe(request: GenerateRecipeRequest, service: RecipeService = Depends(get_recipe_service)):
    """Generate a recipe from a URL or text content."""
    try:
        progress_id = await service.generate_recipe(
            import_type=request.type,
            url=request.url,
            text=request.text,
            image=request.image,
            credentials=request.credentials
        )
        return {"progressId": progress_id}

    except RecipeExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in generate_recipe: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual", response_model=ManualRecipeResponse)
async def create_manual_recipe(
    request: ManualRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
):
    """Create a recipe manually from structured data (no generation pipeline)."""
    try:
        slug = await service.save_manual_recipe(request)
        return {"slug": slug}
    except RecipeExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Manual recipe creation failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}")
async def get_recipe_by_slug(
    slug: str,
    service: RecipeService = Depends(get_recipe_service),
    x_private_token: Optional[str] = Header(None),
):
    """Get a recipe by its slug."""
    recipe = await service.get_recipe(slug)

    if service.is_recipe_private(recipe) and not _has_valid_private_token(x_private_token):
        raise HTTPException(status_code=404, detail="Recipe not found")

    return recipe

@router.delete("/{slug}")
async def delete_recipe(slug: str, service: RecipeService = Depends(get_recipe_service)):
    """Delete a recipe by its slug."""
    await service.delete_recipe(slug)
    return {"detail": "Recipe deleted successfully"}

@router.delete("")
async def delete_all_recipes(service: RecipeService = Depends(get_recipe_service)):
    """Delete all recipes and their associated images."""
    try:
        await service.delete_all_recipes()
        return {"detail": "All recipes have been deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
