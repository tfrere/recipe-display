from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import os
from typing import List
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recipe-files", tags=["recipe-files"])

# Définir les chemins relatifs
BASE_DIR = Path(__file__).parent.parent.parent
RECIPES_DIR = BASE_DIR / "data" / "recipes"
IMAGES_DIR = RECIPES_DIR / "images"

# Créer les dossiers s'ils n'existent pas
RECIPES_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/list")
async def list_recipe_files():
    """List all recipe files."""
    try:
        recipe_files = []
        for file in RECIPES_DIR.glob("*.recipe.json"):
            if file.name != "auth_presets.json":
                recipe_files.append(file.name)
        return recipe_files
    except Exception as e:
        logger.error(f"Error listing recipe files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_recipe_file(filename: str):
    """Download a recipe file."""
    try:
        file_path = RECIPES_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, "rb") as f:
            return f.read()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading recipe file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list-images")
async def list_image_files():
    """List all image files."""
    try:
        image_files = []
        for file in IMAGES_DIR.glob("*"):
            if file.is_file():
                image_files.append(file.name)
        return image_files
    except Exception as e:
        logger.error(f"Error listing image files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download-image/{filename}")
async def download_image_file(filename: str):
    """Download an image file."""
    try:
        file_path = IMAGES_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, "rb") as f:
            return f.read()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading image file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_recipe_file(file: UploadFile = File(...)):
    """Upload a recipe file."""
    try:
        file_path = RECIPES_DIR / file.filename
        logger.info(f"Uploading recipe file to: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File {file.filename} uploaded successfully to {file_path}")
        return {"message": f"File {file.filename} uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading recipe file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-image")
async def upload_recipe_image(file: UploadFile = File(...)):
    """Upload a recipe image."""
    try:
        file_path = IMAGES_DIR / file.filename
        logger.info(f"Uploading image to: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Image {file.filename} uploaded successfully to {file_path}")
        return {"message": f"Image {file.filename} uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clean")
async def clean_recipe_files():
    """Clean all recipe files and images."""
    try:
        logger.info(f"Cleaning files in {RECIPES_DIR} and {IMAGES_DIR}")
        
        # Delete all recipe files except auth_presets.json
        for file in RECIPES_DIR.glob("*.json"):
            if file.name != "auth_presets.json":
                logger.info(f"Deleting recipe file: {file}")
                file.unlink()
        
        # Delete all images
        for file in IMAGES_DIR.glob("*"):
            if file.is_file():
                logger.info(f"Deleting image file: {file}")
                file.unlink()
                
        logger.info("All recipe files and images have been cleaned")
        return {"message": "All recipe files and images have been cleaned"}
    except Exception as e:
        logger.error(f"Error cleaning files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 