import asyncio
from datetime import datetime
from pathlib import Path
import aiohttp
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from models import ImportMetrics, RecipeError, RecipeProgress


class RecipeImporter:
    def __init__(
        self,
        concurrent_imports: int = 5,
        console: Console = None
    ):
        self.concurrent_imports = concurrent_imports
        self.console = console or Console()
        self.metrics = ImportMetrics()
        self.semaphore = asyncio.Semaphore(concurrent_imports)
        
    async def import_recipes(self, urls: list[str]) -> None:
        """Import multiple recipes concurrently."""
        with Progress() as progress:
            overall_task = progress.add_task(
                "[yellow]Importing recipes...", 
                total=len(urls)
            )
            
            tasks = []
            for url in urls:
                task = progress.add_task(
                    f"[cyan]Importing {url}...",
                    total=100,
                    visible=False
                )
                tasks.append(self._import_recipe(url, progress, task))
            
            # Import recipes concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update overall progress and handle results
            for result in results:
                if isinstance(result, Exception):
                    self.metrics.failure_count += 1
                progress.advance(overall_task)
            
            self._show_final_report()
            
    async def _import_recipe(
        self, 
        url: str, 
        progress: Progress, 
        task_id: TaskID
    ) -> None:
        """Import a single recipe with progress tracking."""
        async with self.semaphore:
            progress.update(task_id, visible=True)
            start_time = datetime.now()
            
            try:
                # Initialize recipe progress
                recipe_progress = RecipeProgress(
                    url=url,
                    status="pending",
                    progress=0,
                    current_step="initializing",
                    progress_id="",
                    start_time=start_time,
                    last_update=start_time
                )
                
                async with aiohttp.ClientSession() as session:
                    # Start recipe generation
                    progress_id = await self._start_generation(session, url)
                    recipe_progress.progress_id = progress_id
                    
                    # Poll progress until complete
                    while True:
                        status = await self._check_progress(session, progress_id)
                        if status.get("status") == "completed":
                            recipe_progress.status = "success"
                            recipe_progress.progress = 100
                            self.metrics.success_count += 1
                            break
                        elif status.get("status") == "error":
                            raise Exception(status.get("error", "Unknown error"))
                            
                        # Update progress
                        current_progress = status.get("progress", 0)
                        progress.update(task_id, completed=current_progress)
                        await asyncio.sleep(1)
                        
            except Exception as e:
                self.metrics.errors.append(
                    RecipeError(
                        url=url,
                        error=str(e),
                        timestamp=datetime.now()
                    )
                )
                progress.update(
                    task_id, 
                    description=f"[red]Error importing {url}: {str(e)}"
                )
                raise
                
            finally:
                duration = datetime.now() - start_time
                self.metrics.total_duration += duration
                progress.update(task_id, visible=False)
                
    async def _start_generation(
        self, 
        session: aiohttp.ClientSession, 
        url: str
    ) -> str:
        """Start recipe generation and return progress ID."""
        async with session.post(
            "http://localhost:3001/api/recipes",
            json={"url": url, "credentials": None, "type": "url"}
        ) as response:
            if response.status == 409:
                self.metrics.skip_count += 1
                return None
            if response.status != 200:
                raise Exception(f"Failed to start generation: {await response.text()}")
            data = await response.json()
            return data["progressId"]
            
    async def _check_progress(
        self, 
        session: aiohttp.ClientSession, 
        progress_id: str
    ) -> dict:
        """Check recipe generation progress."""
        if not progress_id:
            return {"status": "completed", "progress": 100}
            
        async with session.get(
            f"http://localhost:3001/api/recipes/progress/{progress_id}"
        ) as response:
            if response.status == 404:
                raise Exception("Progress not found")
            if response.status != 200:
                raise Exception(f"Failed to check progress: {await response.text()}")
                
            data = await response.json()
            
            # Map server status to importer status
            if data["status"] == "error":
                return {
                    "status": "error",
                    "error": data["error"] or "Unknown error",
                    "progress": 0
                }
            elif data["status"] == "completed":
                return {
                    "status": "completed",
                    "progress": 100
                }
            else:
                # Calculate overall progress based on steps
                total_progress = 0
                completed_steps = 0
                for step in data["steps"]:
                    if step["status"] == "completed":
                        completed_steps += 1
                    total_progress += step["progress"]
                
                avg_progress = total_progress / len(data["steps"])
                return {
                    "status": "in_progress",
                    "progress": avg_progress,
                    "current_step": data.get("currentStep", "")
                }
            
    def _show_final_report(self) -> None:
        """Display final import report."""
        table = Table(title="Import Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Successful Imports", str(self.metrics.success_count))
        table.add_row("Failed Imports", str(self.metrics.failure_count))
        table.add_row("Skipped Imports", str(self.metrics.skip_count))
        table.add_row(
            "Total Duration", 
            str(self.metrics.total_duration).split(".")[0]
        )
        
        self.console.print("\n")
        self.console.print(table)
        
        if self.metrics.errors:
            self.console.print("\n[red]Errors:[/red]")
            for error in self.metrics.errors:
                self.console.print(
                    f"[red]- {error.url}: {error.error} "
                    f"({error.timestamp.strftime('%H:%M:%S')})[/red]"
                )
