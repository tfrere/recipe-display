from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class IngredientListItem(BaseModel):
    name: str = ""
    name_en: str = ""


class RecipeListItem(BaseModel):
    title: str
    sourceImageUrl: Optional[str] = None
    description: str = ""
    bookTitle: Optional[str] = None
    author: Optional[str] = None
    diets: List[str] = []
    seasons: List[str] = []
    peakMonths: List[str] = []
    recipeType: Optional[str] = None
    ingredients: List[IngredientListItem] = []
    totalTime: Optional[str] = None  # ISO 8601 from DAG (e.g. "PT30M")
    totalTimeMinutes: float = 0.0   # Convenience float
    totalActiveTime: Optional[str] = None
    totalActiveTimeMinutes: float = 0.0
    totalPassiveTime: Optional[str] = None
    totalPassiveTimeMinutes: float = 0.0
    totalCookingTime: Optional[float] = None  # Legacy
    quick: bool = False
    difficulty: Optional[str] = None
    slug: str
    nutritionTags: Optional[List[str]] = None
    nutritionPerServing: Optional[Dict[str, Any]] = None

class GenerateRecipeResponse(BaseModel):
    progressId: str


class ManualRecipeResponse(BaseModel):
    slug: str