import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import aiohttp
import aiofiles
from PIL import Image
import io
from ..models.recipe import Recipe

class RecipeStorage:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.recipes_path = self.base_path / "recipes"
        self.images_path = self.recipes_path / "images"
        self.errors_path = self.recipes_path / "errors"
        self._ensure_directories()

    def _ensure_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas."""
        self.recipes_path.mkdir(parents=True, exist_ok=True)
        self.images_path.mkdir(parents=True, exist_ok=True)
        self.errors_path.mkdir(parents=True, exist_ok=True)
        
        # Créer les sous-dossiers pour les différentes tailles d'images
        image_sizes = ["original", "thumbnail", "small", "medium", "large"]
        for size in image_sizes:
            (self.images_path / size).mkdir(parents=True, exist_ok=True)

    def _generate_slug(self, title: str) -> str:
        """Génère un slug à partir du titre."""
        # Convertir en minuscules
        slug = title.lower()
        # Remplacer les caractères accentués
        slug = slug.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        slug = slug.replace('à', 'a').replace('â', 'a')
        slug = slug.replace('î', 'i').replace('ï', 'i')
        slug = slug.replace('ô', 'o').replace('ö', 'o')
        slug = slug.replace('û', 'u').replace('ü', 'u')
        slug = slug.replace('ç', 'c')
        # Remplacer les espaces et caractères spéciaux par des tirets
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Supprimer les tirets en début et fin
        slug = slug.strip('-')
        return slug

    async def exists_by_source_url(self, source_url: str) -> bool:
        """Vérifie si une recette avec cette URL source existe déjà."""
        if not source_url:
            return False

        # Parcourir tous les fichiers de recettes
        for recipe_file in self.recipes_path.glob("*.json"):
            if recipe_file.is_file():
                try:
                    async with aiofiles.open(recipe_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        recipe_data = json.loads(content)
                        if recipe_data.get("metadata", {}).get("sourceUrl") == source_url:
                            return True
                except Exception as e:
                    print(f"Erreur lors de la lecture de {recipe_file}: {e}")
                    continue

        return False

    async def save_recipe(self, recipe: Recipe, generation_data: dict = None) -> None:
        """Save a recipe and its associated image."""
        try:
            # 1. Télécharger l'image si une URL est fournie
            if recipe.metadata.sourceImageUrl:
                print(f"\nTéléchargement de l'image depuis {recipe.metadata.sourceImageUrl}...")
                try:
                    relative_img_path = await self._download_image(
                        recipe.metadata.sourceImageUrl,
                        recipe.metadata.slug
                    )
                    recipe.metadata.imageUrl = relative_img_path
                    print(f"Image sauvegardée : {relative_img_path}")
                except Exception as e:
                    print(f"Erreur lors du téléchargement de l'image : {e}")
                    error_data = {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "recipe": recipe.model_dump(),
                        "generation_data": generation_data,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self._save_error("recipe_error", error_data)
                    raise

            # 2. Sauvegarder la recette en JSON
            recipe_path = self.recipes_path / f"{recipe.metadata.slug}.recipe.json"
            recipe_json = recipe.model_dump_json(indent=2)
            
            async with aiofiles.open(recipe_path, 'w') as f:
                await f.write(recipe_json)
            print(f"Recette sauvegardée : {recipe_path}")

        except Exception as e:
            print(f"Erreur lors de la sauvegarde : {e}")
            # Sauvegarder l'erreur générale
            error_data = {
                "error": str(e),
                "error_type": type(e).__name__,
                "recipe": recipe.model_dump() if recipe else None,
                "generation_data": generation_data,
                "timestamp": datetime.now().isoformat()
            }
            await self._save_error("error", error_data)
            raise

    async def _save_image(self, image_url: str, slug: str) -> Optional[str]:
        """Télécharge et sauvegarde une image."""
        try:
            # Créer une session HTTP
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise ValueError(f"Impossible de télécharger l'image. Status: {response.status}")
                    
                    # Déterminer l'extension du fichier à partir du Content-Type
                    content_type = response.headers.get('Content-Type', '')
                    extension = self._get_extension_from_content_type(content_type)
                    if not extension:
                        # Essayer d'obtenir l'extension depuis l'URL
                        extension = Path(urlparse(image_url).path).suffix
                        if not extension:
                            extension = '.jpg'  # Extension par défaut
                    
                    # Créer le chemin de l'image
                    image_path = self.images_path / f"{slug}{extension}"
                    
                    # Sauvegarder l'image
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(await response.read())
                    
                    return str(image_path)
        except Exception as e:
            print(f"Erreur lors du téléchargement de l'image : {e}")
            return None

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Détermine l'extension de fichier à partir du Content-Type."""
        content_type = content_type.lower()
        if 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'png' in content_type:
            return '.png'
        elif 'gif' in content_type:
            return '.gif'
        elif 'webp' in content_type:
            return '.webp'
        elif 'svg' in content_type:
            return '.svg'
        return ''

    async def _download_image(self, url: str, slug: str) -> str:
        """Download and save an image, return the relative path."""
        try:
            # Configurer les headers pour simuler un navigateur web
            parsed_url = urlparse(url)
            origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Utiliser le même user-agent que le scraper
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': origin,
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"macOS"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers, allow_redirects=True, ssl=False) as response:
                        if response.status != 200:
                            error_msg = f"Failed to download image. Status: {response.status}"
                            error_data = {
                                "error": error_msg,
                                "url": url,
                                "status": response.status,
                                "headers_sent": headers,
                                "headers_received": dict(response.headers),
                                "timestamp": datetime.now().isoformat()
                            }
                            await self._save_error("image_error", error_data)
                            raise ValueError(error_msg)
                        
                        # Vérifier le Content-Type
                        content_type = response.headers.get('content-type', '').lower()
                        if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                            error_msg = f"Le contenu téléchargé n'est pas une image (Content-Type: {content_type})"
                            error_data = {
                                "error": error_msg,
                                "url": url,
                                "content_type": content_type,
                                "timestamp": datetime.now().isoformat()
                            }
                            await self._save_error("image_error", error_data)
                            raise ValueError(error_msg)
                        
                        # Lire les données de l'image
                        data = await response.read()
                        
                        # Vérifier que c'est une image valide avec PIL
                        try:
                            img = Image.open(io.BytesIO(data))
                            img.verify()  # Vérifie que l'image est valide
                            img.close()
                        except Exception as e:
                            error_msg = f"Le fichier téléchargé n'est pas une image valide : {str(e)}"
                            error_data = {
                                "error": error_msg,
                                "url": url,
                                "content_type": content_type,
                                "error_details": str(e),
                                "timestamp": datetime.now().isoformat()
                            }
                            await self._save_error("image_error", error_data)
                            raise ValueError(error_msg)
                        
                        # Détecter le type de l'image depuis les headers
                        ext = content_type.split('/')[-1]
                        if ext not in ['jpeg', 'jpg', 'png', 'webp', 'svg']:
                            # Essayer d'obtenir l'extension depuis l'URL
                            url_ext = Path(urlparse(url).path).suffix.lower()
                            if url_ext in ['.jpg', '.jpeg', '.png', '.webp', '.svg']:
                                ext = url_ext[1:]
                            else:
                                # Par défaut, utiliser jpg
                                ext = 'jpg'
                        
                        # Générer un nom de fichier unique
                        filename = f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                        file_path = self.images_path / filename
                        
                        # Sauvegarder l'image
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(data)
                        
                        # Retourner le chemin relatif
                        return str(file_path.relative_to(self.recipes_path))
                except aiohttp.ClientError as e:
                    error_msg = f"Network error while downloading image: {str(e)}"
                    error_data = {
                        "error": error_msg,
                        "url": url,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await self._save_error("image_error", error_data)
                    raise ValueError(error_msg)
        except Exception as e:
            if not isinstance(e, ValueError):
                error_msg = f"Unexpected error while downloading image: {str(e)}"
                error_data = {
                    "error": error_msg,
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                await self._save_error("image_error", error_data)
                raise ValueError(error_msg)
            raise

    async def _save_error(self, prefix: str, error_data: dict) -> None:
        """Save error data to a file in the errors directory."""
        try:
            # Ensure errors directory exists
            self.errors_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
            error_file = self.errors_path / f"{prefix}_{timestamp}.json"
            
            # Save error data
            async with aiofiles.open(error_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(error_data, indent=2, ensure_ascii=False))
            print(f"Error saved to: {error_file}")
        except Exception as e:
            print(f"Failed to save error data: {str(e)}")
            print("Error data:", json.dumps(error_data, indent=2, ensure_ascii=False))