"""Upload recipes in chunks to avoid timeout on large uploads."""

import os
import math
import tempfile
import zipfile
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_CHUNK_MB = 150


def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def upload_zip(session: requests.Session, base_url: str, zip_path: str, label: str):
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info(f"Uploading {label} ({size_mb:.1f} MB)...")
    with open(zip_path, "rb") as f:
        resp = session.post(
            f"{base_url}/upload-batch",
            files={"archive": ("batch.zip", f, "application/zip")},
            timeout=600,
        )
    if resp.status_code == 200:
        result = resp.json()
        logger.info(f"  OK: {result.get('uploaded_recipes', 0)} recipes, {result.get('uploaded_images', 0)} images")
        return True
    else:
        logger.error(f"  FAILED ({resp.status_code}): {resp.text[:200]}")
        return False


def main():
    load_dotenv()
    api_base = os.getenv("RECIPE_SERVER_URL", "https://recipes-api.tfrere.com")
    base_url = f"{api_base}/api/recipe-files"
    recipes_path = Path("data/recipes")
    images_path = recipes_path / "images"
    session = create_session()

    # --- Step 1: Upload all recipe JSONs (small, ~93MB) ---
    logger.info("=== STEP 1: Upload recipe JSON files ===")
    recipe_files = sorted(recipes_path.glob("*.recipe.json"))
    logger.info(f"Found {len(recipe_files)} recipe files")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in recipe_files:
                zf.write(f, arcname=f.name)
        upload_zip(session, base_url, tmp_path, f"recipes ({len(recipe_files)} files)")
    finally:
        os.unlink(tmp_path)

    # --- Step 2: Upload images in chunks ---
    logger.info("=== STEP 2: Upload images in chunks ===")
    image_files = sorted(f for f in images_path.glob("*") if f.is_file())
    logger.info(f"Found {len(image_files)} image files")

    # Compute chunk sizes
    chunk_files = []
    current_chunk = []
    current_size = 0
    max_bytes = MAX_CHUNK_MB * 1024 * 1024

    for img in image_files:
        fsize = img.stat().st_size
        if current_size + fsize > max_bytes and current_chunk:
            chunk_files.append(current_chunk)
            current_chunk = []
            current_size = 0
        current_chunk.append(img)
        current_size += fsize

    if current_chunk:
        chunk_files.append(current_chunk)

    logger.info(f"Split into {len(chunk_files)} chunks of ~{MAX_CHUNK_MB}MB")

    for i, chunk in enumerate(chunk_files):
        label = f"images chunk {i + 1}/{len(chunk_files)} ({len(chunk)} files)"
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for img in chunk:
                    zf.write(img, arcname=f"images/{img.name}")
            success = upload_zip(session, base_url, tmp_path, label)
            if not success:
                logger.error(f"Chunk {i + 1} failed, stopping.")
                break
        finally:
            os.unlink(tmp_path)
        time.sleep(2)

    logger.info("=== DONE ===")


if __name__ == "__main__":
    main()
