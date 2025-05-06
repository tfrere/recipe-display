from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import os
from typing import List
import logging
import asyncio
import zipfile
import io
from starlette.responses import JSONResponse

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
        logger.info(f"File size: {os.fstat(file.file.fileno()).st_size / 1024:.2f} KB")
        
        # Utilisation d'une opération asynchrone pour ne pas bloquer le serveur
        # lors de l'écriture de fichiers volumineux
        async def save_file():
            with open(file_path, "wb") as buffer:
                # Copier par blocs pour éviter de charger tout le fichier en mémoire
                chunk_size = 1024 * 64  # 64KB chunks
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    buffer.write(chunk)
        
        await save_file()
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
        logger.info(f"Image size: {os.fstat(file.file.fileno()).st_size / 1024:.2f} KB")
        
        # Utilisation d'une opération asynchrone pour ne pas bloquer le serveur
        async def save_image():
            with open(file_path, "wb") as buffer:
                # Copier par blocs pour éviter de charger toute l'image en mémoire
                chunk_size = 1024 * 64  # 64KB chunks
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    buffer.write(chunk)
        
        await save_image()
        logger.info(f"Image {file.filename} uploaded successfully to {file_path}")
        return {"message": f"Image {file.filename} uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-batch")
async def upload_recipes_batch(archive: UploadFile = File(...)):
    """Upload multiple recipe files in a single ZIP archive."""
    try:
        logger.info(f"Receiving batch upload via ZIP archive")
        logger.info(f"Archive size: {os.fstat(archive.file.fileno()).st_size / 1024:.2f} KB")
        
        # Lecture du fichier ZIP en mémoire
        content = await archive.read()
        zip_bytes = io.BytesIO(content)
        
        # Traitement et extraction des fichiers
        results = {"recipes": [], "images": []}
        
        with zipfile.ZipFile(zip_bytes, 'r') as zip_ref:
            files_list = zip_ref.namelist()
            logger.info(f"ZIP archive contains {len(files_list)} files")
            
            for filename in files_list:
                try:
                    # Déterminer si c'est une recette ou une image
                    if filename.endswith('.recipe.json'):
                        # Extraire le fichier de recette
                        file_content = zip_ref.read(filename)
                        file_path = RECIPES_DIR / os.path.basename(filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_content)
                        
                        logger.info(f"Extracted recipe file: {os.path.basename(filename)}")
                        results["recipes"].append(os.path.basename(filename))
                    
                    elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        # Extraire l'image
                        if '/' in filename:
                            # Si l'image est dans un sous-dossier (e.g. images/)
                            img_filename = os.path.basename(filename)
                        else:
                            img_filename = filename
                        
                        file_content = zip_ref.read(filename)
                        file_path = IMAGES_DIR / img_filename
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_content)
                        
                        logger.info(f"Extracted image file: {img_filename}")
                        results["images"].append(img_filename)
                
                except Exception as e:
                    logger.error(f"Error extracting {filename}: {str(e)}")
        
        logger.info(f"Batch upload completed: {len(results['recipes'])} recipes, {len(results['images'])} images")
        return {
            "message": "Batch upload successful",
            "uploaded_recipes": len(results["recipes"]),
            "uploaded_images": len(results["images"]),
            "details": results
        }
        
    except Exception as e:
        logger.error(f"Error processing batch upload: {str(e)}")
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