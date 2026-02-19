"""Processeurs de recettes — URL et Texte.

Unifié : la logique commune (sémaphore, progress polling, retry, stats)
est dans la classe de base. Les sous-classes ne définissent que `_start_generation`.
"""

import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import RecipeError, ImportMetrics
from .api_client import RecipeApiClient, SSEConnectionError

# Nombre max de tentatives par recette
MAX_RETRIES = 2
RETRY_DELAY_S = 5


class RecipeProcessor:
    """Processeur unifié pour URL et texte."""

    def __init__(
        self,
        api_client: RecipeApiClient,
        metrics: ImportMetrics,
        session: aiohttp.ClientSession,
    ):
        self.api_client = api_client
        self.metrics = metrics
        self.session = session
        self.processed_items: set[str] = set()

    # ──────────────────────────────────────────────
    # Public entry points
    # ──────────────────────────────────────────────

    async def process_url(
        self, url: str, stats: dict, queue: asyncio.Queue
    ) -> None:
        """Traite une recette depuis une URL."""
        credentials = self.api_client.get_auth_for_url(url)

        async def start(session: aiohttp.ClientSession) -> str | None:
            return await self.api_client.start_generation(
                session, recipe_type="url", url=url, credentials=credentials
            )

        await self._process(item_id=url, stats=stats, queue=queue, start_fn=start)

    async def process_text(
        self,
        recipe_files: tuple[Path, Path | None],
        stats: dict,
        queue: asyncio.Queue,
    ) -> None:
        """Traite une recette depuis un fichier texte + image optionnelle."""
        text_file, image_file = recipe_files
        item_id = str(text_file)

        # Lire le texte
        with open(text_file, "r", encoding="utf-8") as f:
            recipe_text = f.read()

        # Encoder l'image si présente
        image_b64 = None
        if image_file and image_file.exists():
            image_b64, _ = RecipeApiClient.encode_image(image_file)

        async def start(session: aiohttp.ClientSession) -> str | None:
            return await self.api_client.start_generation(
                session, recipe_type="text", text=recipe_text, image=image_b64
            )

        await self._process(item_id=item_id, stats=stats, queue=queue, start_fn=start)

    # ──────────────────────────────────────────────
    # Core processing pipeline (shared)
    # ──────────────────────────────────────────────

    async def _process(
        self,
        item_id: str,
        stats: dict,
        queue: asyncio.Queue,
        start_fn,
    ) -> None:
        """Pipeline commun : start → poll → stats (concurrence limitée par le worker pool)."""
        stats["in_progress"] += 1
        start_time = datetime.now()
        self.processed_items.add(item_id)
        await queue.put((item_id, "started", "Démarrage…"))

        try:
            await self._process_with_retry(
                item_id, stats, queue, start_fn
            )
        except Exception as e:
            self._record_error(item_id, str(e), stats)
            await queue.put((item_id, "error", f"Erreur: {e}"))
        finally:
            if stats["in_progress"] > 0:
                stats["in_progress"] -= 1
            self.metrics.total_duration += datetime.now() - start_time
            stats["completed"] = stats.get("completed", 0) + 1
            # Micro-pause pour laisser l'event loop se rafraîchir
            await asyncio.sleep(0.01)

    async def _process_with_retry(
        self,
        item_id: str,
        stats: dict,
        queue: asyncio.Queue,
        start_fn,
    ) -> None:
        """Tente l'import avec retry uniquement sur erreur serveur.

        Les timeouts de polling ne déclenchent PAS de retry car le
        subprocess serveur continue probablement de tourner — relancer
        créerait un doublon inutile.
        """
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    await queue.put(
                        (item_id, "info", f"Retry {attempt}/{MAX_RETRIES}…")
                    )
                    await asyncio.sleep(RETRY_DELAY_S * attempt)

                # Lancer la génération
                progress_id = await start_fn(self.session)

                if progress_id is None:
                    # Doublon détecté par HTTP 409
                    self.metrics.skip_count += 1
                    stats["skipped"] += 1
                    await queue.put((item_id, "skipped", "Déjà existante"))
                    return

                # SSE streaming with polling fallback
                try:
                    success = await self._stream_until_done(
                        progress_id, item_id, stats, queue
                    )
                except (SSEConnectionError, aiohttp.ClientError):
                    success = await self._poll_until_done(
                        progress_id, item_id, stats, queue
                    )
                if success:
                    return
                else:
                    last_error = "Échec sans exception"

            except Exception as e:
                last_error = str(e)
                is_stall_timeout = "Bloqué depuis" in str(e)

                if is_stall_timeout:
                    # Timeout de polling → le subprocess tourne encore côté
                    # serveur. Retrier ne ferait que créer un doublon.
                    # On sort directement en erreur sans retry.
                    break

                if attempt == MAX_RETRIES:
                    break

        # Toutes les tentatives échouées
        self._record_error(item_id, last_error or "Unknown", stats)
        await queue.put((item_id, "error", f"Erreur: {last_error}"))

    async def _handle_status(
        self,
        status: dict,
        item_id: str,
        stats: dict,
        queue: asyncio.Queue,
        tracker: dict,
    ) -> bool | None:
        """Handle a single progress status event.

        Returns True if terminal (success/skip), raises on error,
        returns None if still in progress.
        """
        st = status.get("status")

        if st == "completed":
            self.metrics.success_count += 1
            stats["success"] += 1
            slug = status.get("slug", "ok")
            await queue.put((item_id, "success", f"Importée → {slug}"))
            return True

        if st == "error":
            error_msg = status.get("error") or "Unknown"
            if "already exists" in error_msg.lower():
                self.metrics.skip_count += 1
                stats["skipped"] += 1
                await queue.put((item_id, "skipped", "Déjà existante"))
                return True
            raise Exception(error_msg)

        # In progress — detect changes and forward to TUI
        current_step = status.get("current_step", "")
        step_message = status.get("step_message", "")
        fingerprint = f"{current_step}|{step_message}"

        if fingerprint != tracker.get("fingerprint"):
            tracker["fingerprint"] = fingerprint
            tracker["last_progress_time"] = datetime.now()

        if current_step and current_step != tracker.get("last_step"):
            tracker["last_step"] = current_step
            await queue.put((item_id, "step", f"step: {current_step}"))

        if step_message and step_message != tracker.get("last_message"):
            tracker["last_message"] = step_message
            await queue.put((item_id, "progress", step_message))

        return None

    def _check_stall(self, tracker: dict, max_stall_s: int) -> None:
        """Raise if no progress has been made for too long."""
        stall = (datetime.now() - tracker["last_progress_time"]).total_seconds()
        if stall > max_stall_s:
            raise Exception(f"Bloqué depuis {stall:.0f}s sans progression")

    def _new_tracker(self) -> dict:
        """Create a fresh progress tracker dict."""
        return {
            "last_progress_time": datetime.now(),
            "last_step": "",
            "last_message": "",
            "fingerprint": "",
        }

    async def _stream_until_done(
        self,
        progress_id: str,
        item_id: str,
        stats: dict,
        queue: asyncio.Queue,
        max_stall_s: int = 900,
    ) -> bool:
        """Suit la progression via SSE (Server-Sent Events).

        Plus efficace que le polling : le serveur pousse les updates
        sur une seule connexion HTTP au lieu de requêtes répétées.
        """
        tracker = self._new_tracker()

        async for status in self.api_client.stream_progress(self.session, progress_id):
            if status.get("status") == "keepalive":
                self._check_stall(tracker, max_stall_s)
                continue

            result = await self._handle_status(status, item_id, stats, queue, tracker)
            if result is not None:
                return result

        raise Exception("SSE stream ended unexpectedly")

    async def _poll_until_done(
        self,
        progress_id: str,
        item_id: str,
        stats: dict,
        queue: asyncio.Queue,
        max_stall_s: int = 900,
    ) -> bool:
        """Polling de progression jusqu'à complétion.

        Le timeout est réinitialisé dès qu'un changement est détecté
        (step ou message). On ne timeout que si le serveur renvoie
        des réponses identiques pendant > max_stall_s.
        """
        poll_start_time = datetime.now()
        tracker = self._new_tracker()
        consecutive_identical = 0

        while True:
            self._check_stall(tracker, max_stall_s)

            status = await self.api_client.check_progress(self.session, progress_id)

            result = await self._handle_status(status, item_id, stats, queue, tracker)
            if result is not None:
                return result

            # Patience for long-running subprocesses: if the server keeps
            # responding "in_progress" with the same fingerprint, the
            # subprocess is still alive. Reset the stall timer periodically.
            current_fp = f"{status.get('current_step', '')}|{status.get('step_message', '')}"
            if current_fp == tracker.get("_prev_poll_fp"):
                consecutive_identical += 1
                if consecutive_identical % 20 == 0:
                    tracker["last_progress_time"] = datetime.now()
            else:
                consecutive_identical = 0
            tracker["_prev_poll_fp"] = current_fp

            # Adaptive polling: fast at start, spaced out later
            elapsed = (datetime.now() - poll_start_time).total_seconds()
            if elapsed < 30:
                await asyncio.sleep(1)
            elif elapsed < 120:
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(5)

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _record_error(self, item_id: str, error: str, stats: dict) -> None:
        """Enregistre une erreur dans les métriques."""
        self.metrics.failure_count += 1
        stats["errors"] += 1
        self.metrics.errors.append(
            RecipeError(url=item_id, error=error, timestamp=datetime.now())
        )
