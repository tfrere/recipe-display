"""Upload recipes in chunks to avoid timeout on large uploads."""

import argparse
import os
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

MAX_CHUNK_MB = 20
RECIPE_CHUNK_SIZE = 500


def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def upload_zip(session: requests.Session, base_url: str, zip_path: str, label: str, max_retries: int = 3):
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    for attempt in range(1, max_retries + 1):
        logger.info(f"Uploading {label} ({size_mb:.1f} MB) [attempt {attempt}]...")
        try:
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
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.warning(f"  Connection error: {e}")
        if attempt < max_retries:
            wait = 10 * attempt
            logger.info(f"  Retrying in {wait}s...")
            time.sleep(wait)
    logger.error(f"  All {max_retries} attempts failed for {label}")
    return False


def get_server_images(session: requests.Session, base_url: str) -> set[str]:
    try:
        resp = session.get(f"{base_url}/list-images", timeout=30)
        if resp.status_code == 200:
            return set(resp.json())
    except Exception:
        pass
    return set()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-only", action="store_true", help="Skip recipe JSONs, upload images only")
    parser.add_argument("--skip-uploaded", action="store_true", help="Skip images already on server")
    args = parser.parse_args()

    load_dotenv()
    api_base = os.getenv("RECIPE_SERVER_URL", "https://recipes-api.tfrere.com")
    base_url = f"{api_base}/api/recipe-files"
    recipes_path = Path("data/recipes")
    images_path = recipes_path / "images"
    session = create_session()

    # --- Step 1: Upload recipe JSONs ---
    if args.images_only:
        logger.info("Skipping recipe JSONs (--images-only)")
    else:
        logger.info("=== STEP 1: Upload recipe JSON files ===")
        recipe_files = sorted(recipes_path.glob("*.recipe.json"))
        logger.info(f"Found {len(recipe_files)} recipe files")

        recipe_chunks = [
            recipe_files[i : i + RECIPE_CHUNK_SIZE]
            for i in range(0, len(recipe_files), RECIPE_CHUNK_SIZE)
        ]
        logger.info(f"Split into {len(recipe_chunks)} chunks of ~{RECIPE_CHUNK_SIZE} files")

        for i, chunk in enumerate(recipe_chunks):
            label = f"recipes chunk {i + 1}/{len(recipe_chunks)} ({len(chunk)} files)"
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for f in chunk:
                        zf.write(f, arcname=f.name)
                success = upload_zip(session, base_url, tmp_path, label)
                if not success:
                    logger.error(f"Recipe chunk {i + 1} failed, stopping.")
                    return
            finally:
                os.unlink(tmp_path)
            time.sleep(2)

    # --- Step 2: Upload images in chunks ---
    logger.info("=== STEP 2: Upload images in chunks ===")
    image_files = sorted(f for f in images_path.glob("*") if f.is_file())
    logger.info(f"Found {len(image_files)} image files")

    if args.skip_uploaded:
        existing = get_server_images(session, base_url)
        before = len(image_files)
        image_files = [f for f in image_files if f.name not in existing]
        logger.info(f"Skipping {before - len(image_files)} already-uploaded images, {len(image_files)} remaining")

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

    failed_chunks = []
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
                logger.warning(f"Chunk {i + 1} failed, continuing with next...")
                failed_chunks.append(i + 1)
        finally:
            os.unlink(tmp_path)
        time.sleep(3)

    if failed_chunks:
        logger.warning(f"Failed chunks: {failed_chunks}. Re-run with --images-only --skip-uploaded to retry.")
    logger.info("=== DONE ===")


if __name__ == "__main__":
    main()
