from typing import Optional, Callable, List, Awaitable, Dict, Any, Union, Tuple, Set
from openai import AsyncOpenAI
from ..models.web_content import WebContent
from ..models.recipe import Recipe, OpenAIRecipe
from ..prompts.structured_recipe import format_structured_recipe_prompt
from ..utils.string_utils import parse_time_to_minutes
from ..utils.error_utils import save_error_to_file
from ..config import load_config
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
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
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

    async def _stream_completion(
        self,
        messages: list,
        on_content: Optional[Callable[[str, int], Awaitable[None]]] = None
    ) -> str:
        """Stream completion from OpenAI API with structured output."""
        
        try:
            print("\n[DEBUG] Starting stream completion")
            async with self.client.beta.chat.completions.stream(
                model=self.config["structure_model"],
                messages=messages,
                temperature=self.config["temperature"],
                response_format=OpenAIRecipe
            ) as stream:
                print("[DEBUG] Stream created")
                async for event in stream:
                    print(f"[DEBUG] Event type: {event.type}")
                    if event.type == "content.delta":
                        print("[DEBUG] Content delta received")
                        if event.parsed is not None and on_content:
                            print(f"[DEBUG] Parsed content: {event.parsed}")
                            await on_content(json.dumps(event.parsed), 50)
                    elif event.type == "content.done":
                        print("[DEBUG] Content done received")
                        final_completion = await stream.get_final_completion()
                        print("[DEBUG] Final completion received")
                        final_dict = final_completion.model_dump()
                        print("[DEBUG] Final dict created")
                        recipe_data = final_dict['choices'][0]['message']['parsed']
                        if on_content:
                            await on_content(json.dumps(recipe_data), 100)
                        return json.dumps(recipe_data)
                    elif event.type == "error":
                        print(f"[DEBUG] Error in stream: {event.error}")
                        raise ValueError(f"Stream error: {event.error}")
            
        except Exception as e:
            print(f"[ERROR] Error in stream completion: {str(e)}")
            print(f"[ERROR] Error type: {type(e)}")
            raise

    async def generate_structured_recipe(
        self,
        content: Union[WebContent, TextContent],
        source_url: Optional[str],
        image_urls: List[str],
        progress_service: Optional['ProgressService'] = None,
        progress_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a structured recipe from cleaned web content or text content."""
        
        prompt = format_structured_recipe_prompt(
            content=content.main_content
        )
        
        # Créer une fonction de callback pour mettre à jour les details de l'étape
        async def update_progress(content: str, progress: int) -> None:
            if progress_service and progress_id:
                await progress_service.update_step(
                    progress_id=progress_id,
                    step="generate_recipe",
                    status="in_progress",
                    progress=progress,
                    details=content if progress < 100 else None,
                    message="Generating recipe structure..." if progress < 100 else "Recipe structure generated"
                )
        
        response = await self._stream_completion(
            messages=[
                {
                    "role": "system",
                    "content": prompt
                }
            ],
            on_content=update_progress
        )
        
        # La réponse est déjà validée par le schéma Pydantic
        recipe_json = json.loads(response)
        
        # Add source URL and image URL with default values
        recipe_json["metadata"]["sourceUrl"] = source_url or ""
        recipe_json["metadata"]["imageUrl"] = ""
        recipe_json["metadata"]["sourceImageUrl"] = ""  # Set default empty string
        if image_urls:
            recipe_json["metadata"]["sourceImageUrl"] = image_urls[0]
        elif isinstance(content, WebContent) and content.selected_image_url:
            recipe_json["metadata"]["sourceImageUrl"] = content.selected_image_url
            
        # Set default values for optional fields
        recipe_json["metadata"]["nationality"] = recipe_json["metadata"].get("nationality")
        recipe_json["metadata"]["author"] = recipe_json["metadata"].get("author")
        recipe_json["metadata"]["bookTitle"] = recipe_json["metadata"].get("bookTitle")
        
        # Determine diets and seasons based on ingredients
        recipe_json["metadata"]["diets"] = self._determine_diets(recipe_json)
        seasons, peak_months = await self._determine_seasons(recipe_json)
        recipe_json["metadata"]["seasons"] = seasons
        recipe_json["metadata"]["peakMonths"] = peak_months

        # Calculate total time and quick flag
        total_time = 0
        try:
            for sub_recipe in recipe_json["subRecipes"]:
                for step in sub_recipe["steps"]:
                    total_time += parse_time_to_minutes(step["time"])
        except Exception as e:
            print(f"[ERROR] Error generating recipe: {str(e)}")
            await save_error_to_file({
                "error_type": "time_parsing_error",
                "error_message": str(e),
                "recipe_json": recipe_json
            })
            raise ValueError(f"Recipe generation failed: {str(e)}")
        
        recipe_json["metadata"]["totalTime"] = total_time
        recipe_json["metadata"]["quick"] = total_time < 30
        
        try:
            # Create the Recipe with all fields
            recipe = Recipe(**recipe_json)
            return recipe_json
        except Exception as e:
            print(f"Erreur lors de la création de l'objet Recipe : {str(e)}")
            print("Recipe JSON :", json.dumps(recipe_json, indent=2))
            await save_error_to_file({
                "error_type": "recipe_validation_error",
                "error_message": str(e),
                "recipe_json": recipe_json
            })
            raise

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