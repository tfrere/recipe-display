"""
Recipe enricher module to add diet and seasonal information to recipes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional
import sys
import os
import argparse
import glob
from datetime import datetime

logger = logging.getLogger(__name__)

# Configurer le logger pour afficher les informations dans la console en mode main
def configure_logger():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

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
            {"name": "Tomato", "peak_months": ["June", "July", "August", "September"]},
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

    def _calculate_total_time(self, recipe_data: Dict[str, Any]) -> float:
        """
        Calcule le temps total de préparation d'une recette en additionnant les durées de chaque étape.
        
        Args:
            recipe_data: Les données de la recette à analyser
            
        Returns:
            Le temps total en minutes (float)
        """
        total_minutes = 0.0
        recipe_title = recipe_data.get("metadata", {}).get("title", "Untitled recipe")
        
        # Vérifier si la recette a déjà un temps total défini et non nul
        existing_time = recipe_data.get("metadata", {}).get("totalTime")
        if existing_time and existing_time > 0:
            logger.debug(f"Using existing total time for '{recipe_title}': {existing_time} minutes")
            return existing_time
        
        # Cas 1: Les étapes sont directement dans la racine du document
        if "steps" in recipe_data:
            steps = recipe_data.get("steps", [])
            logger.info(f"Found {len(steps)} steps directly in recipe '{recipe_title}'")
            
            # Si steps est une liste
            if isinstance(steps, list):
                for i, step in enumerate(steps):
                    time_str = step.get("time")
                    if time_str:
                        minutes = self._parse_time_to_minutes(time_str)
                        logger.debug(f"Step {i+1}: {time_str} = {minutes} minutes")
                        total_minutes += minutes
            # Si steps est un dictionnaire
            else:
                for step_id, step in steps.items():
                    time_str = step.get("time")
                    if time_str:
                        minutes = self._parse_time_to_minutes(time_str)
                        logger.debug(f"Step {step_id}: {time_str} = {minutes} minutes")
                        total_minutes += minutes
                        
            logger.info(f"Calculated total time from direct steps for '{recipe_title}': {total_minutes} minutes")
            return total_minutes
        
        # Cas 2: Les étapes sont dans des sous-recettes
        sub_recipes = recipe_data.get("subRecipes", {})
        
        if not sub_recipes:
            logger.warning(f"No steps or sub-recipes found in recipe '{recipe_title}'")
            return total_minutes
        
        logger.debug(f"Found {len(sub_recipes)} sub-recipes in recipe '{recipe_title}'")
        
        # Si sub_recipes est une liste, adaptons notre code pour la traiter
        if isinstance(sub_recipes, list):
            for i, sub_recipe in enumerate(sub_recipes):
                steps = sub_recipe.get("steps", [])
                logger.debug(f"Sub-recipe {i+1} has {len(steps)} steps")
                
                if not steps:
                    continue
                
                # Si steps est une liste
                if isinstance(steps, list):
                    for j, step in enumerate(steps):
                        time_str = step.get("time")
                        if time_str:
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.debug(f"Step {j+1}: {time_str} = {minutes} minutes")
                            total_minutes += minutes
                # Si steps est un dictionnaire
                else:
                    for step_id, step in steps.items():
                        time_str = step.get("time")
                        if time_str:
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.debug(f"Step {step_id}: {time_str} = {minutes} minutes")
                            total_minutes += minutes
        # Si sub_recipes est un dictionnaire
        else:
            for sub_recipe_id, sub_recipe in sub_recipes.items():
                steps = sub_recipe.get("steps", {})
                logger.debug(f"Sub-recipe {sub_recipe_id} has {len(steps) if steps else 0} steps")
                
                if not steps:
                    continue
                    
                # Si steps est une liste
                if isinstance(steps, list):
                    for j, step in enumerate(steps):
                        time_str = step.get("time")
                        if time_str:
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.debug(f"Step {j+1}: {time_str} = {minutes} minutes")
                            total_minutes += minutes
                # Si steps est un dictionnaire
                else:
                    for step_id, step in steps.items():
                        time_str = step.get("time")
                        if time_str:
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.debug(f"Step {step_id}: {time_str} = {minutes} minutes")
                            total_minutes += minutes
        
        logger.info(f"Calculated total time for recipe '{recipe_title}': {total_minutes} minutes")
        return total_minutes
        
    def _parse_time_to_minutes(self, time_str: str) -> float:
        """
        Convertit une chaîne de temps (ex: "1h30min", "5min", "1hour", "30 minutes", "1 hour 15 minutes") en minutes.
        Gère plusieurs formats de temps, y compris les formats complexes avec plusieurs unités.
        
        Args:
            time_str: La chaîne de temps à convertir
            
        Returns:
            Le temps en minutes (float)
        """
        if not time_str:
            return 0.0
        
        # Convertir en chaîne et mettre en minuscules pour normaliser
        time_str = str(time_str).lower().strip()
        logger.debug(f"Parsing time string: '{time_str}'")
            
        total_minutes = 0.0
        original_str = time_str  # Garder une copie pour le log
        
        # Format "Xh" ou "XhYmin"
        if "h" in time_str:
            hour_match = time_str.find("h")
            try:
                hours = float(time_str[:hour_match].strip())
                total_minutes += hours * 60
                time_str = time_str[hour_match + 1:]  # Supprime la partie heures pour traiter le reste
                logger.debug(f"Parsed {hours} hours, remaining: '{time_str}'")
            except ValueError:
                logger.warning(f"Could not parse hours from time string: {time_str}")
        
        # Format "X hour" ou "X hours"
        elif "hour" in time_str:
            hour_match = time_str.find("hour")
            try:
                hours_part = time_str[:hour_match].strip()
                hours = float(hours_part)
                total_minutes += hours * 60
                
                # Supprimer la partie des heures pour traiter le reste
                time_str = time_str[hour_match + len("hour"):]
                if time_str.startswith("s"):  # Supprimer le 's' pluriel si présent
                    time_str = time_str[1:]
                time_str = time_str.strip()
                logger.debug(f"Parsed {hours} hours, remaining: '{time_str}'")
            except ValueError:
                logger.warning(f"Could not parse hours from time string: {original_str}")
        
        # Format "Xmin" ou "X min"
        if "min" in time_str:
            min_match = time_str.find("min")
            try:
                # Trouver le début de la partie minutes
                min_start = 0
                # Si la chaîne contient plus que juste des minutes, chercher le début de la partie minutes
                if total_minutes > 0:
                    # Chercher le premier chiffre après la partie heures
                    for i, char in enumerate(time_str):
                        if char.isdigit():
                            min_start = i
                            break
                
                min_part = time_str[min_start:min_match].strip()
                if min_part:  # Vérifier que la partie minutes n'est pas vide
                    minutes = float(min_part)
                    total_minutes += minutes
                    logger.debug(f"Parsed {minutes} minutes")
            except ValueError:
                logger.warning(f"Could not parse minutes from time string: {time_str}")
        
        # Format "X minute" ou "X minutes"
        elif "minute" in time_str:
            minute_match = time_str.find("minute")
            try:
                # Trouver le début de la partie minutes
                min_start = 0
                # Si la chaîne contient plus que juste des minutes, chercher le début de la partie minutes
                if total_minutes > 0:
                    # Chercher le premier chiffre après la partie heures
                    for i, char in enumerate(time_str):
                        if char.isdigit():
                            min_start = i
                            break
                
                min_part = time_str[min_start:minute_match].strip()
                if min_part:  # Vérifier que la partie minutes n'est pas vide
                    minutes = float(min_part)
                    total_minutes += minutes
                    logger.debug(f"Parsed {minutes} minutes")
            except ValueError:
                logger.warning(f"Could not parse minutes from time string: {time_str}")
                
        # Format "Xs", "Xsec", "X second" ou "X seconds"
        if "sec" in time_str or "second" in time_str or (total_minutes == 0 and time_str.endswith("s") and time_str[-2:-1].isdigit()):
            # Déterminer où commence la partie secondes
            sec_match = -1
            if "sec" in time_str:
                sec_match = time_str.find("sec")
            elif "second" in time_str:
                sec_match = time_str.find("second")
            
            if sec_match != -1:
                try:
                    # Trouver le début de la partie secondes
                    sec_start = 0
                    if total_minutes > 0:
                        # Chercher le premier chiffre après la partie minutes
                        for i, char in enumerate(time_str):
                            if char.isdigit():
                                sec_start = i
                                break
                    
                    sec_part = time_str[sec_start:sec_match].strip()
                    if sec_part:
                        seconds = float(sec_part)
                        total_minutes += seconds / 60
                        logger.debug(f"Parsed {seconds} seconds")
                except ValueError:
                    logger.warning(f"Could not parse seconds from time string: {time_str}")
        
        # Si après tout ça, le total est toujours 0, vérifier si la chaîne contient juste un nombre
        if total_minutes == 0 and time_str.strip().replace('.', '', 1).isdigit():
            try:
                # Par défaut, on considère que c'est en minutes
                total_minutes = float(time_str.strip())
                logger.debug(f"Interpreted '{time_str}' as {total_minutes} minutes")
            except ValueError:
                pass
                
        logger.debug(f"Parsed time '{original_str}' to {total_minutes} minutes")
        return total_minutes

    def _calculate_total_cooking_time(self, recipe_data: Dict[str, Any]) -> float:
        """
        Calcule le temps total de cuisson activetotalCookingTime d'une recette en additionnant 
        les durées des étapes actives uniquement (où stepMode n'est pas 'passive').
        
        Args:
            recipe_data: Les données de la recette à analyser
            
        Returns:
            Le temps total de cuisson active en minutes (float)
        """
        total_minutes = 0.0
        recipe_title = recipe_data.get("metadata", {}).get("title", "Untitled recipe")
        
        # Vérifier si la recette a déjà un temps de cuisson total défini et non nul
        existing_cooking_time = recipe_data.get("metadata", {}).get("totalCookingTime")
        if existing_cooking_time and existing_cooking_time > 0:
            logger.info(f"Using existing total cooking time for '{recipe_title}': {existing_cooking_time} minutes")
            return existing_cooking_time
        
        # Cas 1: Les étapes sont directement dans la racine du document
        if "steps" in recipe_data:
            steps = recipe_data.get("steps", [])
            logger.info(f"Analyzing {len(steps)} steps for active cooking time in recipe '{recipe_title}'")
            
            # Si steps est une liste
            if isinstance(steps, list):
                for i, step in enumerate(steps):
                    time_str = step.get("time")
                    step_mode = step.get("stepMode", "active")  # Par défaut, on considère les étapes comme actives
                    
                    # Ne compter que les étapes actives
                    if time_str and step_mode != "passive":
                        minutes = self._parse_time_to_minutes(time_str)
                        logger.info(f"Active step {i+1}: '{step.get('action', '')}' with time {time_str} = {minutes} minutes")
                        total_minutes += minutes
                    elif time_str and step_mode == "passive":
                        logger.info(f"Skipping passive step {i+1}: '{step.get('action', '')}' with time {time_str}")
            # Si steps est un dictionnaire
            else:
                for step_id, step in steps.items():
                    time_str = step.get("time")
                    step_mode = step.get("stepMode", "active")  # Par défaut, on considère les étapes comme actives
                    
                    # Ne compter que les étapes actives
                    if time_str and step_mode != "passive":
                        minutes = self._parse_time_to_minutes(time_str)
                        logger.info(f"Active step {step_id}: '{step.get('action', '')}' with time {time_str} = {minutes} minutes")
                        total_minutes += minutes
                    elif time_str and step_mode == "passive":
                        logger.info(f"Skipping passive step {step_id}: '{step.get('action', '')}' with time {time_str}")
                        
            logger.info(f"Calculated active cooking time from direct steps for '{recipe_title}': {total_minutes} minutes")
            return total_minutes
        
        # Cas 2: Les étapes sont dans des sous-recettes
        sub_recipes = recipe_data.get("subRecipes", {})
        
        if not sub_recipes:
            logger.warning(f"No steps or sub-recipes found for active cooking time in recipe '{recipe_title}'")
            return total_minutes
        
        logger.info(f"Found {len(sub_recipes)} sub-recipes for active cooking time in '{recipe_title}'")
        
        # Si sub_recipes est une liste
        if isinstance(sub_recipes, list):
            for i, sub_recipe in enumerate(sub_recipes):
                steps = sub_recipe.get("steps", [])
                logger.info(f"Sub-recipe {i+1} has {len(steps)} steps to analyze for active cooking time")
                
                if not steps:
                    continue
                
                # Si steps est une liste
                if isinstance(steps, list):
                    for j, step in enumerate(steps):
                        time_str = step.get("time")
                        step_mode = step.get("stepMode", "active")  # Par défaut, on considère les étapes comme actives
                        
                        # Ne compter que les étapes actives
                        if time_str and step_mode != "passive":
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.info(f"Active step {j+1}: '{step.get('action', '')}' with time {time_str} = {minutes} minutes")
                            total_minutes += minutes
                        elif time_str and step_mode == "passive":
                            logger.info(f"Skipping passive step {j+1}: '{step.get('action', '')}' with time {time_str}")
                # Si steps est un dictionnaire
                else:
                    for step_id, step in steps.items():
                        time_str = step.get("time")
                        step_mode = step.get("stepMode", "active")  # Par défaut, on considère les étapes comme actives
                        
                        # Ne compter que les étapes actives
                        if time_str and step_mode != "passive":
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.info(f"Active step {step_id}: '{step.get('action', '')}' with time {time_str} = {minutes} minutes")
                            total_minutes += minutes
                        elif time_str and step_mode == "passive":
                            logger.info(f"Skipping passive step {step_id}: '{step.get('action', '')}' with time {time_str}")
        # Si sub_recipes est un dictionnaire
        else:
            for sub_recipe_id, sub_recipe in sub_recipes.items():
                steps = sub_recipe.get("steps", {})
                logger.info(f"Sub-recipe {sub_recipe_id} has {len(steps) if steps else 0} steps to analyze for active cooking time")
                
                if not steps:
                    continue
                    
                # Si steps est une liste
                if isinstance(steps, list):
                    for j, step in enumerate(steps):
                        time_str = step.get("time")
                        step_mode = step.get("stepMode", "active")  # Par défaut, on considère les étapes comme actives
                        
                        # Ne compter que les étapes actives
                        if time_str and step_mode != "passive":
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.info(f"Active step {j+1}: '{step.get('action', '')}' with time {time_str} = {minutes} minutes")
                            total_minutes += minutes
                        elif time_str and step_mode == "passive":
                            logger.info(f"Skipping passive step {j+1}: '{step.get('action', '')}' with time {time_str}")
                # Si steps est un dictionnaire
                else:
                    for step_id, step in steps.items():
                        time_str = step.get("time")
                        step_mode = step.get("stepMode", "active")  # Par défaut, on considère les étapes comme actives
                        
                        # Ne compter que les étapes actives
                        if time_str and step_mode != "passive":
                            minutes = self._parse_time_to_minutes(time_str)
                            logger.info(f"Active step {step_id}: '{step.get('action', '')}' with time {time_str} = {minutes} minutes")
                            total_minutes += minutes
                        elif time_str and step_mode == "passive":
                            logger.info(f"Skipping passive step {step_id}: '{step.get('action', '')}' with time {time_str}")
        
        logger.info(f"Calculated active cooking time for recipe '{recipe_title}': {total_minutes} minutes")
        return total_minutes

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
        Determine the diets based on recipe ingredients categories.
        
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
            # Utiliser la catégorie de l'ingrédient plutôt que l'analyse par mots-clés
            category = ingredient.get("category", "").lower()
            
            if not name:
                continue
                
            # Utilisation des catégories pour la classification
            if category == "meat":
                has_meat = True
                meat_ingredients.append(name)
                
            elif category == "seafood":
                has_seafood = True
                seafood_ingredients.append(name)
                
            elif category == "dairy":
                has_dairy = True
                dairy_ingredients.append(name)
                
            elif category == "egg":
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
        
        # Calculer le temps total
        logger.debug("Calculating total recipe time...")
        total_time = self._calculate_total_time(recipe_data)
        logger.debug(f"Total time calculation complete: {total_time} minutes")
        
        # Calculer le temps de cuisson actif
        logger.debug("Calculating active cooking time...")
        total_cooking_time = self._calculate_total_cooking_time(recipe_data)
        logger.debug(f"Active cooking time calculation complete: {total_cooking_time} minutes")
        
        # Add the enrichment data to the recipe metadata
        if "metadata" not in enriched_recipe:
            enriched_recipe["metadata"] = {}
            
        # Ajouter la date de création si elle n'existe pas déjà
        if "createdAt" not in enriched_recipe["metadata"]:
            enriched_recipe["metadata"]["createdAt"] = datetime.now().isoformat()
            
        # Déterminer le mode de création (text ou url) en fonction des métadonnées existantes
        if "creationMode" not in enriched_recipe["metadata"]:
            if "contentHash" in enriched_recipe["metadata"]:
                enriched_recipe["metadata"]["creationMode"] = "text"
            elif "sourceUrl" in enriched_recipe["metadata"] and enriched_recipe["metadata"]["sourceUrl"]:
                enriched_recipe["metadata"]["creationMode"] = "url"
            else:
                # Si on ne peut pas déterminer, mettre une valeur par défaut
                enriched_recipe["metadata"]["creationMode"] = "unknown"
            
        enriched_recipe["metadata"]["diets"] = diets
        enriched_recipe["metadata"]["seasons"] = seasons
        enriched_recipe["metadata"]["totalTime"] = total_time
        enriched_recipe["metadata"]["totalCookingTime"] = total_cooking_time
        
        logger.info(f"Recipe \"{recipe_title}\" enriched with: {', '.join(diets)} diets, {', '.join(seasons)} seasons, total time: {total_time} minutes, active cooking time: {total_cooking_time} minutes")
        
        return enriched_recipe 

def re_enrich_all_recipes(recipes_dir: str, output_dir: Optional[str] = None, should_backup: bool = True) -> int:
    """
    Ré-enrichit toutes les recettes dans le répertoire spécifié.
    
    Args:
        recipes_dir: Chemin vers le répertoire contenant les recettes à ré-enrichir
        output_dir: Répertoire de sortie (si différent du répertoire d'entrée)
        should_backup: Si True, crée une sauvegarde des fichiers originaux
        
    Returns:
        Le nombre de recettes traitées
    """
    # Utiliser le même répertoire si output_dir n'est pas spécifié
    if output_dir is None:
        output_dir = recipes_dir
        
    # Vérifier que le répertoire existe
    recipes_path = Path(recipes_dir)
    if not recipes_path.is_dir():
        logger.error(f"Le répertoire {recipes_dir} n'existe pas")
        return 0
        
    # Créer le répertoire de sortie s'il n'existe pas
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Créer le répertoire de backup si nécessaire
    backup_dir = None
    if should_backup and output_dir == recipes_dir:
        backup_dir = recipes_path.parent / f"{recipes_path.name}_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Sauvegarde des fichiers originaux dans {backup_dir}")
    
    # Créer l'enrichisseur
    enricher = RecipeEnricher()
    
    # Compter le nombre de recettes traitées
    processed_count = 0
    
    # Trouver tous les fichiers JSON dans le répertoire des recettes
    recipe_files = list(recipes_path.glob('**/*.recipe.json'))
    total_files = len(recipe_files)
    
    logger.info(f"Début du traitement de {total_files} fichiers de recettes")
    
    # Traiter chaque fichier
    for i, recipe_file in enumerate(recipe_files):
        logger.info(f"[{i+1}/{total_files}] Traitement de {recipe_file.name}")
        
        try:
            # Lire le contenu du fichier
            with open(recipe_file, 'r', encoding='utf-8') as f:
                recipe_data = json.load(f)
                
            # Faire une copie de sauvegarde si nécessaire
            if backup_dir:
                backup_file = backup_dir / recipe_file.name
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(recipe_data, f, ensure_ascii=False, indent=2)
            
            # Enrichir la recette
            enriched_data = enricher.enrich_recipe(recipe_data)
            
            # Déterminer le chemin de sortie
            if output_dir == recipes_dir:
                output_file = recipe_file
            else:
                rel_path = recipe_file.relative_to(recipes_path)
                output_file = Path(output_dir) / rel_path
                # Créer les répertoires parents si nécessaire
                output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire la recette enrichie
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)
                
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {recipe_file}: {str(e)}")
    
    logger.info(f"Terminé: {processed_count} recettes traitées sur {total_files}")
    return processed_count

def main():
    """
    Point d'entrée principal pour exécuter l'outil en ligne de commande
    """
    # Configurer le logger
    configure_logger()
    
    # Déterminer le chemin par défaut vers les recettes
    # On suppose que le script est exécuté depuis le répertoire du projet
    # Nous cherchons le dossier /server/data/recipes
    default_recipes_dir = None
    
    # Essaye de trouver le dossier server/data/recipes
    current_dir = Path.cwd()
    
    # Option 1: Nous sommes dans le dossier du package
    package_parent = Path(__file__).parent.parent.parent.parent.parent  # monter jusqu'à /server
    server_data_path = package_parent / 'data' / 'recipes'
    
    # Option 2: Nous sommes quelque part dans la structure du projet
    project_server_path = current_dir
    while project_server_path.name and project_server_path.name != 'server':
        project_server_path = project_server_path.parent
    
    project_data_path = project_server_path / 'data' / 'recipes'
    
    # Option 3: Chercher depuis le répertoire parent immédiat
    immediate_parent_path = Path(__file__).parent.parent.parent.parent.parent.parent / 'server' / 'data' / 'recipes'
    
    # Vérifier les chemins possibles
    if server_data_path.exists():
        default_recipes_dir = str(server_data_path)
        logger.info(f"Utilisation du répertoire de recettes: {default_recipes_dir}")
    elif project_data_path.exists():
        default_recipes_dir = str(project_data_path)
        logger.info(f"Utilisation du répertoire de recettes: {default_recipes_dir}")
    elif immediate_parent_path.exists():
        default_recipes_dir = str(immediate_parent_path)
        logger.info(f"Utilisation du répertoire de recettes: {default_recipes_dir}")
    else:
        default_recipes_dir = './server/data/recipes'
        logger.warning(f"Impossible de trouver automatiquement le répertoire des recettes. Utilisation du chemin par défaut: {default_recipes_dir}")
    
    # Analyser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description='Outil d\'enrichissement de recettes')
    parser.add_argument('--recipes_dir', type=str, default=default_recipes_dir,
                       help=f'Répertoire contenant les recettes à enrichir (défaut: {default_recipes_dir})')
    parser.add_argument('--output_dir', type=str, default=None,
                       help='Répertoire de sortie pour les recettes enrichies (défaut: même que recipes_dir)')
    parser.add_argument('--no-backup', action='store_true',
                       help='Ne pas créer de sauvegarde des fichiers originaux')
    
    args = parser.parse_args()
    
    # Exécuter l'enrichissement
    count = re_enrich_all_recipes(
        recipes_dir=args.recipes_dir,
        output_dir=args.output_dir,
        should_backup=not args.no_backup
    )
    
    # Afficher un résumé
    logger.info(f"Enrichissement terminé: {count} recettes traitées")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 