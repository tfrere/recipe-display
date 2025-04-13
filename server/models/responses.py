from typing import List, Optional
from pydantic import BaseModel

class RecipeListItem(BaseModel):
    title: str
    sourceImageUrl: Optional[str]
    description: str
    bookTitle: Optional[str]
    author: Optional[str]
    diets: List[str]
    seasons: List[str]
    recipeType: Optional[str]
    ingredients: List[str]
    totalTime: float
    totalCookingTime: Optional[float] = None
    quick: bool
    difficulty: Optional[str]
    slug: str

class GenerateRecipeResponse(BaseModel):
    progressId: str