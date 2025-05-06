import os
import requests
import tempfile
import zipfile
from pathlib import Path
import glob
from dotenv import load_dotenv
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_session_with_retries():
    """Crée une session requests avec une stratégie de retry configurée."""
    session = requests.Session()
    retries = Retry(
        total=5,  # Nombre total de tentatives
        backoff_factor=1,  # Facteur de backoff entre les tentatives
        status_forcelist=[502, 503, 504, 429],  # Status codes à retenter
        allowed_methods=["POST", "GET"]  # Méthodes HTTP pour lesquelles retenter
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

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
    
    # Créer une session avec retries
    session = create_session_with_retries()
    
    # Méthode 1: Upload par lot (batch) avec archive ZIP
    upload_recipes_batch(session, base_url, recipes_path, images_path)
    
    # Méthode 2 (fallback): Upload fichier par fichier si la méthode 1 échoue
    # upload_recipes_individual(session, base_url, recipes_path, images_path)

def upload_recipes_batch(session, base_url, recipes_path, images_path):
    """Upload toutes les recettes et images en une seule fois via une archive ZIP."""
    try:
        # Créer un fichier ZIP temporaire
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip_file:
            temp_zip_path = temp_zip_file.name
        
        logger.info(f"Preparing ZIP archive at {temp_zip_path}")
        
        # Collecter les fichiers à ajouter
        recipe_files = [f for f in recipes_path.glob("*.recipe.json*") if f.name != "auth_presets.json"]
        image_files = [f for f in images_path.glob("*") if f.is_file()]
        
        # Créer l'archive ZIP
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Ajouter les recettes
            for recipe_file in recipe_files:
                # Extraire le nom de base sans timestamp
                base_name = recipe_file.name.split(".recipe.json")[0] + ".recipe.json"
                zipf.write(recipe_file, arcname=base_name)
            
            # Ajouter les images dans un sous-dossier "images"
            for image_file in image_files:
                zipf.write(image_file, arcname=f"images/{image_file.name}")
        
        # Obtenir la taille du fichier ZIP
        zip_size = os.path.getsize(temp_zip_path) / (1024 * 1024)  # en MB
        logger.info(f"Created ZIP archive with {len(recipe_files)} recipes and {len(image_files)} images ({zip_size:.2f} MB)")
        
        # Envoyer l'archive au serveur
        with open(temp_zip_path, 'rb') as zip_file:
            files = {"archive": ("recipes.zip", zip_file, "application/zip")}
            logger.info(f"Uploading ZIP archive to {base_url}/upload-batch")
            response = session.post(f"{base_url}/upload-batch", files=files, timeout=300)  # Timeout élevé pour les gros fichiers
        
        # Vérifier la réponse
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Batch upload successful: {result.get('uploaded_recipes')} recipes, {result.get('uploaded_images')} images")
            return True
        else:
            logger.error(f"Error with batch upload: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        return False
    finally:
        # Supprimer le fichier temporaire
        if os.path.exists(temp_zip_path):
            os.unlink(temp_zip_path)
            logger.info(f"Temporary ZIP file deleted")

def upload_recipes_individual(session, base_url, recipes_path, images_path):
    """Upload les recettes et images individuellement (méthode de secours)."""
    logger.info("Using individual file upload method")
    
    # Upload recipe files
    for recipe_file in recipes_path.glob("*.recipe.json*"):
        if recipe_file.name != "auth_presets.json":
            # Extract the base name without timestamp
            base_name = recipe_file.name.split(".recipe.json")[0] + ".recipe.json"
            
            # Vérifier la taille du fichier
            file_size = recipe_file.stat().st_size
            logger.info(f"Uploading {base_name} (size: {file_size/1024:.2f} KB)")
            
            try:
                with open(recipe_file, "rb") as f:
                    files = {"file": (base_name, f, "application/json")}
                    # Augmenter le timeout à 60 secondes
                    response = session.post(f"{base_url}/upload", files=files, timeout=60)
                    logger.info(f"Uploaded {base_name}: {response.status_code}")
                    if response.status_code != 200:
                        logger.error(f"Error uploading {base_name}: {response.text}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception uploading {base_name}: {str(e)}")
                # Attendre avant de continuer avec le fichier suivant
                time.sleep(2)

    # Upload images
    for image_file in images_path.glob("*"):
        if image_file.is_file():
            try:
                with open(image_file, "rb") as f:
                    files = {"file": (image_file.name, f, "image/jpeg")}
                    # Augmenter le timeout à 30 secondes
                    response = session.post(f"{base_url}/upload-image", files=files, timeout=30)
                    logger.info(f"Uploaded image {image_file.name}: {response.status_code}")
                    if response.status_code != 200:
                        logger.error(f"Error uploading {image_file.name}: {response.text}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception uploading {image_file.name}: {str(e)}")
                # Attendre avant de continuer avec le fichier suivant
                time.sleep(2)

if __name__ == "__main__":
    upload_recipes() 