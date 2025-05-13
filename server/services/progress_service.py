from datetime import datetime
import uuid
from typing import Dict, Optional, List, Literal
from models.progress import GenerationProgress, GenerationStep
import asyncio
import logging

URL_STEPS = [
    GenerationStep(
        step="check_existence",
        message="Checking if recipe already exists",
        startedAt=None
    ),
    GenerationStep(
        step="scrape_content",
        message="Fetching recipe content",
        startedAt=None
    ),
    GenerationStep(
        step="structure_recipe",
        message="Structuring recipe data",
        startedAt=None
    ),
    GenerationStep(
        step="save_recipe",
        message="Saving recipe",
        startedAt=None
    )
]

TEXT_IMAGE_STEPS = [
    GenerationStep(
        step="check_existence",
        message="Checking if recipe already exists",
        startedAt=None
    ),
    GenerationStep(
        step="generate_recipe",
        message="Preparing recipe text",
        startedAt=None
    ),
    GenerationStep(
        step="structure_recipe",
        message="Structuring recipe data",
        startedAt=None
    ),
    GenerationStep(
        step="save_recipe",
        message="Saving recipe and image",
        startedAt=None
    )
]

class ProgressService:
    def __init__(self):
        self._progress_entries: Dict[str, Dict] = {}

    async def register(self, progress_id: str, import_type: Literal["url", "text"] = "url") -> None:
        """Register a new progress entry with a given ID."""
        steps = URL_STEPS if import_type == "url" else TEXT_IMAGE_STEPS
        
        self._progress_entries[progress_id] = {
            "id": progress_id,
            "steps": [step.model_dump() for step in steps],
            "status": "pending",
            "error": None,
            "recipe": None,
            "currentStep": None,
            "createdAt": datetime.now().astimezone().isoformat(),
            "updatedAt": datetime.now().astimezone().isoformat()
        }

    async def update_progress(self, progress_id: str, message: str) -> None:
        """Update progress with a simple message."""
        if progress_id not in self._progress_entries:
            return
            
        entry = self._progress_entries[progress_id]
        entry["progressMessage"] = message
        entry["updatedAt"] = datetime.now().astimezone().isoformat()

    async def complete(self, progress_id: str, data: Dict = None) -> None:
        """Mark a progress entry as completed."""
        if progress_id not in self._progress_entries:
            return
            
        entry = self._progress_entries[progress_id]
        entry["status"] = "completed"
        entry["updatedAt"] = datetime.now().astimezone().isoformat()
        
        print(f"[DEBUG] Marking progress {progress_id} as completed with data: {data}")
        
        if data and "slug" in data:
            # Format properly to match what the client expects
            entry["recipe"] = {
                "metadata": {
                    "slug": data["slug"]
                }
            }
            # Conserver aussi les données d'origine au cas où
            entry["result"] = data
            
            print(f"[DEBUG] Set recipe slug in progress: {data['slug']}")
            print(f"[DEBUG] Updated progress entry: {entry}")

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
            "createdAt": datetime.now().astimezone().isoformat(),
            "updatedAt": datetime.now().astimezone().isoformat()
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
        
        # If we're starting a new step, mark the previous step as completed
        if status == "in_progress":
            current_step = entry.get("currentStep")
            if current_step and current_step != step:
                prev_step = next(
                    (s for s in entry["steps"] if s["step"] == current_step),
                    None
                )
                if prev_step and prev_step["status"] != "completed":
                    prev_step["status"] = "completed"
                    prev_step["progress"] = 100
        
        step_entry = next(
            (s for s in entry["steps"] if s["step"] == step),
            None
        )
        
        if step_entry:
            # Add artificial delay for better visualization
            if status == "in_progress" and progress == 0:
                await asyncio.sleep(0.5)  # 500ms delay when starting a step
                # Initialize startedAt when the step begins
                if not step_entry.get("startedAt"):
                    step_entry["startedAt"] = datetime.now().astimezone().isoformat()
            elif status == "completed":
                await asyncio.sleep(0.2)  # 200ms delay when completing a step
            
            step_entry["status"] = status
            step_entry["progress"] = progress
            if message:
                step_entry["message"] = message
            if details:
                step_entry["details"] = details
            
            # Update current step and timestamp
            if status == "in_progress":
                entry["currentStep"] = step
            entry["updatedAt"] = datetime.now().astimezone().isoformat()
            
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
            entry["updatedAt"] = datetime.now().astimezone().isoformat()

    async def set_recipe(self, progress_id: str, recipe: Dict) -> None:
        """Set the generated recipe for a progress entry."""
        if progress_id in self._progress_entries:
            self._progress_entries[progress_id]["recipe"] = recipe
            self._progress_entries[progress_id]["updatedAt"] = datetime.now().astimezone().isoformat()

    def remove_progress(self, progress_id: str) -> None:
        """Remove a progress entry."""
        self._progress_entries.pop(progress_id, None)