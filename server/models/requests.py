from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class GenerateRecipeRequest(BaseModel):
    type: Literal["url", "text", "image"]
    url: Optional[str] = None
    text: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded image
    credentials: Optional[Dict[str, Any]] = None


class ManualIngredient(BaseModel):
    """An ingredient for a manually created recipe."""
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: str = "other"
    preparation: Optional[str] = None
    optional: bool = False


class ManualStep(BaseModel):
    """A preparation step for a manually created recipe."""
    action: str
    stepType: str = "prep"
    duration: Optional[str] = None  # ISO 8601 duration, e.g. "PT10M"
    temperature: Optional[int] = None


class ManualRecipeRequest(BaseModel):
    """Request body for creating a recipe manually."""
    title: str
    description: str = ""
    servings: int = Field(default=4, ge=1, le=50)
    prepTime: Optional[str] = None  # ISO 8601 duration
    cookTime: Optional[str] = None  # ISO 8601 duration
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    recipeType: Literal[
        "appetizer", "starter", "main_course", "dessert", "drink", "base"
    ] = "main_course"
    ingredients: List[ManualIngredient] = Field(min_length=1)
    steps: List[ManualStep] = Field(min_length=1)
    tags: List[str] = []
    notes: List[str] = []
    author: Optional[str] = None
    source: Optional[str] = None
    nationality: Optional[str] = None