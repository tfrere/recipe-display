from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
import os
from pathlib import Path
from typing import Optional

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
DATA_DIR = Path("data")
RECIPES_DIR = DATA_DIR / "recipes"
IMAGES_DIR = RECIPES_DIR / "images"
ORIGINAL_DIR = IMAGES_DIR / "original"

# Créer les dossiers nécessaires
for size in IMAGE_SIZES:
    (IMAGES_DIR / size).mkdir(parents=True, exist_ok=True)

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

def get_image_path(filename: str, size: str) -> Optional[Path]:
    """Trouve le chemin de l'image pour une taille donnée."""
    print(f"[DEBUG] get_image_path: Looking for {filename} in size {size}")
    
    # Pour les originaux
    if size == "original":
        # Chercher l'original avec différentes extensions
        for ext in [".svg", ".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            original_path = ORIGINAL_DIR / (filename + ext)
            print(f"[DEBUG] Checking original path: {original_path}")
            if original_path.exists():
                print(f"[DEBUG] Found original at: {original_path}")
                return original_path
        print("[DEBUG] No original found")
        return None

    # Pour les autres tailles
    # D'abord vérifier si c'est un SVG dans le dossier original
    svg_path = ORIGINAL_DIR / (filename + ".svg")
    print(f"[DEBUG] Checking for SVG: {svg_path}")
    if svg_path.exists():
        print(f"[DEBUG] Found SVG at: {svg_path}")
        return svg_path

    # Sinon chercher la version redimensionnée en WebP
    webp_path = IMAGES_DIR / size / (filename + ".webp")
    print(f"[DEBUG] Checking for WebP: {webp_path}")
    if webp_path.exists():
        print(f"[DEBUG] Found WebP at: {webp_path}")
        return webp_path

    print("[DEBUG] No image found")
    return None

async def ensure_resized_version(filename: str, size: str) -> Optional[Path]:
    """S'assure qu'une version redimensionnée existe et la crée si nécessaire."""
    if size == "original":
        return get_image_path(filename, "original")

    target_path = IMAGES_DIR / size / (filename + ".webp")
    if target_path.exists():
        return target_path

    # Trouver l'original
    original_path = get_image_path(filename, "original")
    if not original_path:
        return None

    # Si c'est un SVG, le retourner tel quel
    if original_path.suffix.lower() == ".svg":
        return original_path

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
        
        # Créer le dossier de destination si nécessaire
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder en WebP avec une bonne qualité
        resized.save(target_path, "WEBP", quality=85, method=6)
        return target_path

@router.get("/{size}/{filename}")
async def serve_image(size: str, filename: str):
    """Sert une image dans la taille demandée."""
    print(f"[DEBUG] Serving image: size={size}, filename={filename}")
    
    if size not in IMAGE_SIZES:
        print(f"[DEBUG] Invalid size: {size}")
        raise HTTPException(status_code=400, detail="Invalid size")

    # Vérifier si le nom de fichier est undefined
    if filename == "undefined":
        print("[DEBUG] Filename is undefined")
        raise HTTPException(status_code=404, detail="Image filename is undefined")

    # Nettoyer le nom de fichier
    filename = Path(filename).stem
    print(f"[DEBUG] Cleaned filename: {filename}")

    # Trouver ou créer l'image dans la bonne taille
    image_path = await ensure_resized_version(filename, size)
    print(f"[DEBUG] Image path from ensure_resized_version: {image_path}")
    
    if not image_path:
        print("[DEBUG] Image path is None")
        raise HTTPException(status_code=404, detail="Image not found")

    # Vérifier si le fichier existe réellement
    if not image_path.exists():
        print(f"[DEBUG] Image file does not exist: {image_path}")
        raise HTTPException(status_code=404, detail="Image file not found")

    print(f"[DEBUG] Image file exists: {image_path}")

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
    print(f"[DEBUG] Media type: {media_type}")

    return FileResponse(image_path, media_type=media_type)