"""
Recipe enricher module to add diet and seasonal information to recipes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional

logger = logging.getLogger(__name__)

# Inclure directement les données saisonnières comme constante dans le code
SEASONAL_DATA = {
    "produce": {
        "vegetables": [
            {"name": "Asparagus", "peak_months": ["April", "May", "June"]},
            {"name": "Broccoli", "peak_months": ["September", "October", "November"]},
            {"name": "Cabbage", "peak_months": ["January", "February", "October", "November", "December"]},
            {"name": "Carrot", "peak_months": ["January", "February", "March", "September", "October", "November", "December"]},
            {"name": "Cauliflower", "peak_months": ["January", "March", "April", "September", "October", "November", "December"]},
            {"name": "Celery", "peak_months": ["July", "August", "September", "October", "November"]},
            {"name": "Corn", "peak_months": ["July", "August", "September"]},
            {"name": "Cucumber", "peak_months": ["May", "June", "July", "August", "September"]},
            {"name": "Eggplant", "peak_months": ["June", "July", "August", "September", "October"]},
            {"name": "Garlic", "peak_months": ["July", "August", "September", "October"]},
            {"name": "Kale", "peak_months": ["January", "February", "September", "October", "November", "December"]},
            {"name": "Leek", "peak_months": ["January", "February", "March", "September", "October", "November", "December"]},
            {"name": "Lettuce", "peak_months": ["April", "May", "June", "July", "August", "September", "October"]},
            {"name": "Mushroom", "peak_months": ["January", "February", "March", "April", "May", "September", "October", "November", "December"]},
            {"name": "Onion", "peak_months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]},
            {"name": "Pea", "peak_months": ["April", "May", "June", "July"]},
            {"name": "Pepper", "peak_months": ["June", "July", "August", "September", "October"]},
            {"name": "Potato", "peak_months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]},
            {"name": "Pumpkin", "peak_months": ["September", "October", "November", "December"]},
            {"name": "Radish", "peak_months": ["April", "May", "June", "July", "August", "September", "October"]},
            {"name": "Spinach", "peak_months": ["March", "April", "May", "June", "September", "October"]},
            {"name": "Squash", "peak_months": ["August", "September", "October", "November", "December"]},
            {"name": "Sweet Potato", "peak_months": ["September", "October", "November", "December"]},
            {"name": "Tomato", "peak_months": ["June", "July", "August", "September", "October"]},
            {"name": "Turnip", "peak_months": ["January", "February", "October", "November", "December"]},
            {"name": "Zucchini", "peak_months": ["June", "July", "August", "September"]}
        ],
        "fruits": [
            {"name": "Apple", "peak_months": ["September", "October", "November"]},
            {"name": "Avocado", "peak_months": ["January", "February", "March", "April", "May", "June", "July", "August"]},
            {"name": "Banana", "peak_months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]},
            {"name": "Berry", "peak_months": ["May", "June", "July", "August"]},
            {"name": "Cherry", "peak_months": ["May", "June", "July"]},
            {"name": "Grapefruit", "peak_months": ["January", "February", "March", "April", "November", "December"]},
            {"name": "Grape", "peak_months": ["August", "September", "October"]},
            {"name": "Lemon", "peak_months": ["January", "February", "March", "April", "May", "December"]},
            {"name": "Lime", "peak_months": ["May", "June", "July", "August", "September", "October"]},
            {"name": "Mango", "peak_months": ["May", "June", "July", "August", "September"]},
            {"name": "Melon", "peak_months": ["June", "July", "August", "September"]},
            {"name": "Orange", "peak_months": ["January", "February", "March", "April", "December"]},
            {"name": "Peach", "peak_months": ["June", "July", "August", "September"]},
            {"name": "Pear", "peak_months": ["August", "September", "October", "November"]},
            {"name": "Pineapple", "peak_months": ["March", "April", "May", "June", "July"]},
            {"name": "Plum", "peak_months": ["July", "August", "September"]},
            {"name": "Raspberry", "peak_months": ["June", "July", "August", "September"]},
            {"name": "Strawberry", "peak_months": ["April", "May", "June", "July"]},
            {"name": "Watermelon", "peak_months": ["June", "July", "August", "September"]}
        ]
    }
}

class RecipeEnricher:
    """
    Class for enriching recipes with additional information like diet and seasons.
    """
    
    def __init__(self, data_folder: Optional[Path] = None):
        """
        Initialize the recipe enricher.
        
        Args:
            data_folder: Optional path to the data folder (non utilisé car données embarquées)
        """
        self._seasonal_data = SEASONAL_DATA
        self._data_folder = data_folder or Path(__file__).parent / "data"
        
    def _load_seasonal_data(self):
        """
        Load seasonal vegetables and fruits data from the embedded constant.
        This method is kept for backward compatibility but no longer needs to load from file.
        """
        # Données déjà chargées depuis la constante SEASONAL_DATA
        if self._seasonal_data is None:
            self._seasonal_data = SEASONAL_DATA
            logger.debug(f"Using embedded seasonal data with {len(self._seasonal_data.get('produce', {}).get('vegetables', []))} vegetables and {len(self._seasonal_data.get('produce', {}).get('fruits', []))} fruits")

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

    def _determine_seasons(self, recipe_json: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Determine the seasons and peak months based on produce ingredients.
        Only seasons that are common to all relevant produce ingredients are returned.
        
        Args:
            recipe_json: The recipe data to analyze
            
        Returns:
            A tuple containing (seasons, peak_months)
        """
        # Ensure seasonal data is loaded
        if self._seasonal_data is None:
            self._load_seasonal_data()
        
        # Track ingredients that were actually matched
        matched_ingredients = []
        # Track seasons for each ingredient
        ingredient_seasons = {}
        # All unique peak months across all ingredients
        all_peak_months = set()
        
        # Get ingredient names based on the structure of our recipe JSON
        ingredients = recipe_json.get("ingredients", [])
        produce_count = sum(1 for ingredient in ingredients if ingredient.get("category", "").lower() == "produce")
        
        logger.debug(f"Analyzing {produce_count} produce ingredients for seasonal availability")
        
        # First, identify all produce ingredients and their seasons
        for ingredient in ingredients:
            name = ingredient.get("name", "").lower()
            category = ingredient.get("category", "").lower()
            
            # Skip if not a produce ingredient
            if not name or category != "produce":
                continue
                
            # Look for matching produce in our seasonal data
            found_match = False
            
            if self._seasonal_data and "produce" in self._seasonal_data:
                for produce_type in ["vegetables", "fruits"]:
                    for item in self._seasonal_data["produce"].get(produce_type, []):
                        item_name = item["name"].lower()
                        
                        # Check if ingredient matches this produce item
                        if name in item_name or item_name in name:
                            # Get the peak months for this ingredient
                            peak_months = set(item.get("peak_months", []))
                            
                            if peak_months:
                                # Calculate the seasons for this ingredient
                                seasons = set(self._determine_seasons_from_months(peak_months))
                                
                                # Store the info
                                matched_ingredients.append(name)
                                ingredient_seasons[name] = seasons
                                all_peak_months.update(peak_months)
                                found_match = True
                                logger.debug(f"Matched ingredient '{name}' with seasonal item '{item_name}', seasons: {seasons}")
                                break
                    
                    if found_match:
                        break
        
        # If no ingredients were matched, return "all" seasons
        if not matched_ingredients:
            logger.info("No seasonal produce ingredients found in recipe, setting season to 'all'")
            return ["all"], []
        
        logger.info(f"Found {len(matched_ingredients)} seasonal ingredients: {', '.join(matched_ingredients)}")
            
        # Find common seasons across all matched ingredients
        common_seasons = None
        for name, seasons in ingredient_seasons.items():
            if common_seasons is None:
                common_seasons = seasons
            else:
                common_seasons = common_seasons.intersection(seasons)
                
        # If no common seasons (empty intersection), use the most restrictive season
        if not common_seasons:
            logger.debug("No common seasons found across all ingredients, using most restrictive")
            # Default to most restrictive (smallest set of seasons)
            smallest_set_size = float('inf')
            most_restrictive_seasons = set()
            most_restrictive_ingredient = ""
            
            for name, seasons in ingredient_seasons.items():
                if len(seasons) < smallest_set_size:
                    smallest_set_size = len(seasons)
                    most_restrictive_seasons = seasons
                    most_restrictive_ingredient = name
                    
            common_seasons = most_restrictive_seasons
            logger.info(f"Using most restrictive seasons from '{most_restrictive_ingredient}': {common_seasons}")
        else:
            logger.info(f"Found common seasons across all ingredients: {common_seasons}")
        
        # Convert back to list and sort
        seasons_list = sorted(list(common_seasons)) if common_seasons else ["all"]
        peak_months_list = sorted(list(all_peak_months))
        
        return seasons_list, peak_months_list

    def _determine_diets(self, recipe_json: Dict[str, Any]) -> List[str]:
        """
        Determine the diets based on recipe ingredients.
        
        Args:
            recipe_json: The recipe data to analyze
            
        Returns:
            A list of applicable diets
        """
        diets = []
        has_meat = False
        has_seafood = False
        has_dairy = False
        has_egg = False
        
        # Get ingredients
        ingredients = recipe_json.get("ingredients", [])
        
        logger.debug(f"Analyzing {len(ingredients)} ingredients for diet determination")
        
        # Check all ingredients
        meat_ingredients = []
        seafood_ingredients = []
        dairy_ingredients = []
        egg_ingredients = []
        
        for ingredient in ingredients:
            name = ingredient.get("name", "").lower()
            if not name:
                continue
                
            # Check for meat
            if any(meat in name for meat in ["beef", "pork", "chicken", "turkey", "lamb", "duck", "venison", "bacon", "sausage", "ham"]):
                has_meat = True
                meat_ingredients.append(name)
                
            # Check for seafood
            if any(seafood in name for seafood in ["fish", "salmon", "tuna", "cod", "shrimp", "prawn", "lobster", "crab", "mussel", "oyster", "clam", "scallop"]):
                has_seafood = True
                seafood_ingredients.append(name)
                
            # Check for dairy
            if any(dairy in name for dairy in ["milk", "cheese", "butter", "cream", "yogurt", "yoghurt", "curd", "whey", "ricotta", "mozzarella"]):
                has_dairy = True
                dairy_ingredients.append(name)
                
            # Check for eggs
            if "egg" in name:
                has_egg = True
                egg_ingredients.append(name)
        
        # Log what was found
        if meat_ingredients:
            logger.debug(f"Found meat ingredients: {', '.join(meat_ingredients)}")
        if seafood_ingredients:
            logger.debug(f"Found seafood ingredients: {', '.join(seafood_ingredients)}")
        if dairy_ingredients:
            logger.debug(f"Found dairy ingredients: {', '.join(dairy_ingredients)}")
        if egg_ingredients:
            logger.debug(f"Found egg ingredients: {', '.join(egg_ingredients)}")
            
        # Determine diets based on ingredients
        if has_meat or has_seafood:
            diets = ["omnivorous"]
            logger.info("Recipe classified as: omnivorous")
        elif has_dairy or has_egg:
            diets = ["vegetarian", "omnivorous"]
            logger.info("Recipe classified as: vegetarian (and omnivorous)")
        else:
            diets = ["vegan", "vegetarian", "omnivorous"]
            logger.info("Recipe classified as: vegan (and vegetarian, omnivorous)")
            
        # Add pescatarian if applicable
        if not has_meat and has_seafood:
            diets.append("pescatarian")
            logger.info("Recipe also classified as: pescatarian")
            
        return diets

    def enrich_recipe(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a recipe with additional information like diet and seasons.
        
        Args:
            recipe_data: The recipe data to enrich
            
        Returns:
            The enriched recipe data
        """
        recipe_title = recipe_data.get("metadata", {}).get("title", "Untitled recipe")
        logger.info(f"Enriching recipe: \"{recipe_title}\"")
        
        # Make a copy to avoid modifying the original
        enriched_recipe = recipe_data.copy()
        
        # Determine diets
        logger.debug("Determining applicable diets...")
        diets = self._determine_diets(recipe_data)
        logger.debug(f"Diet analysis complete: {', '.join(diets)}")
        
        # Determine seasons
        logger.debug("Determining seasonal availability...")
        seasons, peak_months = self._determine_seasons(recipe_data)
        logger.debug(f"Season analysis complete: {', '.join(seasons)}")
        
        # Add the enrichment data to the recipe metadata
        if "metadata" not in enriched_recipe:
            enriched_recipe["metadata"] = {}
            
        enriched_recipe["metadata"]["diets"] = diets
        enriched_recipe["metadata"]["seasons"] = seasons
        
        logger.info(f"Recipe \"{recipe_title}\" enriched with: {', '.join(diets)} diets, {', '.join(seasons)} seasons")
        return enriched_recipe 