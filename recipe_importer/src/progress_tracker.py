"""Affichage live de la progression des imports avec Rich."""

import asyncio
import sys
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table


# ──────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────


def _extract_name(url: str, max_len: int = 30) -> str:
    """Extrait un nom lisible depuis une URL."""
    parts = url.replace("\\", "/").rstrip("/").split("/")
    candidates = [p for p in reversed(parts) if len(p) > 3 and "." not in p]
    raw = candidates[0] if candidates else (parts[-1] if parts else url)
    name = raw.replace("-", " ").replace("_", " ").title()
    return name[:max_len] + "…" if len(name) > max_len else name


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


STEP_PROGRESS = {
    "check_existence": ("Checking", 10),
    "checking existence": ("Checking", 10),
    "scraping": ("Scraping", 30),
    "scrape": ("Scraping", 30),
    "structuring": ("Structuring", 50),
    "structure": ("Structuring", 50),
    "enriching": ("Enriching", 70),
    "enrich": ("Enriching", 70),
    "saving": ("Saving", 90),
    "save": ("Saving", 90),
}


# ──────────────────────────────────────────────────
# Queue drain (shared)
# ──────────────────────────────────────────────────


def _drain_queue(queue: asyncio.Queue, recipes: dict, stats: dict) -> str:
    """Draine la queue. Retourne la dernière erreur ou ''."""
    last_error = ""
    while True:
        try:
            url, status, message = queue.get_nowait()

            if status in ("success", "skipped"):
                recipes.pop(url, None)
            elif status == "error":
                recipes.pop(url, None)
                last_error = f"{_extract_name(url)}: {message}"
            elif status == "waiting":
                pass
            elif status in ("step", "progress", "started"):
                if url not in recipes:
                    recipes[url] = {"name": _extract_name(url), "step": "Starting", "progress": 5}

                if status == "step" and "step:" in message.lower():
                    raw_step = message.split("step:")[-1].strip().lower()
                    for kw, (label, pct) in STEP_PROGRESS.items():
                        if kw in raw_step:
                            recipes[url]["step"] = label
                            recipes[url]["progress"] = pct
                            break
                    else:
                        recipes[url]["step"] = raw_step.title()
                elif status == "progress":
                    for kw, (label, pct) in STEP_PROGRESS.items():
                        if kw in message.lower():
                            recipes[url]["step"] = label
                            recipes[url]["progress"] = pct
                            break

            queue.task_done()
        except asyncio.QueueEmpty:
            break
    return last_error


# ──────────────────────────────────────────────────
# Rich Live display (TTY mode)
# ──────────────────────────────────────────────────


def _build_layout(
    overall_progress: Progress,
    job_progress: Progress,
    stats: dict,
    last_error: str,
) -> Table:
    """Construit le layout combiné Progress + Jobs."""
    # Stats line
    stats_text = (
        f"[green]{stats['success']}[/] done  "
        f"[red]{stats['errors']}[/] err  "
        f"[yellow]{stats['skipped']}[/] skip  "
        f"[cyan]{stats['in_progress']}[/] active"
    )

    grid = Table.grid(expand=True)
    grid.add_row(
        Panel(overall_progress, title="[b]Overall", border_style="green", padding=(1, 2)),
    )
    grid.add_row(
        Panel(
            f"  {stats_text}" + (f"\n  [red]⚠ {last_error[:80]}[/]" if last_error else ""),
            border_style="dim",
        ),
    )
    if job_progress.tasks:
        grid.add_row(
            Panel(job_progress, title="[b]Active Recipes", border_style="cyan", padding=(0, 1)),
        )

    return grid


# ──────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────


class ProgressTracker:
    """Tracker de progression : Rich Live si TTY, sinon fallback console."""

    async def run_app(
        self,
        stats: dict,
        start_time: datetime,
        queue: asyncio.Queue,
        import_tasks: list,
    ) -> None:
        if sys.stdout.isatty():
            await self._run_live(stats, start_time, queue, import_tasks)
        else:
            await self._run_console(stats, start_time, queue, import_tasks)

    # ── Rich Live (TTY) ──

    async def _run_live(
        self,
        stats: dict,
        start_time: datetime,
        queue: asyncio.Queue,
        import_tasks: list,
    ) -> None:
        recipes: dict[str, dict] = {}
        last_error = ""
        job_tasks: dict[str, int] = {}  # url -> task_id in job_progress

        overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        overall_task = overall_progress.add_task(
            f"Importing {stats['total']} recipes ({stats.get('concurrent_imports', 5)} concurrent)",
            total=stats["total"],
        )

        job_progress = Progress(
            TextColumn("  {task.description}"),
            SpinnerColumn(),
            BarColumn(bar_width=20),
            TextColumn("{task.fields[step]:>12}"),
        )

        tasks = [asyncio.create_task(t) for t in import_tasks]

        with Live(
            _build_layout(overall_progress, job_progress, stats, last_error),
            refresh_per_second=4,
        ) as live:
            while not all(t.done() for t in tasks):
                err = _drain_queue(queue, recipes, stats)
                if err:
                    last_error = err

                # Sync overall progress
                completed = stats["success"] + stats["errors"] + stats["skipped"]
                overall_progress.update(overall_task, completed=completed)

                # Sync job progress : add/update/remove recipe tasks
                current_urls = set(recipes.keys())
                tracked_urls = set(job_tasks.keys())

                for url in tracked_urls - current_urls:
                    job_progress.remove_task(job_tasks.pop(url))

                for url in current_urls - tracked_urls:
                    info = recipes[url]
                    tid = job_progress.add_task(info["name"], total=100, completed=info["progress"], step=info["step"])
                    job_tasks[url] = tid

                for url in current_urls & tracked_urls:
                    info = recipes[url]
                    job_progress.update(job_tasks[url], completed=info["progress"], step=info["step"])

                live.update(_build_layout(overall_progress, job_progress, stats, last_error))
                await asyncio.sleep(0.5)

            # Final
            err = _drain_queue(queue, recipes, stats)
            if err:
                last_error = err
            completed = stats["success"] + stats["errors"] + stats["skipped"]
            overall_progress.update(overall_task, completed=completed)
            live.update(_build_layout(overall_progress, job_progress, stats, last_error))
            await asyncio.sleep(0.5)

    # ── Console fallback (non-TTY) ──

    async def _run_console(
        self,
        stats: dict,
        start_time: datetime,
        queue: asyncio.Queue,
        import_tasks: list,
    ) -> None:
        recipes: dict[str, dict] = {}
        last_error = ""
        console = Console()
        last_print_completed = -1

        tasks = [asyncio.create_task(t) for t in import_tasks]

        console.print(
            f"[bold]Importing {stats['total']} recipes "
            f"({stats.get('concurrent_imports', 5)} concurrent)[/]"
        )

        while not all(t.done() for t in tasks):
            err = _drain_queue(queue, recipes, stats)
            if err:
                last_error = err

            completed = stats["success"] + stats["errors"] + stats["skipped"]
            elapsed = int((datetime.now() - start_time).total_seconds())

            if completed != last_print_completed:
                last_print_completed = completed
                active = [r["name"] for r in recipes.values()]
                active_str = ", ".join(active[:3]) + ("…" if len(active) > 3 else "")
                console.print(
                    f"  [{elapsed}s] {completed}/{stats['total']} "
                    f"([green]{stats['success']}[/]✓ [yellow]{stats['skipped']}[/]⏭ [red]{stats['errors']}[/]✗)"
                    + (f" | {active_str}" if active_str else "")
                )

            await asyncio.sleep(1)

        # Final drain
        _drain_queue(queue, recipes, stats)
        completed = stats["success"] + stats["errors"] + stats["skipped"]
        elapsed = int((datetime.now() - start_time).total_seconds())
        console.print(
            f"\n[bold]Done in {_fmt_duration(elapsed)}[/] — "
            f"[green]{stats['success']}[/] done, "
            f"[yellow]{stats['skipped']}[/] skipped, "
            f"[red]{stats['errors']}[/] errors"
        )
