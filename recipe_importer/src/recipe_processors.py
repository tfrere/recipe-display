import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

from .models import RecipeProgress, RecipeError, ImportMetrics
from .api_client import RecipeApiClient


class RecipeProcessorBase:
    """Classe de base pour les processeurs de recettes."""
    
    def __init__(self, api_client: RecipeApiClient, metrics: ImportMetrics, semaphore: asyncio.Semaphore):
        self.api_client = api_client
        self.metrics = metrics
        self.semaphore = semaphore
        self.processed_items = set()
    
    async def process(self, item, stats: Dict, updates_queue: asyncio.Queue) -> None:
        """Méthode abstraite pour traiter une recette."""
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    async def check_progress_until_complete(
        self, 
        session: aiohttp.ClientSession, 
        progress_id: str, 
        item_id: str, 
        stats: Dict,
        updates_queue: asyncio.Queue,
        max_stall_time: int = 3600
    ) -> bool:
        """Vérifie la progression jusqu'à la fin et met à jour les statistiques."""
        # Mettre à jour l'heure du dernier progrès
        last_progress_time = datetime.now()
        last_step_message = ""
        last_step = ""
        
        # Variable pour indiquer si la recette a été traitée avec succès
        recipe_succeeded = False
        
        # Variables pour suivre si certaines étapes clés ont été atteintes
        recipe_saved = False
        
        while True:
            # Vérifier si la tâche est bloquée depuis trop longtemps
            stall_time = (datetime.now() - last_progress_time).total_seconds()
            if stall_time > max_stall_time:
                raise Exception(f"Task stalled for {stall_time:.1f}s without progress")
            
            # Vérifier la progression
            status = await self.api_client.check_progress(session, progress_id)
            
            # Si terminé avec succès
            if status.get("status") == "completed":
                self.metrics.success_count += 1
                stats["success"] += 1
                recipe_succeeded = True  # Marquer comme réussie
                
                # Obtenir le slug si disponible
                slug_display = status.get("slug", "unknown")
                if slug_display == "unknown":
                    slug_display = "imported successfully"
                    
                await updates_queue.put((item_id, "success", f"Imported → {slug_display}"))
                break
                
            # Si erreur
            elif status.get("status") == "error":
                error_message = status.get("error", "Unknown error")
                # Vérifier si c'est une erreur de recette déjà existante
                if "already exists" in error_message.lower():
                    self.metrics.skip_count += 1
                    stats["skipped"] += 1
                    await updates_queue.put((item_id, "skipped", "Skipped (already exists)"))
                    return False
                else:
                    # Si l'étape de sauvegarde a été atteinte, considérer comme un succès partiel
                    if recipe_saved:
                        await updates_queue.put((item_id, "warning", f"Partial success (with error: {error_message})"))
                        self.metrics.success_count += 1
                        stats["success"] += 1
                        return True
                        
                    # Si c'est une véritable erreur
                    self.metrics.failure_count += 1
                    stats["errors"] += 1
                    self.metrics.errors.append(
                        RecipeError(
                            url=item_id,
                            error=error_message,
                            timestamp=datetime.now()
                        )
                    )
                    await updates_queue.put((item_id, "error", f"Error: {error_message}"))
                    return False
            
            # Mettre à jour la progression
            current_progress = status.get("progress", 0)
            current_step = status.get("current_step", "")
            
            # Vérifier si l'étape de sauvegarde est en cours ou complétée
            if current_step == "save_recipe" or any(step for step in status.get("steps", []) 
                    if step.get("step") == "save_recipe" and step.get("status") in ["in_progress", "completed"]):
                recipe_saved = True
            
            # Enregistrer l'étape actuelle pour les messages d'attente
            if current_step and current_step != last_step:
                last_step = current_step
                # Envoyer un message spécifique pour l'étape
                await updates_queue.put((item_id, "step", f"step: {current_step}"))
                # Réinitialiser le temps d'attente car nous avons changé d'étape
                last_progress_time = datetime.now()
            
            # Si un nouveau message d'étape est disponible
            step_message = status.get("step_message", "")
            if step_message and step_message != last_step_message:
                last_step_message = step_message
                await updates_queue.put((item_id, "progress", step_message))
                # Mettre à jour l'heure du dernier progrès
                last_progress_time = datetime.now()
                
                # Vérifier les indices que la recette a été sauvegardée dans le message
                if any(save_keyword in step_message.lower() for save_keyword in 
                    ["saved", "saving", "created", "sauvegarde", "enregistrée"]):
                    recipe_saved = True
            
            # Log pour debugging avec l'étape explicitement mentionnée
            if stall_time > 10 and (datetime.now() - last_progress_time).total_seconds() % 5 < 0.1:
                await updates_queue.put((item_id, "info", f"Still waiting... ({stall_time:.1f}s, step: {current_step})"))
                
            # Courte pause avant la prochaine vérification
            await asyncio.sleep(1)
        
        # Si on arrive ici sans exception et avec recipe_succeeded, c'est un succès
        return recipe_succeeded


class UrlRecipeProcessor(RecipeProcessorBase):
    """Processeur pour les recettes basées sur des URLs."""
    
    async def process(self, url: str, stats: Dict, updates_queue: asyncio.Queue) -> None:
        """Traite une recette à partir d'une URL."""
        # Indiquer que la tâche est en attente au sémaphore
        await updates_queue.put((url, "info", "Waiting for semaphore..."))
        
        # Timestamp pour détecter les blocages
        waiting_start_time = datetime.now()
        
        # Incrémenter le compteur des tâches en attente de sémaphore
        stats["waiting_for_semaphore"] = stats.get("waiting_for_semaphore", 0) + 1
        
        async with self.semaphore:
            start_time = datetime.now()
            waiting_duration = (start_time - waiting_start_time).total_seconds()
            await updates_queue.put((url, "info", f"Got semaphore after {waiting_duration:.1f}s"))
            
            # Décrémenter le compteur des tâches en attente de sémaphore
            stats["waiting_for_semaphore"] = max(0, stats.get("waiting_for_semaphore", 1) - 1)
            
            # Incrémenter le compteur de tâches en cours
            stats["in_progress"] += 1
            
            # Signaler le début de l'importation
            await updates_queue.put((url, "info", "Starting import"))
            
            try:
                # Initialiser le suivi de progression
                recipe_progress = RecipeProgress(
                    url=url,
                    status="pending",
                    progress=0,
                    current_step="initializing",
                    progress_id="",
                    start_time=start_time,
                    last_update=start_time
                )
                
                # Ajouter l'URL à la liste des URLs traitées
                self.processed_items.add(url)
                
                # Récupérer les identifiants pour cette URL si disponibles
                credentials = self.api_client.get_auth_for_url(url)
                
                # Créer une session avec timeout par défaut
                timeout = aiohttp.ClientTimeout(total=30, sock_connect=10, sock_read=20)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    # Démarrer la génération de la recette
                    await updates_queue.put((url, "info", "Calling API to start generation"))
                    progress_id = await self.api_client.start_url_generation(session, url, credentials)
                    await updates_queue.put((url, "info", f"Got progress ID: {progress_id if progress_id else 'None'}"))
                    recipe_progress.progress_id = progress_id
                    
                    # Si l'URL existe déjà, la marquer comme ignorée
                    if progress_id is None:
                        self.metrics.skip_count += 1
                        stats["skipped"] += 1
                        stats["in_progress"] -= 1
                        await updates_queue.put((url, "skipped", "Skipped (already exists)"))
                        return
                    
                    # Vérifier la progression jusqu'à la fin
                    recipe_succeeded = await self.check_progress_until_complete(
                        session=session,
                        progress_id=progress_id,
                        item_id=url,
                        stats=stats,
                        updates_queue=updates_queue
                    )
                    
                    # Log de débogage pour les recettes réussies
                    if recipe_succeeded:
                        await updates_queue.put((url, "debug", f"Recipe successfully imported (verified)"))
            
            except Exception as e:
                # Enregistrer l'erreur
                self.metrics.errors.append(
                    RecipeError(
                        url=url,
                        error=str(e),
                        timestamp=datetime.now()
                    )
                )
                self.metrics.failure_count += 1
                stats["errors"] += 1
                
                # Notifier l'erreur
                await updates_queue.put((url, "error", f"Error: {str(e)}"))
                
            finally:
                # Décrémenter le compteur de tâches en cours seulement si on n'a pas déjà quitté la fonction
                if stats["in_progress"] > 0:
                    stats["in_progress"] -= 1
                
                # Mettre à jour la durée totale
                duration = datetime.now() - start_time
                self.metrics.total_duration += duration
                
                # Incrémenter le compteur de tâches terminées
                stats["completed"] += 1


class TextRecipeProcessor(RecipeProcessorBase):
    """Processeur pour les recettes basées sur des fichiers texte."""
    
    async def process(self, recipe_files: Tuple[Path, Optional[Path]], stats: Dict, updates_queue: asyncio.Queue) -> None:
        """Traite une recette à partir d'un fichier texte et éventuellement une image."""
        text_file, image_file = recipe_files
        recipe_id = text_file.stem  # L'identifiant unique de la recette
        
        # Indiquer que la tâche est en attente au sémaphore
        await updates_queue.put((str(text_file), "info", "Waiting for semaphore..."))
        
        # Timestamp pour détecter les blocages
        waiting_start_time = datetime.now()
        
        # Incrémenter le compteur des tâches en attente de sémaphore
        stats["waiting_for_semaphore"] = stats.get("waiting_for_semaphore", 0) + 1
        
        async with self.semaphore:
            start_time = datetime.now()
            waiting_duration = (start_time - waiting_start_time).total_seconds()
            await updates_queue.put((str(text_file), "info", f"Got semaphore after {waiting_duration:.1f}s"))
            
            # Décrémenter le compteur des tâches en attente de sémaphore
            stats["waiting_for_semaphore"] = max(0, stats.get("waiting_for_semaphore", 1) - 1)
            
            # Incrémenter le compteur de tâches en cours
            stats["in_progress"] += 1
            
            # Signaler le début de l'importation
            await updates_queue.put((str(text_file), "info", f"Starting import for {recipe_id}"))
            
            try:
                # Initialiser le suivi de progression
                recipe_progress = RecipeProgress(
                    url=str(text_file),  # Utiliser le chemin du fichier comme "url" pour la progression
                    status="pending",
                    progress=0,
                    current_step="initializing",
                    progress_id="",
                    start_time=start_time,
                    last_update=start_time
                )
                
                # Ajouter l'URL à la liste des URLs traitées
                self.processed_items.add(str(text_file))
                
                # Lire le contenu du fichier texte
                await updates_queue.put((str(text_file), "info", "Reading text file"))
                with open(text_file, 'r', encoding='utf-8') as f:
                    recipe_text = f.read()
                
                # Lire et encoder l'image si elle existe
                image_base64 = None
                if image_file and image_file.exists():
                    await updates_queue.put((str(text_file), "info", "Reading image file"))
                    image_base64, mime_type = RecipeApiClient.encode_image(image_file)
                    await updates_queue.put((str(text_file), "info", f"Image encoded as {mime_type}, size: {len(image_base64)} characters"))
                
                # Créer une session avec timeout par défaut
                timeout = aiohttp.ClientTimeout(total=30, sock_connect=10, sock_read=20)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    # Démarrer la génération de la recette
                    await updates_queue.put((str(text_file), "info", "Calling API to start generation"))
                    
                    # Modifier le texte pour inclure une référence à l'image si elle n'est pas incluse dans le API
                    modified_recipe_text = recipe_text
                    if image_base64 and "Image:" not in recipe_text:
                        # Ajouter une ligne mentionnant l'image (aidant certains modèles LLM)
                        modified_recipe_text = f"{recipe_text}\n\nmain recipe mage: {recipe_id}.jpg"
                        await updates_queue.put((str(text_file), "info", "Added image reference to text"))

                    progress_id = await self.api_client.start_text_generation(session, modified_recipe_text, image_base64)
                    await updates_queue.put((str(text_file), "info", f"Got progress ID: {progress_id if progress_id else 'None'}"))
                    recipe_progress.progress_id = progress_id
                    
                    # Si l'URL existe déjà, la marquer comme ignorée
                    if progress_id is None:
                        self.metrics.skip_count += 1
                        stats["skipped"] += 1
                        stats["in_progress"] -= 1
                        await updates_queue.put((str(text_file), "skipped", "Skipped (already exists)"))
                        return
                    
                    # Vérifier la progression jusqu'à la fin
                    recipe_succeeded = await self.check_progress_until_complete(
                        session=session,
                        progress_id=progress_id,
                        item_id=str(text_file),
                        stats=stats,
                        updates_queue=updates_queue
                    )
                    
                    # Log de débogage pour les recettes réussies
                    if recipe_succeeded:
                        await updates_queue.put((str(text_file), "debug", f"Recipe {recipe_id} successfully imported (verified)"))
            
            except Exception as e:
                # Enregistrer l'erreur
                self.metrics.errors.append(
                    RecipeError(
                        url=str(text_file),
                        error=str(e),
                        timestamp=datetime.now()
                    )
                )
                self.metrics.failure_count += 1
                stats["errors"] += 1
                
                # Notifier l'erreur
                await updates_queue.put((str(text_file), "error", f"Error: {str(e)}"))
                
            finally:
                # Décrémenter le compteur de tâches en cours seulement si on n'a pas déjà quitté la fonction
                if stats["in_progress"] > 0:
                    stats["in_progress"] -= 1
                
                # Mettre à jour la durée totale
                duration = datetime.now() - start_time
                self.metrics.total_duration += duration
                
                # Incrémenter le compteur de tâches terminées
                stats["completed"] += 1 