import asyncio
import io
import logging
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recipe-files", tags=["recipe-files"])

BASE_DIR = Path(__file__).parent.parent.parent
RECIPES_DIR = BASE_DIR / "data" / "recipes"
IMAGES_DIR = RECIPES_DIR / "images"

RECIPES_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".json": "application/json",
}


def _media_type(path: Path) -> str:
    return MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")


@router.get("/list")
async def list_recipe_files():
    """List all recipe files."""
    try:
        return [
            f.name for f in RECIPES_DIR.glob("*.recipe.json")
            if f.name != "auth_presets.json"
        ]
    except Exception as e:
        logger.error(f"Error listing recipe files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_recipe_file(filename: str):
    """Download a recipe file."""
    file_path = RECIPES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/json", filename=filename)


@router.get("/list-images")
async def list_image_files():
    """List all image files."""
    try:
        return [f.name for f in IMAGES_DIR.glob("*") if f.is_file()]
    except Exception as e:
        logger.error(f"Error listing image files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-image/{filename}")
async def download_image_file(filename: str):
    """Download an image file."""
    file_path = IMAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type=_media_type(file_path), filename=filename)


async def _write_upload(file: UploadFile, dest: Path):
    """Read an uploaded file in chunks and write to disk without blocking the event loop."""
    chunk_size = 1024 * 64
    content = bytearray()
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
    await asyncio.to_thread(dest.write_bytes, bytes(content))


@router.post("/upload")
async def upload_recipe_file(file: UploadFile = File(...)):
    """Upload a recipe file."""
    try:
        file_path = RECIPES_DIR / file.filename
        await _write_upload(file, file_path)
        logger.info(f"File {file.filename} uploaded successfully to {file_path}")
        return {"message": f"File {file.filename} uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading recipe file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-image")
async def upload_recipe_image(file: UploadFile = File(...)):
    """Upload a recipe image."""
    try:
        file_path = IMAGES_DIR / file.filename
        await _write_upload(file, file_path)
        logger.info(f"Image {file.filename} uploaded successfully to {file_path}")
        return {"message": f"Image {file.filename} uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-batch")
async def upload_recipes_batch(archive: UploadFile = File(...)):
    """Upload multiple recipe files in a single ZIP archive."""
    try:
        content = await archive.read()
        zip_bytes = io.BytesIO(content)
        results = {"recipes": [], "images": []}

        with zipfile.ZipFile(zip_bytes, "r") as zip_ref:
            for filename in zip_ref.namelist():
                try:
                    basename = os.path.basename(filename)
                    file_content = zip_ref.read(filename)

                    if filename.endswith(".recipe.json"):
                        dest = RECIPES_DIR / basename
                        await asyncio.to_thread(dest.write_bytes, file_content)
                        results["recipes"].append(basename)
                    elif any(filename.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")):
                        dest = IMAGES_DIR / basename
                        await asyncio.to_thread(dest.write_bytes, file_content)
                        results["images"].append(basename)
                except Exception as e:
                    logger.error(f"Error extracting {filename}: {e}")

        logger.info(
            f"Batch upload completed: {len(results['recipes'])} recipes, "
            f"{len(results['images'])} images"
        )
        return {
            "message": "Batch upload successful",
            "uploaded_recipes": len(results["recipes"]),
            "uploaded_images": len(results["images"]),
            "details": results,
        }
    except Exception as e:
        logger.error(f"Error processing batch upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clean")
async def clean_recipe_files():
    """Clean all recipe files and images."""
    try:
        for file in RECIPES_DIR.glob("*.json"):
            if file.name != "auth_presets.json":
                file.unlink()

        for file in IMAGES_DIR.glob("*"):
            if file.is_file():
                file.unlink()

        logger.info("All recipe files and images have been cleaned")
        return {"message": "All recipe files and images have been cleaned"}
    except Exception as e:
        logger.error(f"Error cleaning files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
