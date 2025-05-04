from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import os
from typing import List

router = APIRouter(prefix="/api/recipe-files", tags=["recipe-files"])

@router.post("/upload")
async def upload_recipe_file(file: UploadFile = File(...)):
    """Upload a recipe file."""
    try:
        file_path = Path("data/recipes") / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"File {file.filename} uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-image")
async def upload_recipe_image(file: UploadFile = File(...)):
    """Upload a recipe image."""
    try:
        file_path = Path("data/recipes/images") / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"Image {file.filename} uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clean")
async def clean_recipe_files():
    """Clean all recipe files and images."""
    try:
        recipes_path = Path("data/recipes")
        images_path = recipes_path / "images"
        
        # Delete all recipe files except auth_presets.json
        for file in recipes_path.glob("*.json"):
            if file.name != "auth_presets.json":
                file.unlink()
        
        # Delete all images
        for file in images_path.glob("*"):
            if file.is_file():
                file.unlink()
                
        return {"message": "All recipe files and images have been cleaned"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 