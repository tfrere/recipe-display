import requests
from dotenv import load_dotenv
import os
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_recipes():
    """Clean all recipes and images from the server."""
    load_dotenv()
    # Construire l'URL de base avec le bon chemin d'API
    api_base = os.getenv("RECIPE_SERVER_URL", "https://recipes-api.tfrere.com")
    base_url = f"{api_base}/api/recipe-files"
    
    if not api_base:
        raise ValueError("RECIPE_SERVER_URL environment variable is not set")

    logger.info(f"Using API URL: {base_url}")
    logger.info("Cleaning all recipes and images...")

    response = requests.delete(f"{base_url}/clean")
    logger.info(f"Clean response: {response.status_code}")
    
    if response.status_code != 200:
        logger.error(f"Error cleaning recipes: {response.text}")
    else:
        logger.info("Successfully cleaned all recipes and images")

if __name__ == "__main__":
    clean_recipes() 