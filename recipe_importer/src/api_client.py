"""Client HTTP pour l'API de recettes."""

import base64
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse
from rich.console import Console

class RecipeApiClient:
    """Interactions avec l'API de recettes."""

    def __init__(
        self,
        api_url: str,
        auth_presets: dict | None = None,
        console: Console | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.console = console or Console()
        self.auth_presets = auth_presets or {}

    # ──────────────────────────────────────────────
    # Auth helpers
    # ──────────────────────────────────────────────

    def get_auth_for_url(self, url: str) -> dict | None:
        """Récupère les credentials pour une URL."""
        if not self.auth_presets:
            return None
        domain = urlparse(url).netloc
        for preset_domain, preset_config in self.auth_presets.items():
            if preset_domain in domain:
                return preset_config
        return None

    # ──────────────────────────────────────────────
    # Core HTTP helper (redirect-aware)
    # ──────────────────────────────────────────────

    async def _post_json(
        self,
        session: aiohttp.ClientSession,
        payload: dict,
        timeout_s: int = 30,
    ) -> dict:
        """POST JSON vers /api/recipes avec gestion des redirections.

        Returns:
            dict with "progressId" on success.
        Raises:
            DuplicateRecipeError if 409.
            Exception on other failures.
        """
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        url = f"{self.api_url}/api/recipes"

        async with session.post(url, json=payload, timeout=timeout) as resp:
            if resp.status == 409:
                raise DuplicateRecipeError()
            if resp.status in (301, 302, 307, 308):
                redirect_url = resp.headers.get("Location")
                if not redirect_url:
                    raise Exception("Redirect sans header Location")
                async with session.post(
                    redirect_url, json=payload, timeout=timeout
                ) as rr:
                    if rr.status != 200:
                        raise Exception(f"Échec après redirect: {await rr.text()}")
                    return await rr.json()
            if resp.status != 200:
                body = await resp.text()
                raise Exception(f"API {resp.status}: {body}")
            return await resp.json()

    # ──────────────────────────────────────────────
    # Start generation (URL or Text)
    # ──────────────────────────────────────────────

    async def start_generation(
        self,
        session: aiohttp.ClientSession,
        *,
        recipe_type: str,
        url: str | None = None,
        text: str | None = None,
        image: str | None = None,
        credentials: dict | None = None,
    ) -> str | None:
        """Lance la génération et retourne le progressId (None si doublon)."""
        payload = {
            "type": recipe_type,
            "url": url,
            "text": text,
            "image": image,
            "credentials": credentials,
        }
        try:
            data = await self._post_json(session, payload)
            return data["progressId"]
        except DuplicateRecipeError:
            return None

    # ──────────────────────────────────────────────
    # Progress polling
    # ──────────────────────────────────────────────

    async def check_progress(
        self, session: aiohttp.ClientSession, progress_id: str
    ) -> dict:
        """Vérifie la progression d'une génération."""
        if not progress_id:
            return {"status": "completed", "progress": 100}

        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with session.get(
                f"{self.api_url}/api/recipes/progress/{progress_id}",
                timeout=timeout,
            ) as resp:
                if resp.status == 404:
                    raise Exception("Progress introuvable")
                if resp.status != 200:
                    raise Exception(f"Erreur progress: {await resp.text()}")

                data = await resp.json()
                return self._parse_progress(data)

        except asyncio.TimeoutError:
            return {
                "status": "in_progress",
                "progress": 0,
                "current_step": "unknown",
                "step_message": "Timeout (le serveur continue probablement)",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_progress(self, data: dict) -> dict:
        """Parse la réponse brute du serveur en un format simplifié."""
        if data["status"] == "error":
            error_msg = data.get("error") or "Unknown error"
            return {"status": "error", "error": error_msg, "progress": 0}

        if data["status"] == "completed":
            slug = None
            recipe = data.get("recipe")
            if isinstance(recipe, dict):
                slug = recipe.get("metadata", {}).get("slug") or recipe.get("slug")
            return {"status": "completed", "progress": 100, "slug": slug}

        # In progress — calculer la progression moyenne
        steps = data.get("steps", [])
        total_progress = 0
        current_step_info = None

        for step in steps:
            if step["status"] == "completed":
                total_progress += 100
            elif step["status"] == "in_progress":
                total_progress += step.get("progress", 0)
                current_step_info = step

        avg = total_progress / len(steps) if steps else 0

        result = {
            "status": "in_progress",
            "progress": avg,
            "current_step": data.get("currentStep", ""),
        }
        if current_step_info:
            result["step_message"] = current_step_info.get("message", "")
        return result

    # ──────────────────────────────────────────────
    # SSE streaming
    # ──────────────────────────────────────────────

    async def stream_progress(
        self, session: aiohttp.ClientSession, progress_id: str
    ) -> AsyncIterator[dict]:
        """Stream progress updates via SSE. Yields parsed dicts."""
        url = f"{self.api_url}/api/recipes/progress/{progress_id}/stream"
        timeout = aiohttp.ClientTimeout(total=None, sock_read=30)

        async with session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                raise SSEConnectionError(f"SSE endpoint returned {resp.status}")

            buffer = ""
            async for chunk in resp.content.iter_any():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n\n" in buffer:
                    message, buffer = buffer.split("\n\n", 1)
                    for line in message.split("\n"):
                        line = line.strip()
                        if line.startswith("data: "):
                            raw = line[6:]
                            try:
                                data = json.loads(raw)
                                yield self._parse_sse_event(data)
                            except json.JSONDecodeError:
                                continue

    def _parse_sse_event(self, data: dict) -> dict:
        """Parse un event SSE brut en format simplifié (même format que _parse_progress)."""
        if data.get("type") == "keepalive":
            return {"status": "keepalive"}

        if data.get("error") == "not_found":
            return {"status": "error", "error": "Progress introuvable"}

        return self._parse_progress(data)

    # ──────────────────────────────────────────────
    # List recipes
    # ──────────────────────────────────────────────

    async def list_recipes(self, session: aiohttp.ClientSession) -> list[dict]:
        """Récupère toutes les recettes depuis l'API."""
        try:
            async with session.get(f"{self.api_url}/api/recipes") as resp:
                if resp.status != 200:
                    self.console.print(f"[yellow]Warning: API returned status {resp.status} when listing recipes[/yellow]")
                    return []
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as e:
            self.console.print(f"[yellow]Warning: Could not list recipes: {e}[/yellow]")
            return []

    # ──────────────────────────────────────────────
    # Image encoding
    # ──────────────────────────────────────────────

    @staticmethod
    def encode_image(image_file: Path) -> tuple[str | None, str]:
        """Encode une image en base64 data URI."""
        if not image_file or not image_file.exists():
            return None, ""

        mime_map = {".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(image_file.suffix.lower(), "image/jpeg")

        with open(image_file, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return f"data:{mime_type};base64,{b64}", mime_type


class DuplicateRecipeError(Exception):
    """La recette existe déjà (HTTP 409)."""
    pass


class SSEConnectionError(Exception):
    """Impossible de se connecter au flux SSE."""
    pass
