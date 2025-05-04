import os
import requests
from pathlib import Path
import glob
from dotenv import load_dotenv
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_recipes():
    """Upload all recipes and images to the server."""
    load_dotenv()
    # Construire l'URL de base avec le bon chemin d'API
    api_base = os.getenv("RECIPE_SERVER_URL", "https://recipes-api.tfrere.com")
    base_url = f"{api_base}/api/recipe-files"
    
    if not api_base:
        raise ValueError("RECIPE_SERVER_URL environment variable is not set")

    recipes_path = Path("data/recipes")
    images_path = recipes_path / "images"

    logger.info(f"Using API URL: {base_url}")
    logger.info(f"Looking for recipes in: {recipes_path}")
    logger.info(f"Looking for images in: {images_path}")

    # Upload recipe files
    for recipe_file in recipes_path.glob("*.recipe.json*"):
        if recipe_file.name != "auth_presets.json":
            # Extract the base name without timestamp
            base_name = recipe_file.name.split(".recipe.json")[0] + ".recipe.json"
            with open(recipe_file, "rb") as f:
                files = {"file": (base_name, f, "application/json")}
                response = requests.post(f"{base_url}/upload", files=files)
                logger.info(f"Uploaded {base_name}: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Error uploading {base_name}: {response.text}")

    # Upload images
    for image_file in images_path.glob("*"):
        if image_file.is_file():
            with open(image_file, "rb") as f:
                files = {"file": (image_file.name, f, "image/jpeg")}
                response = requests.post(f"{base_url}/upload-image", files=files)
                logger.info(f"Uploaded image {image_file.name}: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Error uploading {image_file.name}: {response.text}")

if __name__ == "__main__":
    upload_recipes() 