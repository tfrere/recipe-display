import os
import requests
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_recipes():
    """Download all recipes and images from the server."""
    load_dotenv()
    # Build base URL with correct API path
    api_base = os.getenv("RECIPE_SERVER_URL", "https://recipes-api.tfrere.com")
    base_url = f"{api_base}/api/recipe-files"
    
    if not api_base:
        raise ValueError("RECIPE_SERVER_URL environment variable is not set")

    recipes_path = Path("data/recipes")
    images_path = recipes_path / "images"

    # Create directories if they don't exist
    recipes_path.mkdir(parents=True, exist_ok=True)
    images_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Using API URL: {base_url}")
    logger.info(f"Saving recipes to: {recipes_path}")
    logger.info(f"Saving images to: {images_path}")

    try:
        # Download recipe files
        response = requests.get(f"{base_url}/list")
        if response.status_code != 200:
            logger.error(f"Error getting recipe list: {response.text}")
            return

        recipe_files = response.json()
        for recipe_file in recipe_files:
            if not recipe_file.endswith(".recipe.json"):
                continue

            download_url = f"{base_url}/download/{recipe_file}"
            response = requests.get(download_url)
            
            if response.status_code == 200:
                file_path = recipes_path / recipe_file
                with open(file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded {recipe_file}")
            else:
                logger.error(f"Error downloading {recipe_file}: {response.text}")

        # Download images
        response = requests.get(f"{base_url}/list-images")
        if response.status_code != 200:
            logger.error(f"Error getting image list: {response.text}")
            return

        image_files = response.json()
        for image_file in image_files:
            download_url = f"{base_url}/download-image/{image_file}"
            response = requests.get(download_url)
            
            if response.status_code == 200:
                file_path = images_path / image_file
                with open(file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded image {image_file}")
            else:
                logger.error(f"Error downloading image {image_file}: {response.text}")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    download_recipes() 