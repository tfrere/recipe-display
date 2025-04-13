from fastapi import APIRouter, Depends, HTTPException
from typing import List
from models.requests import GenerateRecipeRequest
from models.responses import RecipeListItem, GenerateRecipeResponse
from models.progress import GenerationProgress
from services.recipe_service import RecipeService, RecipeExistsError
import os

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

def get_recipe_service():
    """Dependency that provides a RecipeService instance."""
    # Utiliser la variable d'environnement DATA_PATH si elle existe
    data_path = os.getenv("DATA_PATH", "data")
    print(f"[DEBUG] Initializing RecipeService with base_path: {data_path}")
    return RecipeService(base_path=data_path)

@router.get("/progress/{task_id}", response_model=GenerationProgress)
async def get_generation_progress(task_id: str, service: RecipeService = Depends(get_recipe_service)):
    """Get the progress of a recipe generation."""
    progress = await service.get_generation_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Progress not found for ID: {task_id}")
    return progress

@router.options("/progress/{task_id}")
async def options_generation_progress():
    """Handle OPTIONS request for CORS."""
    return {"detail": "OK"}

@router.get("", response_model=List[RecipeListItem])
async def list_recipes(include_private: bool = False, service: RecipeService = Depends(get_recipe_service)):
    """Get list of all recipes with their metadata."""
    return await service.list_recipes(include_private)

@router.options("")
async def options_recipes():
    """Handle OPTIONS request for CORS."""
    return {"detail": "OK"}

@router.post("", response_model=GenerateRecipeResponse)
async def generate_recipe(request: GenerateRecipeRequest, service: RecipeService = Depends(get_recipe_service)):
    """Generate a recipe from a URL or text content."""
    try:
        print("[DEBUG] Starting recipe generation request")
        print(f"[DEBUG] Request type: {request.type}")
        print(f"[DEBUG] Request URL: {request.url}")
        print(f"[DEBUG] Request text length: {len(request.text) if request.text else 0}")
        print(f"[DEBUG] Request has image: {bool(request.image)}")
        
        # Get progress ID first
        progress_id = await service.generate_recipe(
            import_type=request.type,
            url=request.url,
            text=request.text,
            image=request.image,
            credentials=request.credentials
        )
        
        print(f"[DEBUG] Recipe generation started with progress ID: {progress_id}")
        
        # Return immediately with progress ID
        return {"progressId": progress_id}
        
    except RecipeExistsError as e:
        print(f"[ERROR] Recipe exists error: {str(e)}")
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        print(f"[ERROR] Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Unexpected error in generate_recipe: {str(e)}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{slug}")
async def get_recipe_by_slug(slug: str, service: RecipeService = Depends(get_recipe_service)):
    """Get a recipe by its slug."""
    return await service.get_recipe(slug)

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

@router.options("")
async def options_recipes():
    """Handle OPTIONS request for CORS."""
    return {"detail": "OK"}