from typing import Optional, Callable, List, Awaitable, Dict, Any, Union, Tuple, Set
from ..models.web_content import WebContent
from ..models.recipe import Recipe, LLMRecipe
from ..prompts.structured_recipe import format_structured_recipe_prompt
from ..utils.string_utils import parse_time_to_minutes
from ..utils.error_utils import save_error_to_file
from ..config import load_config
from ..llm.base import LLMProvider
from ..llm.providers.openai import OpenAIProvider
import json
from dataclasses import dataclass
import aiofiles
from pathlib import Path

@dataclass
class TextContent:
    """Simple wrapper for text content."""
    main_content: str
    selected_image_url: str = ""

class RecipeStructurer:
    """Service for generating structured recipes."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.config = load_config()
        self._seasonal_data = None

    async def _load_seasonal_data(self):
        """Load seasonal vegetables and fruits data if not already loaded."""
        if self._seasonal_data is None:
            async with aiofiles.open(Path("data/constants/seasonal_vegetables.json")) as f:
                content = await f.read()
                self._seasonal_data = json.loads(content)

    def _determine_seasons_from_months(self, months: Set[str]) -> List[str]:
        """Convert months to seasons."""
        seasons = set()
        month_to_season = {
            "December": "winter", "January": "winter", "February": "winter",
            "March": "spring", "April": "spring", "May": "spring",
            "June": "summer", "July": "summer", "August": "summer",
            "September": "autumn", "October": "autumn", "November": "autumn"
        }
        
        for month in months:
            if month in month_to_season:
                seasons.add(month_to_season[month])
        
        return list(seasons) if seasons else ["all"]

    async def _determine_seasons(self, recipe_json: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Determine the seasons and peak months based on produce ingredients."""
        await self._load_seasonal_data()
        
        peak_months = set()
        produce_ingredients = []

        # Collect all produce ingredients
        for sub_recipe in recipe_json["subRecipes"]:
            for ingredient in sub_recipe.get("ingredients", []):
                ingredient_ref = next(
                    (ing for ing in recipe_json["ingredients"] if ing["id"] == ingredient.get("ref")),
                    None
                )
                if ingredient_ref and ingredient_ref.get("category") == "produce":
                    produce_ingredients.append(ingredient_ref["name"].lower())

        # Match ingredients with seasonal data
        for produce_type in ["vegetables", "fruits"]:
            for item in self._seasonal_data["produce"][produce_type]:
                item_name = item["name"].lower()
                # Check if any produce ingredient contains or is contained in the seasonal item name
                if any(ing in item_name or item_name in ing for ing in produce_ingredients):
                    peak_months.update(item["peak_months"])

        seasons = self._determine_seasons_from_months(peak_months)
        return seasons, list(peak_months)

    async def generate_structured_recipe(
        self,
        content: Union[WebContent, TextContent],
        source_url: Optional[str],
        image_urls: List[str],
        progress_service: Optional['ProgressService'] = None,
        progress_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a structured recipe from cleaned web content or text content."""
        
        # Détermine le modèle à utiliser selon le provider
        model_key = "openai_models" if isinstance(self.provider, OpenAIProvider) else "anthropic_models"
        
        # Récupère le prompt fixe et construit le prompt complet
        fixed_prompt = format_structured_recipe_prompt("")  # Récupère la partie fixe sans contenu
        prompt = {
            "role": "system",
            "fixed_content": fixed_prompt,  # La partie fixe avec les instructions
            "content": content.main_content,  # Le contenu de la recette
            "model": self.config[model_key]["structure"]  # Utilise le bon modèle selon le provider
        }
        
        # Créer une fonction de callback pour streamer le texte généré
        accumulated_text = ""
        async def stream_callback(text: str) -> None:
            nonlocal accumulated_text
            accumulated_text += text
            if progress_service and progress_id:
                await progress_service.update_step(
                    progress_id=progress_id,
                    step="generate_recipe",
                    status="in_progress",
                    progress=50,  # On garde 50% car il y a encore la validation après
                    details=accumulated_text,
                    message="Generating recipe structure..."
                )
        
        # Générer la recette structurée
        recipe_json = await self.provider.generate_structured(
            model=LLMRecipe,
            prompt=prompt,
            temperature=self.config["temperature"],
            progress_callback=stream_callback if progress_service and progress_id else None
        )
        
        # Mise à jour finale du progress
        if progress_service and progress_id:
            await progress_service.update_step(
                progress_id=progress_id,
                step="generate_recipe",
                status="completed",
                progress=100,
                details=None,
                message="Recipe structure generated"
            )
        
        # Convert Pydantic model to dict
        return recipe_json.model_dump()

    def _determine_diets(self, recipe_json: Dict[str, Any]) -> List[str]:
        """Determine the diets based on recipe ingredients."""
        diets = []
        has_meat_or_seafood = False
        has_dairy = False

        # Check all ingredients in all subrecipes
        for sub_recipe in recipe_json["subRecipes"]:
            for ingredient in sub_recipe.get("ingredients", []):
                ingredient_ref = next(
                    (ing for ing in recipe_json["ingredients"] if ing["id"] == ingredient.get("ref")),
                    None
                )
                if ingredient_ref:
                    category = ingredient_ref.get("category", "")
                    if category in ["meat", "seafood", "egg"]:
                        has_meat_or_seafood = True
                    elif category == "dairy":
                        has_dairy = True

        # Stack the diets based on ingredients
        if has_meat_or_seafood:
            diets = ["omnivorous"]
        elif has_dairy:
            diets = ["vegetarian", "omnivorous"]
        else:
            diets = ["vegan", "vegetarian", "omnivorous"]

        return diets