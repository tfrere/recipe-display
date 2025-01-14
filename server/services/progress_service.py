from datetime import datetime
import uuid
from typing import Dict, Optional, List, Literal
from models.progress import GenerationProgress, GenerationStep
import asyncio

URL_STEPS = [
    GenerationStep(
        step="cleanup_content",
        message="Cleaning up content"
    ),
    GenerationStep(
        step="generate_recipe",
        message="Generating recipe"
    ),
    GenerationStep(
        step="save_recipe",
        message="Saving recipe"
    )
]

TEXT_IMAGE_STEPS = [
    GenerationStep(
        step="cleanup_content",
        message="Cleaning up content"
    ),
    GenerationStep(
        step="generate_recipe",
        message="Generating recipe"
    ),
    GenerationStep(
        step="save_recipe",
        message="Saving recipe"
    )
]

class ProgressService:
    def __init__(self):
        self._progress_entries: Dict[str, Dict] = {}

    async def create_progress(self, import_type: Literal["url", "text"] = "url") -> str:
        """Create a new progress entry with appropriate steps based on import type."""
        progress_id = str(uuid.uuid4())
        steps = URL_STEPS if import_type == "url" else TEXT_IMAGE_STEPS
        
        self._progress_entries[progress_id] = {
            "id": progress_id,
            "steps": [step.model_dump() for step in steps],
            "status": "pending",
            "error": None,
            "recipe": None,
            "currentStep": None,
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat()
        }
        
        return progress_id

    async def update_step(
        self,
        progress_id: str,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """Update a step in the progress entry."""
        if progress_id not in self._progress_entries:
            return
            
        entry = self._progress_entries[progress_id]
        step_entry = next(
            (s for s in entry["steps"] if s["step"] == step),
            None
        )
        
        if step_entry:
            # Add artificial delay for better visualization
            if status == "in_progress" and progress == 0:
                await asyncio.sleep(0.5)  # 500ms delay when starting a step
            elif status == "completed":
                await asyncio.sleep(0.2)  # 200ms delay when completing a step
            
            step_entry["status"] = status
            step_entry["progress"] = progress
            if message:
                step_entry["message"] = message
            if details:
                step_entry["details"] = details
            
            # Update current step and timestamp
            entry["currentStep"] = step
            entry["updatedAt"] = datetime.now().isoformat()
            
            # Update global status
            if status == "error":
                entry["status"] = "error"
            elif all(s["status"] == "completed" for s in entry["steps"]):
                entry["status"] = "completed"
            else:
                entry["status"] = "in_progress"

    async def get_progress(self, progress_id: str) -> Optional[GenerationProgress]:
        """Get a progress entry by ID."""
        if progress_id not in self._progress_entries:
            return None
            
        entry = self._progress_entries[progress_id]
        
        try:
            # Convert ISO strings to datetime
            created_at = datetime.fromisoformat(entry["createdAt"])
            updated_at = datetime.fromisoformat(entry["updatedAt"])
            
            # Create GenerationProgress object
            progress = GenerationProgress(
                id=entry["id"],
                status=entry["status"],
                error=entry["error"],
                recipe=entry["recipe"],
                currentStep=entry["currentStep"],
                createdAt=created_at,
                updatedAt=updated_at,
                steps=[GenerationStep(**step) for step in entry["steps"]]
            )
            
            return progress
        except Exception as e:
            print(f"[ERROR] Error getting progress: {str(e)}")
            return None

    async def set_error(self, progress_id: str, error: str) -> None:
        """Set an error for a progress entry."""
        if progress_id in self._progress_entries:
            entry = self._progress_entries[progress_id]
            entry["error"] = error
            entry["status"] = "error"
            entry["updatedAt"] = datetime.now().isoformat()

    async def set_recipe(self, progress_id: str, recipe: Dict) -> None:
        """Set the generated recipe for a progress entry."""
        if progress_id in self._progress_entries:
            self._progress_entries[progress_id]["recipe"] = recipe
            self._progress_entries[progress_id]["updatedAt"] = datetime.now().isoformat()

    def remove_progress(self, progress_id: str) -> None:
        """Remove a progress entry."""
        self._progress_entries.pop(progress_id, None)