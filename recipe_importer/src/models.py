from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel


class RecipeError(BaseModel):
    url: str
    error: str
    timestamp: datetime


class ImportMetrics(BaseModel):
    success_count: int = 0
    skip_count: int = 0
    failure_count: int = 0
    total_duration: timedelta = timedelta()
    errors: List[RecipeError] = []
    start_time: datetime = datetime.now()
