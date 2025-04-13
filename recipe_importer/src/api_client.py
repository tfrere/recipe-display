import asyncio
import base64
import aiohttp
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from rich.console import Console

from .models import RecipeError


class RecipeApiClient:
    """Classe responsable des interactions avec l'API de recettes."""
    
    def __init__(self, api_url: str, auth_presets: dict = None, console: Console = None):
        self.api_url = api_url.rstrip('/')  # Enlever le slash à la fin si présent
        self.console = console or Console()
        self.auth_presets = auth_presets or {}
    
    def get_auth_for_url(self, url: str) -> dict:
        """Récupère les credentials d'authentification pour une URL donnée."""
        if not self.auth_presets:
            return None
            
        # Extraire le domaine de l'URL
        domain = urlparse(url).netloc
        
        # Chercher une correspondance dans les auth_presets
        for preset_domain, preset_config in self.auth_presets.items():
            if preset_domain in domain:
                self.console.print(f"[blue]Using authentication for {domain} with preset {preset_domain}[/blue]")
                return preset_config
                
        return None
    
    async def start_url_generation(self, session: aiohttp.ClientSession, url: str, credentials: dict = None) -> str:
        """Démarre la génération de recette à partir d'URL et retourne l'ID de progression."""
        try:
            # Ajouter un timeout pour éviter les blocages
            timeout = aiohttp.ClientTimeout(total=30)  # 30 secondes maximum
            
            async with session.post(
                f"{self.api_url}/api/recipes",
                json={
                    "type": "url",
                    "url": url,
                    "text": None,
                    "image": None,
                    "credentials": credentials
                },
                timeout=timeout
            ) as response:
                if response.status == 409:
                    return None
                elif response.status == 301 or response.status == 302 or response.status == 307 or response.status == 308:
                    # Gérer les redirections
                    redirect_url = response.headers.get('Location')
                    if redirect_url:
                        self.console.print(f"[yellow]Redirecting to {redirect_url}[/yellow]")
                        async with session.post(
                            redirect_url,
                            json={
                                "type": "url",
                                "url": url,
                                "text": None,
                                "image": None,
                                "credentials": credentials
                            },
                            timeout=timeout
                        ) as redirect_response:
                            if redirect_response.status != 200:
                                raise Exception(f"Failed to start generation after redirect: {await redirect_response.text()}")
                            data = await redirect_response.json()
                            return data["progressId"]
                    else:
                        raise Exception(f"Received redirect without Location header")
                elif response.status != 200:
                    raise Exception(f"Failed to start generation: {await response.text()}")
                    
                data = await response.json()
                return data["progressId"]
        except asyncio.TimeoutError:
            raise Exception(f"API request timed out after 30 seconds")
    
    async def start_text_generation(self, session: aiohttp.ClientSession, recipe_text: str, image_base64: str = None) -> str:
        """Démarre la génération de recette à partir de texte et retourne l'ID de progression."""
        try:
            # Ajouter un timeout pour éviter les blocages
            timeout = aiohttp.ClientTimeout(total=30)  # 30 secondes maximum
            
            # Vérifier que l'image est valide si elle est fournie
            if image_base64 and not image_base64.startswith("data:image/"):
                self.console.print(f"[yellow]Warning: Image format incorrect, fixing...[/yellow]")
                # Ajuster le format si nécessaire
                image_base64 = f"data:image/jpeg;base64,{image_base64}" if "base64," not in image_base64 else image_base64
            
            # Log pour debugging
            self.console.print(f"[blue]Sending text recipe ({len(recipe_text)} chars) with image: {bool(image_base64)}[/blue]")
            
            async with session.post(
                f"{self.api_url}/api/recipes",
                json={
                    "type": "text",
                    "url": None,
                    "text": recipe_text,
                    "image": image_base64,
                    "credentials": None
                },
                timeout=timeout
            ) as response:
                if response.status == 409:
                    return None
                elif response.status == 301 or response.status == 302 or response.status == 307 or response.status == 308:
                    # Gérer les redirections
                    redirect_url = response.headers.get('Location')
                    if redirect_url:
                        self.console.print(f"[yellow]Redirecting to {redirect_url}[/yellow]")
                        async with session.post(
                            redirect_url,
                            json={
                                "type": "text",
                                "url": None,
                                "text": recipe_text,
                                "image": image_base64,
                                "credentials": None
                            },
                            timeout=timeout
                        ) as redirect_response:
                            if redirect_response.status != 200:
                                raise Exception(f"Failed to start generation after redirect: {await redirect_response.text()}")
                            data = await redirect_response.json()
                            return data["progressId"]
                    else:
                        raise Exception(f"Received redirect without Location header")
                elif response.status != 200:
                    response_text = await response.text()
                    self.console.print(f"[red]API Error: {response.status} - {response_text}[/red]")
                    raise Exception(f"Failed to start generation: {response_text}")
                    
                data = await response.json()
                return data["progressId"]
        except asyncio.TimeoutError:
            raise Exception(f"API request timed out after 30 seconds")
        except Exception as e:
            self.console.print(f"[red]Error in start_text_generation: {str(e)}[/red]")
            raise
    
    async def check_progress(self, session: aiohttp.ClientSession, progress_id: str) -> dict:
        """Vérifie la progression de la génération de recette."""
        if not progress_id:
            return {"status": "completed", "progress": 100}
        
        try:
            # Ajouter un timeout pour éviter les blocages
            timeout = aiohttp.ClientTimeout(total=30)  # 30 secondes maximum
            
            async with session.get(
                f"{self.api_url}/api/recipes/progress/{progress_id}",
                timeout=timeout
            ) as response:
                if response.status == 404:
                    raise Exception("Progress not found")
                if response.status != 200:
                    raise Exception(f"Failed to check progress: {await response.text()}")
                    
                data = await response.json()
                
                # Map server status to importer status
                if data["status"] == "error":
                    error_message = data.get("error", "Unknown error")
                    
                    # Si l'erreur concerne le slug mais que le fichier a été créé, on le considère comme un succès
                    if "Failed to extract recipe slug" in error_message or "Recipe successfully saved" in error_message:
                        self.console.print(f"[yellow]Warning: {error_message}, but recipe may have been imported successfully[/yellow]")
                        return {
                            "status": "completed",
                            "progress": 100,
                            "slug": "unknown"
                        }
                    
                    # Si l'erreur est liée à recipe_scraper.cli mais contient des éléments indiquant un succès partiel
                    if "recipe_scraper.cli" in error_message and any(success_str in error_message for success_str in ["saved to", "created", "imported"]):
                        self.console.print(f"[yellow]Warning: CLI error but recipe might have been partially imported: {error_message}[/yellow]")
                        return {
                            "status": "completed",
                            "progress": 100,
                            "slug": "unknown"
                        }
                    
                    return {
                        "status": "error",
                        "error": error_message,
                        "progress": 0
                    }
                elif data["status"] == "completed":
                    # Get the recipe slug if available
                    slug = None
                    if data.get("recipe") and isinstance(data["recipe"], dict):
                        slug = data["recipe"].get("slug")
                    
                    return {
                        "status": "completed",
                        "progress": 100,
                        "slug": slug
                    }
                else:
                    # Calculate overall progress based on steps
                    total_progress = 0
                    completed_steps = 0
                    step_count = len(data["steps"])
                    current_step_info = None
                    
                    for step in data["steps"]:
                        if step["status"] == "completed":
                            completed_steps += 1
                            total_progress += 100
                        elif step["status"] == "in_progress":
                            total_progress += step["progress"]
                            current_step_info = step
                        
                    # If no in_progress step was found but there's a currentStep
                    if not current_step_info and data.get("currentStep"):
                        # Find the step that matches currentStep
                        for step in data["steps"]:
                            if step["step"] == data["currentStep"]:
                                current_step_info = step
                                break
                    
                    # Calculate average progress
                    avg_progress = total_progress / step_count if step_count > 0 else 0
                    
                    # Create detailed status
                    result = {
                        "status": "in_progress",
                        "progress": avg_progress,
                        "current_step": data.get("currentStep", ""),
                    }
                    
                    # Add step details if available
                    if current_step_info:
                        result["step_message"] = current_step_info.get("message", "")
                        result["step_progress"] = current_step_info.get("progress", 0)
                    
                    return result
        except asyncio.TimeoutError:
            self.console.print(f"[yellow]Warning: Timeout while checking progress for {progress_id}[/yellow]")
            return {
                "status": "in_progress",
                "progress": 0,
                "current_step": "unknown",
                "step_message": "Timeout lors de la vérification, mais le serveur continue probablement le traitement"
            }
        except Exception as e:
            self.console.print(f"[red]Error checking progress: {str(e)}[/red]")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def list_imported_recipes(self, session: aiohttp.ClientSession, processed_urls: set) -> None:
        """Liste les recettes importées pendant cette session."""
        try:
            async with session.get(f"{self.api_url}/api/recipes") as response:
                if response.status != 200:
                    self.console.print(f"[red]Failed to fetch recipes: {response.status}[/red]")
                    return
                
                data = await response.json()
                
                if not data:
                    self.console.print("[yellow]No recipes found[/yellow]")
                    return
                
                self.console.print("\n[green]Successfully imported recipes:[/green]")
                
                for recipe in data:
                    # Vérifier si la recette correspond à une URL que nous avons traitée
                    source_url = recipe.get("metadata", {}).get("sourceUrl", "")
                    if source_url in processed_urls:
                        self.console.print(f"[green]- {recipe['title']} ({recipe['slug']})[/green]")
        
        except Exception as e:
            self.console.print(f"[red]Error listing recipes: {str(e)}[/red]")
    
    @staticmethod
    def encode_image(image_file: Path) -> tuple[str, str]:
        """Encode une image en base64 avec le bon type MIME."""
        if not image_file or not image_file.exists():
            return None, ""
        
        with open(image_file, 'rb') as f:
            image_data = f.read()
            
        # Déterminer le type MIME en fonction de l'extension
        mime_type = "image/jpeg"  # Par défaut
        if image_file.suffix.lower() == ".png":
            mime_type = "image/png"
        elif image_file.suffix.lower() == ".gif":
            mime_type = "image/gif"
        elif image_file.suffix.lower() == ".webp":
            mime_type = "image/webp"
        
        # Convertir en base64 avec le préfixe approprié incluant le bon type MIME
        image_base64 = f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
        
        return image_base64, mime_type 