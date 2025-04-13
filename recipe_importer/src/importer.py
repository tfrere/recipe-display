import asyncio
import json
import base64
from datetime import datetime
from pathlib import Path
import aiohttp
from urllib.parse import urlparse
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from .models import ImportMetrics, RecipeError, RecipeProgress
from .api_client import RecipeApiClient
from .progress_tracker import ProgressTracker
from .report import ReportGenerator
from .recipe_processors import UrlRecipeProcessor, TextRecipeProcessor


class RecipeImporter:
    """Coordonne l'importation des recettes à partir d'URLs ou de fichiers texte."""
    
    def __init__(
        self,
        concurrent_imports: int = 5,
        api_url: str = "http://localhost:3001",
        auth_presets_file: str = "auth_presets.json",
        console: Console = None
    ):
        self.concurrent_imports = concurrent_imports
        self.api_url = api_url.rstrip('/')  # Enlever le slash à la fin si présent
        self.console = console or Console()
        self.metrics = ImportMetrics()
        self.semaphore = asyncio.Semaphore(concurrent_imports)
        self.processed_urls = set()  # Pour suivre les URLs traitées
        
        # Charger les présets d'authentification
        self.auth_presets = self._load_auth_presets(auth_presets_file)
        
        # Initialiser les composants
        self.api_client = RecipeApiClient(api_url, self.auth_presets, self.console)
        self.progress_tracker = ProgressTracker(self.console)
        self.report_generator = ReportGenerator(self.console)
        
    def _load_auth_presets(self, auth_presets_file: str) -> dict:
        """Charge les configurations d'authentification depuis un fichier JSON."""
        try:
            with open(auth_presets_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.console.print(f"[yellow]Warning: Could not load auth presets: {str(e)}[/yellow]")
            return {}
        
    def _get_auth_for_url(self, url: str) -> dict:
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
        
    async def import_recipes(self, urls: list[str]) -> None:
        """Import multiple recipes concurrently."""
        start_time = datetime.now()
        
        # Créer des compteurs pour suivre la progression
        stats = {
            "total": len(urls),
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "in_progress": 0,
            "waiting": 0,  # Nouveau compteur pour les tâches en attente
            "completed": 0,  # Compteur pour les tâches terminées
            "concurrent_imports": self.concurrent_imports
        }
        
        # Afficher les informations initiales
        self.console.print("\n[bold cyan]Recipe Importer[/bold cyan]")
        self.console.print("[dim]" + "═" * 50 + "[/dim]")
        self.console.print(f"[cyan]Total URLs:[/cyan] [green]{len(urls)}[/green] [cyan]| Max Concurrent Imports:[/cyan] [yellow]{self.concurrent_imports}[/yellow]")
        self.console.print("[dim]" + "═" * 50 + "[/dim]")
        
        # Créer un canal de communication simple
        updates_queue = asyncio.Queue()
        
        # Créer et lancer la tâche d'affichage des statistiques
        stats_task = asyncio.create_task(
            self.progress_tracker.track_progress(stats, start_time, updates_queue)
        )
        
        # Initialiser le processeur de recettes
        url_processor = UrlRecipeProcessor(self.api_client, self.metrics, self.semaphore)
        
        # Créer et lancer les tâches d'importation
        import_tasks = []
        for url in urls:
            import_tasks.append(url_processor.process(url, stats, updates_queue))
            
        # Ajouter les URLs traitées à notre ensemble
        self.processed_urls.update(url_processor.processed_items)
        
        # Attendre que toutes les importations soient terminées
        await asyncio.gather(*import_tasks, return_exceptions=True)
        
        # Arrêter proprement la tâche d'affichage
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass
        
        # Afficher le rapport final
        self.report_generator.show_final_report(self.metrics)

    async def import_text_recipes(self, recipe_files: list[tuple[Path, Path]]) -> None:
        """Import multiple text recipes concurrently."""
        start_time = datetime.now()
        
        # Créer des compteurs pour suivre la progression
        stats = {
            "total": len(recipe_files),
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "in_progress": 0,
            "waiting": 0,  # Nouveau compteur pour les tâches en attente
            "completed": 0,  # Compteur pour les tâches terminées
            "concurrent_imports": self.concurrent_imports
        }
        
        # Afficher les informations initiales
        self.console.print("\n[bold cyan]Recipe Importer - Text Mode[/bold cyan]")
        self.console.print("[dim]" + "═" * 50 + "[/dim]")
        self.console.print(f"[cyan]Total Files:[/cyan] [green]{len(recipe_files)}[/green] [cyan]| Max Concurrent Imports:[/cyan] [yellow]{self.concurrent_imports}[/yellow]")
        self.console.print("[dim]" + "═" * 50 + "[/dim]")
        
        # Créer un canal de communication simple
        updates_queue = asyncio.Queue()
        
        # Créer et lancer la tâche d'affichage des statistiques
        stats_task = asyncio.create_task(
            self.progress_tracker.track_progress(stats, start_time, updates_queue)
        )
        
        # Initialiser le processeur de recettes
        text_processor = TextRecipeProcessor(self.api_client, self.metrics, self.semaphore)
        
        # Créer et lancer les tâches d'importation
        import_tasks = []
        for recipe_file in recipe_files:
            import_tasks.append(text_processor.process(recipe_file, stats, updates_queue))
            
        # Ajouter les URLs traitées à notre ensemble
        self.processed_urls.update(text_processor.processed_items)
        
        # Attendre que toutes les importations soient terminées
        await asyncio.gather(*import_tasks, return_exceptions=True)
        
        # Arrêter proprement la tâche d'affichage
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass
        
        # Afficher le rapport final
        self.report_generator.show_final_report(self.metrics)
    
    async def list_imported_recipes(self, session: aiohttp.ClientSession) -> None:
        """Liste les recettes importées pendant cette session."""
        await self.api_client.list_imported_recipes(session, self.processed_urls)
