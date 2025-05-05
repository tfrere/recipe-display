from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel


class RecipeError(BaseModel):
    url: str
    error: str
    timestamp: datetime


class GenerationStep(BaseModel):
    step: str
    message: str
    progress: int = 0  # 0-100
    status: str = "pending"  # "pending", "in_progress", "completed", "error"
    details: Optional[str] = None


class RecipeProgress(BaseModel):
    url: str
    status: str  # "pending", "in_progress", "completed", "error"
    progress: float
    current_step: Optional[str] = None
    error: Optional[str] = None
    progress_id: str
    start_time: datetime
    last_update: datetime
    steps: List[GenerationStep] = []


class ImportMetrics(BaseModel):
    success_count: int = 0
    skip_count: int = 0
    failure_count: int = 0
    total_duration: timedelta = timedelta()
    errors: List[RecipeError] = []
    start_time: datetime = datetime.now()
