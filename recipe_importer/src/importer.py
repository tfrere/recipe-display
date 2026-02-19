"""Coordonnateur d'import de recettes."""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from rich.console import Console

from .models import ImportMetrics
from .api_client import RecipeApiClient
from .progress_tracker import ProgressTracker
from .report import ReportGenerator
from .recipe_processors import RecipeProcessor


class RecipeImporter:
    """Coordonne l'importation de recettes (URL ou texte) en parallèle."""

    def __init__(
        self,
        concurrent_imports: int = 5,
        api_url: str = "http://localhost:3001",
        auth_presets_file: str = "auth_presets.json",
        console: Console | None = None,
        headless: bool = False,
        max_per_domain: int = 8,
    ):
        self.concurrent_imports = concurrent_imports
        self.max_per_domain = max_per_domain
        self.api_url = api_url.rstrip("/")
        self.console = console or Console()
        self.headless = headless
        self.metrics = ImportMetrics()

        # Auth presets
        self.auth_presets = self._load_auth_presets(auth_presets_file)

        # Components
        self.api_client = RecipeApiClient(api_url, self.auth_presets, self.console)
        self.progress_tracker = ProgressTracker()
        self.report_generator = ReportGenerator(self.console)

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    async def import_urls(self, urls: list[str]) -> None:
        """Importe des recettes depuis une liste d'URLs.

        Les URLs sont mélangées pour répartir la charge entre les domaines.
        Un sémaphore par domaine limite la concurrence (max_per_domain)
        afin d'éviter les 429 Too Many Requests.
        """
        # Shuffle pour répartir les domaines uniformément
        shuffled = list(urls)
        random.shuffle(shuffled)

        stats = self._make_stats(len(shuffled))
        queue: asyncio.Queue = asyncio.Queue()
        session = aiohttp.ClientSession()

        # Sémaphore par domaine : max N requêtes simultanées par site
        max_per_domain = min(self.max_per_domain, self.concurrent_imports)
        domain_semaphores: dict[str, asyncio.Semaphore] = {}

        def get_domain_semaphore(url: str) -> asyncio.Semaphore:
            domain = urlparse(url).netloc
            if domain not in domain_semaphores:
                domain_semaphores[domain] = asyncio.Semaphore(max_per_domain)
            return domain_semaphores[domain]

        processor = RecipeProcessor(
            self.api_client, self.metrics, session
        )

        work_queue: asyncio.Queue = asyncio.Queue()
        for url in shuffled:
            await work_queue.put(url)

        async def worker():
            while not work_queue.empty():
                try:
                    url = work_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                async with get_domain_semaphore(url):
                    await processor.process_url(url, stats, queue)

        async def _run_all():
            try:
                workers = [
                    asyncio.create_task(worker())
                    for _ in range(self.concurrent_imports)
                ]
                await asyncio.gather(*workers, return_exceptions=True)
            finally:
                await session.close()

        await self._run_with_tracking(_run_all(), stats, queue)

    async def import_text_recipes(
        self, recipe_files: list[tuple[Path, Path | None]]
    ) -> None:
        """Importe des recettes depuis des fichiers texte."""
        stats = self._make_stats(len(recipe_files))
        queue: asyncio.Queue = asyncio.Queue()
        session = aiohttp.ClientSession()

        processor = RecipeProcessor(
            self.api_client, self.metrics, session
        )

        work_queue: asyncio.Queue = asyncio.Queue()
        for rf in recipe_files:
            await work_queue.put(rf)

        async def worker():
            while not work_queue.empty():
                try:
                    rf = work_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                await processor.process_text(rf, stats, queue)

        async def _run_all():
            try:
                workers = [
                    asyncio.create_task(worker())
                    for _ in range(self.concurrent_imports)
                ]
                await asyncio.gather(*workers, return_exceptions=True)
            finally:
                await session.close()

        await self._run_with_tracking(_run_all(), stats, queue)

    async def list_imported_recipes(self) -> None:
        """Liste toutes les recettes importées sur le serveur."""
        async with aiohttp.ClientSession() as session:
            recipes = await self.api_client.list_recipes(session)
            if not recipes:
                self.console.print("[yellow]Aucune recette trouvée[/yellow]")
                return

            self.console.print(f"\n[green]Recettes sur le serveur ({len(recipes)}):[/green]")
            for r in recipes:
                title = r.get("title", r.get("metadata", {}).get("title", "?"))
                slug = r.get("slug", "?")
                self.console.print(f"  [green]•[/green] {title} [dim]({slug})[/dim]")

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    async def _run_with_tracking(
        self,
        import_coro,
        stats: dict,
        queue: asyncio.Queue,
    ) -> None:
        """Lance le TUI ou le mode console selon la config."""
        start_time = datetime.now()

        if self.headless:
            # Mode console simple — pas de TUI, juste les logs
            async def _drain_and_log():
                while True:
                    try:
                        url, status, message = queue.get_nowait()
                        if status in ("success", "error", "skipped"):
                            completed = stats["success"] + stats["errors"] + stats["skipped"]
                            elapsed = int((datetime.now() - start_time).total_seconds())
                            self.console.print(
                                f"  [{elapsed}s] {status:>7} ({completed}/{stats['total']}) {message}"
                            )
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        break

            import_task = asyncio.create_task(import_coro)
            while not import_task.done():
                await asyncio.sleep(2)
                await _drain_and_log()
            await _drain_and_log()
        else:
            await self.progress_tracker.run_app(
                stats=stats,
                start_time=start_time,
                queue=queue,
                import_tasks=[import_coro],
            )

        self.report_generator.show_final_report(self.metrics)

    def _make_stats(self, total: int) -> dict:
        """Crée le dict de stats partagé."""
        return {
            "total": total,
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "in_progress": 0,
            "completed": 0,
            "concurrent_imports": self.concurrent_imports,
        }

    def _load_auth_presets(self, path: str) -> dict:
        """Charge les presets d'auth depuis un fichier JSON."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
