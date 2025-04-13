from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

class GenerationStep(BaseModel):
    step: str
    message: str
    progress: int = Field(default=0, ge=0, le=100)  # 0-100
    status: str = Field(default="pending")  # "pending", "in_progress", "completed", "error"
    details: Optional[str] = None
    startedAt: Optional[datetime] = Field(default=None, alias="startedAt", serialization_alias="startedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        json_schema_extra={
            "example": {
                "step": "fetch_url",
                "message": "Fetching recipe URL",
                "progress": 50,
                "status": "in_progress",
                "details": "Some details...",
                "startedAt": "2024-01-01T00:00:00"
            }
        }
    )

class GenerationProgress(BaseModel):
    id: str
    steps: List[GenerationStep]
    status: str  # "pending", "in_progress", "completed", "error"
    error: Optional[str] = None
    recipe: Optional[Any] = None
    current_step: Optional[str] = Field(default=None, alias="currentStep", serialization_alias="currentStep")
    created_at: datetime = Field(alias="createdAt", serialization_alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt", serialization_alias="updatedAt")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123",
                "steps": [],
                "status": "pending",
                "error": None,
                "recipe": None,
                "currentStep": None,
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": "2024-01-01T00:00:00"
            }
        }
    )