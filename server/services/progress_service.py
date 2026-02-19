import asyncio
import logging
from datetime import datetime
from typing import Dict, Literal, Optional

from models.progress import GenerationProgress, GenerationStep

logger = logging.getLogger(__name__)

URL_STEPS = [
    GenerationStep(step="check_existence", message="Checking if recipe already exists", startedAt=None),
    GenerationStep(step="scrape_content", message="Fetching recipe content", startedAt=None),
    GenerationStep(step="structure_recipe", message="Structuring recipe data", startedAt=None),
    GenerationStep(step="save_recipe", message="Saving recipe", startedAt=None),
]

TEXT_IMAGE_STEPS = [
    GenerationStep(step="check_existence", message="Checking if recipe already exists", startedAt=None),
    GenerationStep(step="generate_recipe", message="Preparing recipe text", startedAt=None),
    GenerationStep(step="structure_recipe", message="Structuring recipe data", startedAt=None),
    GenerationStep(step="save_recipe", message="Saving recipe and image", startedAt=None),
]

IMAGE_OCR_STEPS = [
    GenerationStep(step="ocr_extract", message="Extracting text from image (OCR)", startedAt=None),
    GenerationStep(step="structure_recipe", message="Structuring recipe data", startedAt=None),
    GenerationStep(step="save_recipe", message="Saving recipe", startedAt=None),
]


_CLEANUP_AFTER_S = 300  # Remove terminal entries 5 min after last update


class ProgressService:
    def __init__(self):
        self._progress_entries: Dict[str, Dict] = {}
        self._subscribers: Dict[str, list[asyncio.Queue]] = {}

    def _cleanup_stale(self) -> None:
        """Remove progress entries that reached a terminal state (completed/error)
        more than ``_CLEANUP_AFTER_S`` seconds ago."""
        now = datetime.now().astimezone()
        to_remove = []
        for pid, entry in self._progress_entries.items():
            if entry["status"] not in ("completed", "error"):
                continue
            if pid in self._subscribers and self._subscribers[pid]:
                continue  # still has active SSE listeners
            try:
                updated = datetime.fromisoformat(entry["updatedAt"])
                if (now - updated).total_seconds() > _CLEANUP_AFTER_S:
                    to_remove.append(pid)
            except (KeyError, ValueError):
                to_remove.append(pid)
        for pid in to_remove:
            self._progress_entries.pop(pid, None)
            self._subscribers.pop(pid, None)
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} stale progress entries")

    def subscribe(self, progress_id: str) -> asyncio.Queue:
        """Create and register a subscriber queue for SSE streaming."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(progress_id, []).append(queue)
        return queue

    def unsubscribe(self, progress_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        queues = self._subscribers.get(progress_id, [])
        try:
            queues.remove(queue)
        except ValueError:
            pass
        if not queues:
            self._subscribers.pop(progress_id, None)

    async def _notify(self, progress_id: str) -> None:
        """Push a progress snapshot to all SSE subscribers."""
        queues = self._subscribers.get(progress_id, [])
        if not queues:
            return
        progress = await self.get_progress(progress_id)
        if progress:
            data = progress.model_dump_json(by_alias=True)
            for q in queues:
                q.put_nowait(data)

    async def register(self, progress_id: str, import_type: Literal["url", "text", "image"] = "url") -> None:
        """Register a new progress entry with a given ID."""
        self._cleanup_stale()

        if import_type == "url":
            steps = URL_STEPS
        elif import_type == "image":
            steps = IMAGE_OCR_STEPS
        else:
            steps = TEXT_IMAGE_STEPS

        self._progress_entries[progress_id] = {
            "id": progress_id,
            "steps": [step.model_dump() for step in steps],
            "status": "pending",
            "error": None,
            "recipe": None,
            "currentStep": None,
            "createdAt": datetime.now().astimezone().isoformat(),
            "updatedAt": datetime.now().astimezone().isoformat(),
        }

    async def complete(self, progress_id: str, data: Dict = None) -> None:
        """Mark a progress entry as completed."""
        if progress_id not in self._progress_entries:
            return

        entry = self._progress_entries[progress_id]
        entry["status"] = "completed"
        entry["updatedAt"] = datetime.now().astimezone().isoformat()

        if data and "slug" in data:
            entry["recipe"] = {"metadata": {"slug": data["slug"]}}
            entry["result"] = data
            logger.info(f"Progress {progress_id} completed with slug: {data['slug']}")

        await self._notify(progress_id)

    async def update_step(
        self,
        progress_id: str,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Update a step in the progress entry."""
        if progress_id not in self._progress_entries:
            return

        entry = self._progress_entries[progress_id]

        # If starting a new step, mark the previous step as completed
        if status == "in_progress":
            current_step = entry.get("currentStep")
            if current_step and current_step != step:
                prev_step = next(
                    (s for s in entry["steps"] if s["step"] == current_step),
                    None,
                )
                if prev_step and prev_step["status"] != "completed":
                    prev_step["status"] = "completed"
                    prev_step["progress"] = 100

        step_entry = next(
            (s for s in entry["steps"] if s["step"] == step),
            None,
        )

        if step_entry:
            if status == "in_progress" and progress == 0:
                if not step_entry.get("startedAt"):
                    step_entry["startedAt"] = datetime.now().astimezone().isoformat()

            step_entry["status"] = status
            step_entry["progress"] = progress
            if message:
                step_entry["message"] = message
            if details:
                step_entry["details"] = details

            if status == "in_progress":
                entry["currentStep"] = step
            entry["updatedAt"] = datetime.now().astimezone().isoformat()

            if status == "error":
                entry["status"] = "error"
                # Propagate step message to top-level error so SSE clients
                # get the error detail in the first notification.
                if message and not entry.get("error"):
                    entry["error"] = message
            elif all(s["status"] == "completed" for s in entry["steps"]):
                entry["status"] = "completed"
            else:
                entry["status"] = "in_progress"

        await self._notify(progress_id)

    async def get_progress(self, progress_id: str) -> Optional[GenerationProgress]:
        """Get a progress entry by ID."""
        if progress_id not in self._progress_entries:
            return None

        entry = self._progress_entries[progress_id]

        try:
            created_at = datetime.fromisoformat(entry["createdAt"])
            updated_at = datetime.fromisoformat(entry["updatedAt"])

            return GenerationProgress(
                id=entry["id"],
                status=entry["status"],
                error=entry["error"],
                recipe=entry["recipe"],
                currentStep=entry["currentStep"],
                createdAt=created_at,
                updatedAt=updated_at,
                steps=[GenerationStep(**step) for step in entry["steps"]],
            )
        except Exception as e:
            logger.error(f"Error getting progress {progress_id}: {e}")
            return None

    async def set_error(self, progress_id: str, error: str) -> None:
        """Set an error for a progress entry."""
        if progress_id in self._progress_entries:
            entry = self._progress_entries[progress_id]
            entry["error"] = error
            entry["status"] = "error"
            entry["updatedAt"] = datetime.now().astimezone().isoformat()
            await self._notify(progress_id)
