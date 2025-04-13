from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
import os
import urllib.parse
import logging
from pathlib import Path
from typing import Optional, List

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

# Configuration des tailles d'images
IMAGE_SIZES = {
    "thumbnail": (200, 200),
    "small": (400, 400),
    "medium": (800, 800),
    "large": (1200, 1200),
    "original": None
}

# Chemins des dossiers
DATA_DIR = Path("data")  # Chemin relatif depuis server/
RECIPES_IMAGES_DIR = DATA_DIR / "recipes" / "images"  # Chemin vers les images de recettes
CACHE_DIR = DATA_DIR / "images" / "cache"  # Dossier pour stocker les versions redimensionnées

# Créer les dossiers nécessaires pour le cache
for size in IMAGE_SIZES:
    if size != "original":  # Pas besoin de cache pour les originaux
        (CACHE_DIR / size).mkdir(parents=True, exist_ok=True)

def resize_image(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Redimensionne une image en conservant son ratio."""
    # Calculer les dimensions en préservant le ratio
    img_ratio = img.width / img.height
    target_ratio = size[0] / size[1]

    if img_ratio > target_ratio:
        # Image plus large, ajuster la largeur
        new_width = size[0]
        new_height = int(new_width / img_ratio)
    else:
        # Image plus haute, ajuster la hauteur
        new_height = size[1]
        new_width = int(new_height * img_ratio)

    # Redimensionner avec Lanczos (meilleure qualité)
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

def get_all_image_files() -> List[Path]:
    """Récupère toutes les images dans le dossier des recettes."""
    if not RECIPES_IMAGES_DIR.exists():
        logger.warning(f"Le dossier d'images n'existe pas: {RECIPES_IMAGES_DIR}")
        return []
    
    all_files = []
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]:
        all_files.extend(list(RECIPES_IMAGES_DIR.glob(f"*{ext}")))
    
    logger.info(f"Images trouvées: {len(all_files)}")
    return all_files

def get_original_image_path(filename: str) -> Optional[Path]:
    """Trouve le chemin de l'image originale."""
    # Décoder l'URL au cas où
    filename = urllib.parse.unquote(filename)
    
    logger.info(f"Recherche de l'image originale: {filename}")
    logger.info(f"Dossier des images: {RECIPES_IMAGES_DIR}, existe: {RECIPES_IMAGES_DIR.exists()}")
    
    # Chercher l'original avec différentes extensions
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]:
        # Essayer avec le nom exact
        original_path = RECIPES_IMAGES_DIR / (filename + ext)
        logger.info(f"Vérification du chemin: {original_path}, existe: {original_path.exists()}")
        if original_path.exists():
            return original_path
    
    # Si le fichier n'existe pas, récupérer toutes les images et essayer de trouver
    # une correspondance partielle (insensible à la casse)
    all_images = get_all_image_files()
    filename_lower = filename.lower()
    
    for img_path in all_images:
        # Comparer les noms sans extension
        if img_path.stem.lower() == filename_lower:
            logger.info(f"Correspondance exacte trouvée: {img_path}")
            return img_path
        
        # Vérifier si le nom du fichier est un préfixe
        if img_path.stem.lower().startswith(filename_lower[:40]):
            logger.info(f"Correspondance par préfixe trouvée: {img_path}")
            return img_path
    
    logger.warning(f"Aucune image trouvée pour: {filename}")
    return None

def get_cached_image_path(filename: str, size: str) -> Optional[Path]:
    """Trouve le chemin de l'image dans le cache pour une taille donnée."""
    if size == "original":
        return get_original_image_path(filename)
    
    # Pour les autres tailles, chercher dans le cache
    for ext in [".webp", ".jpg", ".jpeg", ".png"]:
        cache_path = CACHE_DIR / size / (filename + ext)
        if cache_path.exists():
            return cache_path
    
    return None

async def ensure_resized_version(filename: str, size: str) -> Optional[Path]:
    """S'assure qu'une version redimensionnée existe et la crée si nécessaire."""
    if size == "original":
        return get_original_image_path(filename)

    # Vérifier si l'image est déjà dans le cache
    cached_path = get_cached_image_path(filename, size)
    if cached_path:
        return cached_path

    # Trouver l'original
    original_path = get_original_image_path(filename)
    if not original_path:
        return None

    # Si c'est un SVG, le retourner tel quel
    if original_path.suffix.lower() == ".svg":
        return original_path

    # Créer le dossier de destination si nécessaire
    target_dir = CACHE_DIR / size
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Chemin pour la version redimensionnée en WebP (meilleure compression)
    target_path = target_dir / (filename + ".webp")

    try:
        # Redimensionner l'image
        with Image.open(original_path) as img:
            # Convertir en RGB si nécessaire (pour les images avec transparence)
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            
            target_size = IMAGE_SIZES[size]
            resized = resize_image(img, target_size)
            
            # Sauvegarder en WebP avec une bonne qualité
            resized.save(target_path, "WEBP", quality=85, method=6)
            logger.info(f"Image redimensionnée créée: {target_path}")
            return target_path
    except Exception as e:
        logger.error(f"Erreur lors du redimensionnement de l'image {original_path}: {str(e)}")
        return original_path  # En cas d'erreur, retourner l'original

@router.get("/tmp/{filename}")
async def get_temp_image(filename: str):
    """Get a temporary image."""
    # Check if the image exists in the temp directory
    temp_image_path = Path("data/tmp") / filename
    if not temp_image_path.exists():
        raise HTTPException(status_code=404, detail="Temporary image not found")
    
    # Determine content type based on extension
    ext = temp_image_path.suffix.lower().lstrip('.')
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp"
    }
    content_type = content_type_map.get(ext, "application/octet-stream")
    
    # Return the image
    return FileResponse(temp_image_path, media_type=content_type)

@router.get("/{size}/{filename}")
async def serve_image(size: str, filename: str):
    """Sert une image dans la taille demandée."""
    logger.info(f"Demande d'image: size={size}, filename={filename}")
    
    if size not in IMAGE_SIZES:
        raise HTTPException(status_code=400, detail="Invalid size")

    # Vérifier si le nom de fichier est valide
    if not filename or filename == "undefined":
        raise HTTPException(status_code=404, detail="Image filename is invalid")

    # Décoder l'URL si nécessaire
    decoded_filename = urllib.parse.unquote(filename)
    
    # Nettoyer le nom de fichier (supprimer l'extension si présente)
    clean_filename = Path(decoded_filename).stem
    logger.info(f"Nom de fichier nettoyé: {clean_filename}")

    # Trouver ou créer l'image dans la bonne taille
    image_path = await ensure_resized_version(clean_filename, size)
    
    if not image_path or not image_path.exists():
        logger.warning(f"Image non trouvée: {clean_filename}")
        raise HTTPException(status_code=404, detail=f"Image not found: {clean_filename}")

    logger.info(f"Image trouvée: {image_path}")

    # Déterminer le type MIME
    mime_types = {
        ".svg": "image/svg+xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    media_type = mime_types.get(image_path.suffix.lower(), "application/octet-stream")
    logger.info(f"Type MIME: {media_type}")

    return FileResponse(image_path, media_type=media_type)