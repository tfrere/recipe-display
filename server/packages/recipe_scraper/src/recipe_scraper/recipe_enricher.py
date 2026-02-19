"""
Recipe enricher module to add diet, seasonal, and nutritional information to recipes.

Enrichment pipeline:
1. Diet classification (vegan, vegetarian, omnivorous, pescatarian)
2. Seasonal availability based on produce ingredients
3. Total time and active cooking time calculation
4. Nutritional profile via OpenNutrition embeddings (async)
   - Ingredient name translation to English (local dict + LLM fallback)
   - BGE-small embedding match against OpenNutrition index (zero false positives)
   - Per-serving macro computation with liquid retention heuristics
   - Qualitative nutrition tags
"""

import json
import logging
import math
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional
from .observability import observe, langfuse_context
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Liquid retention heuristics for nutrition calculation
# ---------------------------------------------------------------------------
# Keywords in English ingredient names that identify cooking liquids
_LIQUID_KEYWORDS = {
    # Broths / stocks
    "broth", "stock", "bouillon", "fond",
    # Cooking alcohol
    "wine", "white wine", "red wine", "beer", "cognac", "brandy", "marsala",
    "rum", "port", "sherry", "vermouth",
    # Discarded cooking water
    "pasta water", "blanching water", "cooking water",
}

# Cooking-alcohol keywords (subset of _LIQUID_KEYWORDS)
_ALCOHOL_KEYWORDS = {
    "wine", "white wine", "red wine", "beer", "cognac", "brandy", "marsala",
    "rum", "port", "sherry", "vermouth",
}

# Discarded-liquid keywords (0% retention)
_DISCARD_KEYWORDS = {
    "pasta water", "blanching water", "cooking water",
}

# Soup-type recipe keywords (checked against recipe title, lowercased)
_SOUP_KEYWORDS = {
    "soupe", "soup", "velouté", "veloute", "potage", "bisque",
    "minestrone", "bouillon", "consommé", "consomme", "chowder",
    "gazpacho", "harira", "chorba",
}

# Frying-oil keywords — large quantities of oil for deep/shallow frying.
# Only ~10-15% of frying oil is absorbed by food (USDA retention factors).
_FRYING_OIL_KEYWORDS = {
    "peanut oil", "vegetable oil", "canola oil", "sunflower oil",
    "corn oil", "soybean oil", "frying oil", "neutral oil",
}
# Confit/rendering fat keywords — fat used as a cooking medium,
# mostly discarded after cooking. ~20% retained on the food surface.
_CONFIT_FAT_KEYWORDS = {
    "duck fat", "goose fat", "lard", "schmaltz", "tallow",
    "rendered fat", "bacon fat", "beef dripping",
}
# Minimum volume of oil (in ml) to be considered frying oil.
# Below this, the oil is likely used for sautéing and fully consumed.
_FRYING_OIL_THRESHOLD_ML = 400.0

# Retention factors by liquid category
_LIQUID_RETENTION_FACTORS = {
    "discard": 0.0,       # Liquid is thrown away (pasta water)
    "alcohol": 0.20,      # Most evaporates during cooking
    "soup_broth": 0.80,   # Broth IS the dish in soups
    "braising": 0.30,     # Broth partly consumed, partly evaporated
    "frying_oil": 0.15,   # ~15% oil absorption (USDA retention factors)
    "confit_fat": 0.20,   # ~20% fat retained on food surface after confit
}

# Minimum volume (in ml) to trigger liquid retention heuristic.
# Small quantities (a splash of wine, 2 tbsp broth) are fully absorbed.
_LIQUID_VOLUME_THRESHOLD_ML = 250.0


def _is_soup_recipe(metadata: Dict[str, Any]) -> bool:
    """
    Detect whether a recipe is a soup/broth-based dish where
    the liquid is the main component and is fully consumed.

    Args:
        metadata: Recipe metadata dict (with 'title', 'type', etc.)

    Returns:
        True if the recipe looks like a soup.
    """
    title = (metadata.get("title") or "").lower()
    recipe_type = (metadata.get("type") or "").lower()
    combined = f"{title} {recipe_type}"
    return any(kw in combined for kw in _SOUP_KEYWORDS)


def _classify_liquid(name_en: str, is_soup: bool) -> Optional[str]:
    """
    Classify a liquid ingredient into a retention category.

    Args:
        name_en: English ingredient name (lowered).
        is_soup: Whether the recipe is a soup.

    Returns:
        One of 'discard', 'alcohol', 'soup_broth', 'braising', or None.
    """
    # Check multi-word keywords first (e.g. "pasta water")
    for kw in _DISCARD_KEYWORDS:
        if kw in name_en:
            return "discard"

    for kw in _ALCOHOL_KEYWORDS:
        if kw in name_en:
            return "alcohol"

    # Check broth/stock keywords
    broth_keywords = {"broth", "stock", "bouillon", "fond"}
    for kw in broth_keywords:
        if kw in name_en:
            return "soup_broth" if is_soup else "braising"

    # Check confit/rendering fat
    for kw in _CONFIT_FAT_KEYWORDS:
        if kw in name_en:
            return "confit_fat"

    # Check frying oil (large volumes of neutral oil)
    for kw in _FRYING_OIL_KEYWORDS:
        if kw in name_en:
            return "frying_oil"
    # Generic "oil" or "olive oil" with large volume → likely frying
    if "oil" in name_en:
        return "frying_oil"

    return None


# Configurer le logger pour afficher les informations dans la console en mode main
def configure_logger():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

# Seasonal produce data from ADEME Impact CO2 (Licence Ouverte 2.0)
# Source: https://impactco2.fr/api/v1/fruitsetlegumes
_SEASONAL_DATA_PATH = Path(__file__).parent / "data" / "seasonal_produce.json"

def _load_seasonal_data() -> dict:
    """Load seasonal produce data from JSON file."""
    try:
        with open(_SEASONAL_DATA_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Seasonal data file not found: {_SEASONAL_DATA_PATH}")
        return {"produce": {"vegetables": [], "fruits": []}}

SEASONAL_DATA = _load_seasonal_data()

# Ingredients that are available year-round in stores (imported/stored) and should
# NOT influence recipe seasonality, even though ADEME marks them with limited months.
# ADEME data reflects local French production only (e.g. Lemon = Jan-Feb = Menton).
# Loaded from the data file for easy maintenance; falls back to a hardcoded set.
YEAR_ROUND_STAPLES: Set[str] = set(
    SEASONAL_DATA.get("year_round_staples", [
        "lemon", "lime", "garlic", "onion", "potato", "ginger",
        "shallot", "sweet potato",
    ])
)


def _build_seasonal_index(data: dict) -> Dict[str, dict]:
    """
    Build a normalized lookup index from SEASONAL_DATA.
    
    Returns a dict mapping normalized names (lowercase, singular) to their
    seasonal item data. Handles plurals and common aliases automatically.
    
    Example: {"pear": {...}, "pears": {...}, "zucchini": {...}, "courgette": {...}}
    """
    import re
    index: Dict[str, dict] = {}
    
    for produce_type in ["vegetables", "fruits"]:
        for item in data.get("produce", {}).get(produce_type, []):
            name = item["name"].lower()
            index[name] = item
            
            # Add common plural forms
            if name.endswith("y") and not name.endswith(("ay", "ey", "oy", "uy")):
                index[name[:-1] + "ies"] = item  # cherry -> cherries, blackberry -> blackberries
            elif name.endswith("o"):
                index[name + "es"] = item  # tomato -> tomatoes, potato -> potatoes
                index[name + "s"] = item   # also "tomatos" just in case
            elif name.endswith(("s", "sh", "ch", "x", "z")):
                index[name + "es"] = item  # watercress -> watercresses
            else:
                index[name + "s"] = item   # pear -> pears, carrot -> carrots
    
    return index


# Pre-built index for fast O(1) lookups instead of O(n) substring scanning
_SEASONAL_INDEX = _build_seasonal_index(SEASONAL_DATA)

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

    def _parse_iso8601_duration(self, duration_str: str) -> float:
        """
        Parse ISO 8601 duration format (e.g., PT30M, PT1H30M, PT1H, PT45S).
        
        Args:
            duration_str: ISO 8601 duration string starting with PT
            
        Returns:
            Duration in minutes (float)
        """
        import re
        
        total_minutes = 0.0
        duration_str = duration_str.upper()
        
        # Remove the PT prefix
        if duration_str.startswith("PT"):
            duration_str = duration_str[2:]
        
        # Parse hours
        hours_match = re.search(r'(\d+(?:\.\d+)?)H', duration_str)
        if hours_match:
            total_minutes += float(hours_match.group(1)) * 60
        
        # Parse minutes
        minutes_match = re.search(r'(\d+(?:\.\d+)?)M', duration_str)
        if minutes_match:
            total_minutes += float(minutes_match.group(1))
        
        # Parse seconds
        seconds_match = re.search(r'(\d+(?:\.\d+)?)S', duration_str)
        if seconds_match:
            total_minutes += float(seconds_match.group(1)) / 60
        
        logger.debug(f"Parsed ISO 8601 duration '{duration_str}' to {total_minutes} minutes")
        return total_minutes

    @staticmethod
    def _match_seasonal_item(ingredient_name: str) -> Optional[dict]:
        """
        Match an ingredient name against the seasonal index using n-gram lookup.
        
        Tries all contiguous sub-phrases by decreasing length for best precision:
          "red bell pepper"   -> "red bell pepper", "red bell", "bell pepper", "red", "bell", "pepper"
          "pomegranate seeds" -> "pomegranate seeds", "pomegranate", "seeds"
          "strawberries"      -> direct lookup (plural pre-indexed)
        
        Returns the matched seasonal item dict, or None.
        """
        words = ingredient_name.lower().split()
        n = len(words)
        # Try sub-phrases from longest to shortest.
        # At equal length, try from the END first since the head noun
        # is usually last in English ("cherry tomatoes" -> "tomatoes").
        for length in range(n, 0, -1):
            for start in range(n - length, -1, -1):
                candidate = " ".join(words[start:start + length])
                if candidate in _SEASONAL_INDEX:
                    return _SEASONAL_INDEX[candidate]
        return None

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

    # ── DAG-based time calculation ─────────────────────────────────────

    def _calculate_times_from_dag(
        self, recipe_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate recipe times using the critical path through the step DAG.

        Instead of naively summing all step durations, we:
        1. Build a dependency graph from uses/produces/requires relationships.
        2. Parse each step's duration to minutes.
        3. Compute the critical path (longest path through the DAG) to get
           the real wall-clock time (totalTime).
        4. Separate active vs passive time along that critical path.
        5. Sum all active durations regardless of path (activeTime).

        Returns a dict with ISO 8601 strings:
            totalTime        – wall-clock time (critical path)
            totalActiveTime  – sum of non-passive durations on critical path
            totalPassiveTime – sum of passive durations on critical path
        """
        steps = recipe_data.get("steps", [])
        recipe_title = recipe_data.get("metadata", {}).get("title", "?")

        if not steps or not isinstance(steps, list):
            logger.warning(f"No steps list found for '{recipe_title}', falling back to linear sum")
            return self._calculate_times_linear_fallback(recipe_data)

        # ── 1. Parse durations & build lookup ──────────────────────────
        step_by_id: Dict[str, Dict] = {}
        duration_min: Dict[str, float] = {}
        is_passive: Dict[str, bool] = {}

        # Minimum duration fallback for steps without an explicit duration.
        # Prep/combine/cook steps always take *some* time; 5min is a conservative
        # floor that prevents the critical path from collapsing to near-zero
        # when the LLM forgets to estimate durations on prep steps.
        _FALLBACK_DURATION_MIN = 5.0
        # Equipment-only steps (preheat oven) get a shorter fallback
        _EQUIPMENT_KEYWORDS = {"preheat", "préchauffer", "allumer", "préparer le four"}

        for step in steps:
            sid = step.get("id", "")
            step_by_id[sid] = step
            dur_str = step.get("duration") or step.get("time")
            if dur_str:
                duration_min[sid] = self._parse_time_to_minutes(dur_str)
            else:
                # Apply fallback: equipment steps get 0, others get 5min
                action_lower = step.get("action", "").lower()
                is_equipment = any(kw in action_lower for kw in _EQUIPMENT_KEYWORDS)
                duration_min[sid] = 0.0 if is_equipment else _FALLBACK_DURATION_MIN
            is_passive[sid] = bool(step.get("isPassive", False))

        # ── 2. Build adjacency: predecessor → successors ───────────────
        # A step S depends on:
        #   - the step that `produces` any state listed in S.uses
        #   - the step that `produces` any state listed in S.requires
        # Additionally, steps are implicitly ordered: step[i] depends on step[i-1]
        # if it hasn't already been linked via produces/uses.

        # Map produced state → step id
        state_producer: Dict[str, str] = {}
        for step in steps:
            prod = step.get("produces", "")
            if prod:
                state_producer[prod] = step["id"]

        # Ingredients are implicit sources (no predecessor step)
        ingredient_ids = {ing.get("id", "") for ing in recipe_data.get("ingredients", [])}

        # Build predecessors for each step
        predecessors: Dict[str, set] = {s["id"]: set() for s in steps}
        for step in steps:
            sid = step["id"]
            refs = list(step.get("uses", [])) + list(step.get("requires", []))
            for ref in refs:
                if ref in ingredient_ids:
                    continue  # ingredients have no predecessor step
                if ref in state_producer:
                    pred_id = state_producer[ref]
                    if pred_id != sid:
                        predecessors[sid].add(pred_id)

        # ── 3. Critical path via dynamic programming ───────────────────
        # earliest_finish[sid] = max(earliest_finish[pred] for pred in preds) + duration[sid]
        # Process in topological order (steps list is already topologically sorted by design)

        earliest_finish: Dict[str, float] = {}
        # Track the critical predecessor for path reconstruction
        critical_pred: Dict[str, Optional[str]] = {}

        for step in steps:
            sid = step["id"]
            # Find the latest finishing predecessor
            max_pred_finish = 0.0
            best_pred = None
            for pred in predecessors[sid]:
                pf = earliest_finish.get(pred, 0.0)
                if pf > max_pred_finish:
                    max_pred_finish = pf
                    best_pred = pred

            earliest_finish[sid] = max_pred_finish + duration_min[sid]
            critical_pred[sid] = best_pred

        # ── 4. Find the critical path end ──────────────────────────────
        final_state = recipe_data.get("finalState", "")
        if final_state and final_state in state_producer:
            critical_end = state_producer[final_state]
        else:
            # Fallback: step with largest earliest_finish
            critical_end = max(earliest_finish, key=earliest_finish.get) if earliest_finish else None

        total_time_min = earliest_finish.get(critical_end, 0.0) if critical_end else 0.0

        # ── 5. Walk back the critical path for active/passive split ────
        critical_path_active = 0.0
        critical_path_passive = 0.0
        path_ids = []

        current = critical_end
        while current:
            path_ids.append(current)
            dur = duration_min.get(current, 0.0)
            if is_passive.get(current, False):
                critical_path_passive += dur
            else:
                critical_path_active += dur
            current = critical_pred.get(current)

        path_ids.reverse()

        # ── 6. Log the result ──────────────────────────────────────────
        # Also compute linear sum for comparison
        linear_total = sum(duration_min.values())
        linear_active = sum(d for sid, d in duration_min.items() if not is_passive.get(sid, False))

        logger.info(
            f"[{recipe_title}] DAG critical path: {total_time_min:.0f}min "
            f"(active={critical_path_active:.0f}min + passive={critical_path_passive:.0f}min) | "
            f"Linear sum would be: {linear_total:.0f}min | "
            f"Path: {' → '.join(path_ids)}"
        )

        return {
            "totalTime": self._minutes_to_iso8601(total_time_min),
            "totalActiveTime": self._minutes_to_iso8601(critical_path_active),
            "totalPassiveTime": self._minutes_to_iso8601(critical_path_passive),
            # Keep float versions for backward compat / easy display
            "totalTimeMinutes": round(total_time_min, 1),
            "totalActiveTimeMinutes": round(critical_path_active, 1),
            "totalPassiveTimeMinutes": round(critical_path_passive, 1),
        }

    def _minutes_to_iso8601(self, minutes: float) -> str:
        """Convert minutes to ISO 8601 duration string (e.g. PT1H30M)."""
        if minutes <= 0:
            return "PT0M"
        total_min = round(minutes)
        hours = total_min // 60
        mins = total_min % 60
        if hours and mins:
            return f"PT{hours}H{mins}M"
        elif hours:
            return f"PT{hours}H"
        else:
            return f"PT{mins}M"

    def _calculate_times_linear_fallback(
        self, recipe_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback for recipes without a proper DAG.
        Simply sums all step durations linearly.
        """
        total_minutes = 0.0
        active_minutes = 0.0

        steps = recipe_data.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                time_str = step.get("duration") or step.get("time")
                if time_str:
                    mins = self._parse_time_to_minutes(time_str)
                    total_minutes += mins
                    is_pass = step.get("isPassive", False) or step.get("stepMode") == "passive"
                    if not is_pass:
                        active_minutes += mins

        passive_minutes = total_minutes - active_minutes
        return {
            "totalTime": self._minutes_to_iso8601(total_minutes),
            "totalActiveTime": self._minutes_to_iso8601(active_minutes),
            "totalPassiveTime": self._minutes_to_iso8601(passive_minutes),
            "totalTimeMinutes": round(total_minutes, 1),
            "totalActiveTimeMinutes": round(active_minutes, 1),
            "totalPassiveTimeMinutes": round(passive_minutes, 1),
        }
        
    def _parse_time_to_minutes(self, time_str: str) -> float:
        """
        Convertit une chaîne de temps en minutes.
        
        Supporte les formats:
        - ISO 8601: "PT30M", "PT1H30M", "PT1H", "PT45S"
        - Legacy: "1h30min", "5min", "1hour", "30 minutes"
        
        Args:
            time_str: La chaîne de temps à convertir
            
        Returns:
            Le temps en minutes (float)
        """
        if not time_str:
            return 0.0
        
        # Convertir en chaîne et mettre en minuscules pour normaliser
        time_str = str(time_str).strip()
        original_str = time_str
        
        # Check for ISO 8601 duration format (PT...)
        if time_str.upper().startswith("PT"):
            return self._parse_iso8601_duration(time_str)
        
        # Legacy format parsing
        time_str = time_str.lower()
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

    # _calculate_total_cooking_time removed — replaced by _calculate_times_from_dag above

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
            # Prefer English name (name_en) for matching against SEASONAL_DATA
            name_en = ingredient.get("name_en", "").lower()
            name_fr = ingredient.get("name", "").lower()
            name = name_en if name_en else name_fr
            display_name = f"{name_fr} ({name_en})" if name_en and name_en != name_fr else name_fr
            category = ingredient.get("category", "").lower()
            
            # Skip if not a produce ingredient
            if not name or category != "produce":
                continue
                
            # Look up ingredient in the seasonal index
            # Strategy: try longest n-gram first (e.g. "green bell pepper")
            # then shorter ones ("bell pepper", "pepper") for best match.
            item = self._match_seasonal_item(name)
            
            if item is None:
                continue
            
            item_name = item["name"].lower()
            
            # Skip year-round staples (available via import/storage)
            if item_name in YEAR_ROUND_STAPLES:
                logger.debug(f"Skipping year-round staple '{display_name}' ({item_name})")
                continue
            
            peak_months = set(item.get("peak_months", []))
            if not peak_months:
                continue
            
            # Skip year-round ingredients (12 months)
            if len(peak_months) >= 12:
                logger.debug(f"Skipping year-round ingredient '{display_name}' ({item_name})")
                continue
            
            # Calculate the seasons for this ingredient
            seasons = set(self._determine_seasons_from_months(peak_months))
            
            matched_ingredients.append(display_name)
            ingredient_seasons[display_name] = seasons
            all_peak_months.update(peak_months)
            logger.debug(f"Matched '{display_name}' -> '{item_name}', seasons: {seasons}")
        
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
                
        # If no common seasons (empty intersection), use majority vote.
        # Each ingredient "votes" for its seasons; we keep seasons that appear
        # in at least half of the matched ingredients. This avoids a single
        # off-season ingredient overriding five in-season ones.
        if not common_seasons:
            logger.debug("No common seasons found across all ingredients, using majority vote")
            season_votes: Dict[str, int] = {}
            for name, seasons in ingredient_seasons.items():
                for s in seasons:
                    season_votes[s] = season_votes.get(s, 0) + 1
            
            threshold = len(ingredient_seasons) / 2
            common_seasons = {s for s, count in season_votes.items() if count >= threshold}
            
            # If still empty (very unlikely), fall back to all votes
            if not common_seasons:
                common_seasons = set(season_votes.keys())
            
            logger.info(
                f"Majority vote results (threshold={threshold:.1f}): "
                f"{', '.join(f'{s}={c}' for s, c in sorted(season_votes.items()))} "
                f"-> selected: {common_seasons}"
            )
        else:
            logger.info(f"Found common seasons across all ingredients: {common_seasons}")
        
        # Convert back to list and sort
        # If all 4 seasons are covered, simplify to "all"
        if common_seasons and len(common_seasons) >= 4:
            seasons_list = ["all"]
        else:
            seasons_list = sorted(list(common_seasons)) if common_seasons else ["all"]
            
        # Filter peak months to keep only those matching the determined seasons
        # This prevents having "all year" peak months when the recipe is seasonally constrained
        final_peak_months = set()
        month_to_season = {
            "December": "winter", "January": "winter", "February": "winter",
            "March": "spring", "April": "spring", "May": "spring",
            "June": "summer", "July": "summer", "August": "summer",
            "September": "autumn", "October": "autumn", "November": "autumn"
        }
        
        for month in all_peak_months:
            season = month_to_season.get(month)
            if season and (season in common_seasons or "all" in seasons_list):
                final_peak_months.add(month)
                
        peak_months_list = sorted(list(final_peak_months))
        
        return seasons_list, peak_months_list

    # Curated diet classification lists (lazy-loaded)
    _diet_lists: Optional[Dict[str, List[str]]] = None
    _DIET_CLASSIFICATION_PATH = Path(__file__).parent / "data" / "diet_classification.json"

    @classmethod
    def _get_diet_lists(cls) -> Dict[str, List[str]]:
        """Lazy-load the curated diet classification lists."""
        if cls._diet_lists is None:
            if cls._DIET_CLASSIFICATION_PATH.exists():
                with open(cls._DIET_CLASSIFICATION_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cls._diet_lists = {
                    k: v for k, v in data.items() if not k.startswith("_")
                }
                logger.info(
                    f"Loaded diet classification lists: "
                    f"{', '.join(f'{k}({len(v)})' for k, v in cls._diet_lists.items())}"
                )
            else:
                cls._diet_lists = {}
                logger.warning("diet_classification.json not found, using category fallback only")
        return cls._diet_lists

    def _determine_diets(self, recipe_json: Dict[str, Any]) -> List[str]:
        """
        Determine the diets based on ingredient names (curated lists)
        with LLM category as fallback.

        Strategy:
        1. Match each ingredient's name_en against curated word lists
           (meat, seafood, dairy, egg, non_vegan_other)
        2. Fall back to the LLM-assigned category field only when
           no curated match is found
        3. Optional ingredients do not exclude a diet (they are noted separately)

        Args:
            recipe_json: The recipe data to analyze

        Returns:
            A list of applicable diets (most restrictive first)
        """
        import re as _re

        diet_lists = self._get_diet_lists()

        has_meat = False
        has_seafood = False
        has_dairy = False
        has_egg = False
        has_non_vegan_other = False

        ingredients = recipe_json.get("ingredients", [])
        logger.debug(f"Analyzing {len(ingredients)} ingredients for diet determination")

        meat_ingredients = []
        seafood_ingredients = []
        dairy_ingredients = []
        egg_ingredients = []
        non_vegan_ingredients = []

        def _matches_list(name_lower: str, items: List[str]) -> bool:
            """Check if name matches any item via word-boundary matching."""
            for item in sorted(items, key=len, reverse=True):
                if _re.search(rf'\b{_re.escape(item)}\b', name_lower):
                    return True
            return False

        for ingredient in ingredients:
            name_en = (ingredient.get("name_en") or "").lower().strip()
            name = (ingredient.get("name") or "").lower().strip()
            category = (ingredient.get("category") or "").lower()
            is_optional = ingredient.get("optional", False)

            if not name_en and not name:
                continue

            # Try curated lists first (name_en is preferred)
            check_name = name_en or name
            matched = False

            if diet_lists.get("meat") and _matches_list(check_name, diet_lists["meat"]):
                if not is_optional:
                    has_meat = True
                meat_ingredients.append(check_name)
                matched = True
            elif diet_lists.get("seafood") and _matches_list(check_name, diet_lists["seafood"]):
                if not is_optional:
                    has_seafood = True
                seafood_ingredients.append(check_name)
                matched = True
            elif diet_lists.get("dairy") and _matches_list(check_name, diet_lists["dairy"]):
                if not is_optional:
                    has_dairy = True
                dairy_ingredients.append(check_name)
                matched = True
            elif diet_lists.get("egg") and _matches_list(check_name, diet_lists["egg"]):
                if not is_optional:
                    has_egg = True
                egg_ingredients.append(check_name)
                matched = True
            elif diet_lists.get("non_vegan_other") and _matches_list(check_name, diet_lists["non_vegan_other"]):
                if not is_optional:
                    has_non_vegan_other = True
                non_vegan_ingredients.append(check_name)
                matched = True

            # Fallback: use LLM-assigned category if curated list didn't match
            if not matched and category:
                if category in ("meat", "poultry"):
                    if not is_optional:
                        has_meat = True
                    meat_ingredients.append(f"{check_name} (category:{category})")
                elif category == "seafood":
                    if not is_optional:
                        has_seafood = True
                    seafood_ingredients.append(f"{check_name} (category:{category})")
                elif category == "dairy":
                    if not is_optional:
                        has_dairy = True
                    dairy_ingredients.append(f"{check_name} (category:{category})")
                elif category == "egg":
                    if not is_optional:
                        has_egg = True
                    egg_ingredients.append(f"{check_name} (category:{category})")

        # Log findings
        if meat_ingredients:
            logger.debug(f"Meat ingredients: {', '.join(meat_ingredients)}")
        if seafood_ingredients:
            logger.debug(f"Seafood ingredients: {', '.join(seafood_ingredients)}")
        if dairy_ingredients:
            logger.debug(f"Dairy ingredients: {', '.join(dairy_ingredients)}")
        if egg_ingredients:
            logger.debug(f"Egg ingredients: {', '.join(egg_ingredients)}")
        if non_vegan_ingredients:
            logger.debug(f"Non-vegan other: {', '.join(non_vegan_ingredients)}")

        # Determine diets
        diets: List[str] = []
        if has_meat or has_seafood:
            diets = ["omnivorous"]
            logger.info("Recipe classified as: omnivorous")
        elif has_dairy or has_egg or has_non_vegan_other:
            diets = ["vegetarian", "omnivorous"]
            logger.info("Recipe classified as: vegetarian (and omnivorous)")
        else:
            diets = ["vegan", "vegetarian", "omnivorous"]
            logger.info("Recipe classified as: vegan (and vegetarian, omnivorous)")

        # Pescatarian: seafood but no meat
        if not has_meat and has_seafood:
            diets.append("pescatarian")
            logger.info("Recipe also classified as: pescatarian")

        return diets

    @staticmethod
    def _sanitize_types(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce fields to their expected types.

        Fixes common LLM output issues:
        - servings as string ("30 cl", "null", "Not specified") -> int
        - ingredient quantity as string ("1 to 2", "12 à 16") -> float (midpoint)
        """
        import re as _re

        metadata = recipe_data.get("metadata", {})

        # ── Fix servings ─────────────────────────────────────────────
        servings = metadata.get("servings")
        if servings is not None and not isinstance(servings, (int, float)):
            original = servings
            # Try to extract a number from the string
            match = _re.search(r"(\d+)", str(servings))
            if match:
                metadata["servings"] = int(match.group(1))
            else:
                metadata["servings"] = 1
            logger.warning(
                f"[Sanitize] servings coerced: {repr(original)} -> {metadata['servings']}"
            )

        # ── Fix ingredient quantities ────────────────────────────────
        for ing in recipe_data.get("ingredients", []):
            qty = ing.get("quantity")
            if qty is not None and not isinstance(qty, (int, float)):
                original = qty
                qty_str = str(qty)
                # Handle range strings: "1 to 2", "12 à 16", "1-2"
                range_match = _re.search(
                    r"(\d+(?:[.,]\d+)?)\s*(?:to|à|a|-)\s*(\d+(?:[.,]\d+)?)",
                    qty_str,
                )
                if range_match:
                    lo = float(range_match.group(1).replace(",", "."))
                    hi = float(range_match.group(2).replace(",", "."))
                    ing["quantity"] = round((lo + hi) / 2, 1)
                else:
                    # Try plain number extraction
                    num_match = _re.search(r"(\d+(?:[.,]\d+)?)", qty_str)
                    if num_match:
                        ing["quantity"] = float(num_match.group(1).replace(",", "."))
                    else:
                        ing["quantity"] = None
                logger.warning(
                    f"[Sanitize] ingredient '{ing.get('name', '?')}' quantity coerced: "
                    f"{repr(original)} -> {ing['quantity']}"
                )

        return recipe_data

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
        
        # Sanitize types before any processing
        self._sanitize_types(enriched_recipe)
        
        # ── Diets (independent) ──────────────────────────────────────────
        diets: List[str] = []
        try:
            logger.debug("Determining applicable diets...")
            diets = self._determine_diets(recipe_data)
            logger.debug(f"Diet analysis complete: {', '.join(diets)}")
        except Exception as exc:
            logger.error(f"[Enrichment] Diet detection failed: {exc}", exc_info=True)
        
        # ── Seasons (independent) ────────────────────────────────────────
        seasons: List[str] = ["all"]
        peak_months: List[int] = []
        try:
            logger.debug("Determining seasonal availability...")
            seasons, peak_months = self._determine_seasons(recipe_data)
            logger.debug(f"Season analysis complete: {', '.join(seasons)}")
        except Exception as exc:
            logger.error(f"[Enrichment] Season detection failed: {exc}", exc_info=True)
        
        # ── DAG times (independent) ──────────────────────────────────────
        _EMPTY_TIMES = {
            "totalTime": "PT0M", "totalActiveTime": "PT0M", "totalPassiveTime": "PT0M",
            "totalTimeMinutes": 0.0, "totalActiveTimeMinutes": 0.0, "totalPassiveTimeMinutes": 0.0,
        }
        time_info = _EMPTY_TIMES.copy()
        try:
            logger.debug("Calculating times from step DAG (critical path)...")
            time_info = self._calculate_times_from_dag(recipe_data)
            logger.debug(
                f"DAG time calculation complete: total={time_info['totalTime']} "
                f"active={time_info['totalActiveTime']} passive={time_info['totalPassiveTime']}"
            )

            # Cross-check with schema.org times if available
            schema_data = recipe_data.get("metadata", {}).get("_schema_data")
            if schema_data:
                schema_total = schema_data.get("totalTime")
                if schema_total:
                    schema_minutes = self._parse_time_to_minutes(schema_total)
                    dag_minutes = time_info.get("totalTimeMinutes", 0)
                    if schema_minutes > 0 and dag_minutes > 0:
                        divergence = abs(dag_minutes - schema_minutes) / schema_minutes
                        if divergence > 0.3:
                            logger.warning(
                                f"[Time divergence] DAG={dag_minutes:.0f}min vs "
                                f"schema.org={schema_minutes:.0f}min ({divergence:.0%} off). "
                                f"Using schema.org totalTime as ground truth."
                            )
                            time_info["totalTime"] = schema_total
                            time_info["totalTimeMinutes"] = schema_minutes
                # Also use schema.org prepTime/cookTime if they exist and DAG lacks detail
                for schema_field, meta_field in [
                    ("prepTime", "prepTime"),
                    ("cookTime", "cookTime"),
                ]:
                    val = schema_data.get(schema_field)
                    if val:
                        enriched_recipe["metadata"][meta_field] = val
        except Exception as exc:
            logger.error(f"[Enrichment] DAG time calculation failed: {exc}", exc_info=True)
        
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
        # DAG-computed times (ISO 8601)
        enriched_recipe["metadata"]["totalTime"] = time_info["totalTime"]
        enriched_recipe["metadata"]["totalActiveTime"] = time_info["totalActiveTime"]
        enriched_recipe["metadata"]["totalPassiveTime"] = time_info["totalPassiveTime"]
        # Convenience: float minutes for easy frontend display
        enriched_recipe["metadata"]["totalTimeMinutes"] = time_info["totalTimeMinutes"]
        enriched_recipe["metadata"]["totalActiveTimeMinutes"] = time_info["totalActiveTimeMinutes"]
        enriched_recipe["metadata"]["totalPassiveTimeMinutes"] = time_info["totalPassiveTimeMinutes"]
        # Remove legacy field if present
        enriched_recipe["metadata"].pop("totalCookingTime", None)
        
        logger.info(
            f"Recipe \"{recipe_title}\" enriched with: {', '.join(diets)} diets, "
            f"{', '.join(seasons)} seasons, DAG times: {time_info['totalTime']} total "
            f"({time_info['totalActiveTime']} active + {time_info['totalPassiveTime']} passive)"
        )
        
        return enriched_recipe

    # ── LLM weight estimation fallback ─────────────────────────────────

    _WEIGHT_CACHE_PATH = Path(__file__).parent / "data" / "weight_estimates_cache.json"

    def _load_weight_cache(self) -> Dict[str, float]:
        """Load the LLM weight-estimate cache from disk."""
        if not hasattr(self, '_weight_cache'):
            if self._WEIGHT_CACHE_PATH.exists():
                try:
                    with open(self._WEIGHT_CACHE_PATH) as f:
                        data = json.load(f)
                    self._weight_cache = {
                        k: v for k, v in data.items() if not k.startswith("_")
                    }
                    logger.debug(f"Loaded {len(self._weight_cache)} weight estimates from cache")
                except (json.JSONDecodeError, OSError):
                    self._weight_cache = {}
            else:
                self._weight_cache = {}
        return self._weight_cache

    def _save_weight_cache(self) -> None:
        """Persist weight-estimate cache to disk."""
        cache = self._load_weight_cache()
        data = {
            "_meta": {
                "description": "LLM-estimated weight per unit for ingredients (grams).",
                "format": "cache_key → grams_per_unit. Key = 'unit|ingredient_en' or 'none|ingredient_en'.",
            }
        }
        data.update(dict(sorted(cache.items())))
        self._WEIGHT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self._WEIGHT_CACHE_PATH, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _weight_cache_key(unit: Optional[str], name_en: str) -> str:
        """
        Build a normalized cache key for weight estimation.

        Uses the canonical unit form (via NutritionMatcher._normalize_unit)
        so that 'packets|yeast' and 'packet|yeast' resolve to the same key.
        """
        from .services.nutrition_matcher import NutritionMatcher

        if unit:
            normalized = NutritionMatcher._normalize_unit(unit)
        else:
            normalized = "none"
        return f"{normalized}|{name_en.lower().strip()}"

    async def _fill_missing_weights_llm(
        self,
        ingredients: List[Dict[str, Any]],
        nutrition_data: Dict[str, Any],
    ) -> None:
        """
        For ingredients where estimate_grams returns None, ask an LLM to
        estimate the weight per unit and cache the result.

        Mutates ingredient dicts in place: adds 'estimatedWeightGrams' field.
        """
        from .services.nutrition_matcher import NutritionMatcher

        cache = self._load_weight_cache()
        to_ask: List[Dict[str, Any]] = []  # ingredients needing LLM

        for ing in ingredients:
            name_en = ing.get("name_en", "")
            if not name_en:
                continue

            key = name_en.strip().lower()
            nut = nutrition_data.get(key)
            if not nut or nut.get("not_found"):
                continue  # no nutrition data anyway

            qty = ing.get("quantity")
            unit = ing.get("unit")
            grams = NutritionMatcher.estimate_grams(qty, unit, name_en)
            if grams is not None:
                continue  # static lookup worked

            if qty is None:
                continue  # nothing to estimate

            # Check cache
            ck = self._weight_cache_key(unit, name_en)
            if ck in cache:
                ing["estimatedWeightGrams"] = qty * cache[ck]
                logger.debug(f"Weight cache hit: '{ck}' → {cache[ck]}g/unit")
                continue

            to_ask.append(ing)

        if not to_ask:
            return

        # Batch LLM call
        logger.info(f"Estimating weights via LLM for {len(to_ask)} unresolved ingredients...")
        lines = []
        for ing in to_ask:
            q = ing.get("quantity", 1)
            u = ing.get("unit") or "piece"
            n = ing.get("name_en", "")
            lines.append(f"{q} {u} {n}")

        estimates = await self._batch_estimate_weights_llm(lines)

        for ing, est_grams in zip(to_ask, estimates):
            if est_grams is None or est_grams <= 0:
                continue
            # Sanity bounds: no single ingredient exceeds 2kg in a typical recipe
            if est_grams > 2_000:
                logger.warning(
                    f"LLM weight estimate {est_grams}g for "
                    f"'{ing.get('name_en')}' exceeds 2kg — ignoring"
                )
                continue

            qty = ing.get("quantity", 1) or 1  # guard against qty=0
            unit = ing.get("unit")
            name_en = ing.get("name_en", "")

            per_unit = est_grams / qty
            ck = self._weight_cache_key(unit, name_en)
            cache[ck] = round(per_unit, 1)

            ing["estimatedWeightGrams"] = round(est_grams, 1)
            logger.info(f"LLM weight: '{ck}' → {per_unit:.1f}g/unit (total {est_grams:.1f}g)")

        self._save_weight_cache()

    def _get_weight_llm_client(self):
        """Lazy-initialize and cache the OpenRouter client for weight estimation."""
        if not hasattr(self, '_weight_llm_client') or self._weight_llm_client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                return None
            from openai import AsyncOpenAI
            self._weight_llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/recipe-display",
                    "X-Title": "Weight Estimator",
                },
            )
        return self._weight_llm_client

    async def _batch_estimate_weights_llm(self, lines: List[str]) -> List[Optional[float]]:
        """
        Ask an LLM to estimate total weight in grams for each ingredient line.

        Args:
            lines: e.g. ["1 handful basil leaves", "2 small cloves garlic"]

        Returns:
            List of estimated grams (same order), or None for failures.
        """
        import re as _re

        client = self._get_weight_llm_client()
        if client is None:
            logger.warning("No OpenRouter API key — skipping LLM weight estimation")
            return [None] * len(lines)

        numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
        prompt = f"""Estimate the total weight in grams for each ingredient line.
Reply with ONLY one number per line (the weight in grams), in the same order.
Use common culinary knowledge. No units, no text, just the number.

{numbered}"""

        try:
            response = await client.chat.completions.create(
                model="deepseek/deepseek-v3.2",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a culinary expert. Estimate ingredient weights "
                            "in grams. Reply with one number per line, nothing else."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=256,
                temperature=0.0,
                extra_body={
                    "provider": {
                        "sort": "throughput",
                        "allow_fallbacks": True,
                    }
                },
            )

            result_text = response.choices[0].message.content or ""
            result_lines = [l.strip() for l in result_text.strip().split("\n") if l.strip()]

            estimates: List[Optional[float]] = []
            for line in result_lines:
                # Extract first number from line (handles "30g", "30 grams", "30", etc.)
                m = _re.search(r"[\d.]+", line)
                estimates.append(float(m.group()) if m else None)

            # Pad to match input length
            while len(estimates) < len(lines):
                estimates.append(None)
            return estimates[:len(lines)]

        except Exception as e:
            logger.error(f"LLM weight estimation failed: {e}")
            return [None] * len(lines)

    @observe(name="enrich_recipe")
    async def enrich_recipe_async(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a recipe with ALL information including nutrition (async).
        
        This extends enrich_recipe() by adding:
        - Ingredient translation (name_en)
        - Nutritional profile per serving (via OpenNutrition embeddings)
        - Nutrition tags (high-protein, low-calorie, etc.)
        
        Args:
            recipe_data: The recipe data to enrich
            
        Returns:
            The enriched recipe data with nutrition info
        """
        # First, run the synchronous enrichment (diets, seasons, time)
        # Each sub-step is already isolated inside enrich_recipe().
        enriched = self.enrich_recipe(recipe_data)
        
        recipe_title = enriched.get("metadata", {}).get("title", "Untitled recipe")

        ingredients = enriched.get("ingredients", [])
        if not ingredients:
            logger.warning(f"No ingredients to enrich for \"{recipe_title}\"")
            return enriched

        # ── Translation + Nutrition (independent from diets/seasons/times) ──
        try:
            logger.info(f"Starting async nutrition enrichment for \"{recipe_title}\"")

            from .services.ingredient_translator import IngredientTranslator
            from .services.nutrition_matcher import NutritionMatcher

            translator = IngredientTranslator()

            if not hasattr(self, '_nutrition_matcher'):
                self._nutrition_matcher = NutritionMatcher()
            matcher = self._nutrition_matcher

            # Step 1: Translate ingredient names to English
            logger.info(f"Translating {len(ingredients)} ingredients to English...")
            translated = await translator.translate_ingredients(ingredients)

            for i, (ing, name_en) in enumerate(translated):
                enriched["ingredients"][i]["name_en"] = name_en

            # Step 1b + Step 2: Run seasons re-analysis and nutrition matching in parallel
            names_en = [name_en for _, name_en in translated if name_en]

            import asyncio as _aio

            async def _seasons_task():
                return self._determine_seasons(enriched)

            async def _nutrition_task():
                loop = _aio.get_running_loop()
                return await loop.run_in_executor(None, matcher.match_batch, names_en)

            logger.info(f"Running seasons + nutrition matching in parallel ({len(names_en)} ingredients)...")
            (seasons_peak, nutrition_data) = await _aio.gather(
                _seasons_task(),
                _nutrition_task(),
            )
            seasons, peak_months = seasons_peak

            enriched["metadata"]["seasons"] = seasons
            if peak_months:
                enriched["metadata"]["peakMonths"] = peak_months
            logger.info(f"Season re-analysis with English names: {', '.join(seasons)}")

            # Step 2b: LLM weight estimation for ingredients the static lookup can't resolve
            await self._fill_missing_weights_llm(enriched["ingredients"], nutrition_data)

            # Step 3: Compute per-serving nutrition profile
            servings = enriched.get("metadata", {}).get("servings", 1)
            metadata = enriched.get("metadata", {})
            profile = self._compute_nutrition_profile(
                enriched["ingredients"], nutrition_data, servings, metadata
            )

            nutrition_issues = profile.pop("issues", [])
            enriched["metadata"]["nutritionPerServing"] = profile
            if nutrition_issues:
                enriched["metadata"]["nutritionIssues"] = nutrition_issues

            # Step 4: Derive nutrition tags
            tags = self._derive_nutrition_tags(profile)
            enriched["metadata"]["nutritionTags"] = tags

            # Step 5: Sanity-check servings vs calories
            # Two tiers: moderate threshold (triggers only for small servings)
            # and extreme threshold (triggers regardless of servings count).
            cal_per_serving = profile.get("calories", 0)
            current_servings = enriched["metadata"].get("servings", 1)
            recipe_type = enriched.get("metadata", {}).get("recipeType", "")
            kcal_threshold = 2000 if recipe_type == "main_course" else 1500
            _EXTREME_THRESHOLD = 3000
            _MAX_MULTIPLIER = 4

            needs_fix = (
                isinstance(current_servings, (int, float))
                and (
                    (current_servings <= 2 and cal_per_serving > kcal_threshold)
                    or cal_per_serving > _EXTREME_THRESHOLD
                )
            )

            if needs_fix:
                raw_estimate = round(cal_per_serving * current_servings / 500)
                estimated_servings = min(
                    max(4, raw_estimate),
                    current_servings * _MAX_MULTIPLIER,
                )
                logger.warning(
                    f"[Servings auto-fix] '{recipe_title}': {cal_per_serving:.0f} kcal/serving "
                    f"with servings={current_servings} is suspicious (threshold={kcal_threshold}). "
                    f"Auto-correcting to {estimated_servings} servings."
                )
                enriched["metadata"]["servingsOriginal"] = current_servings
                enriched["metadata"]["servingsSuspect"] = True
                enriched["metadata"]["servings"] = estimated_servings

                ratio = current_servings / estimated_servings
                for macro in ("calories", "protein", "fat", "carbs", "fiber"):
                    if macro in profile:
                        profile[macro] = round(profile[macro] * ratio, 1)
                enriched["metadata"]["nutritionPerServing"] = profile

                tags = self._derive_nutrition_tags(profile)
                enriched["metadata"]["nutritionTags"] = tags

            logger.info(
                f"Nutrition enrichment complete for \"{recipe_title}\": "
                f"{profile.get('calories', 0)} kcal/serving, "
                f"confidence={profile.get('confidence', 'unknown')}, "
                f"tags={tags}"
            )

        except Exception as exc:
            logger.error(
                f"[Enrichment] Nutrition pipeline failed for \"{recipe_title}\": {exc}. "
                f"Recipe will be saved without nutrition data.",
                exc_info=True,
            )

        return enriched

    def _compute_nutrition_profile(
        self,
        ingredients: List[Dict[str, Any]],
        nutrition_data: Dict[str, Optional[Dict[str, Any]]],
        servings: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute per-serving nutritional profile from ingredient nutrition data.

        Applies liquid-retention heuristics for cooking liquids (broth, wine, etc.)
        when their volume exceeds _LIQUID_VOLUME_THRESHOLD_ML.

        Args:
            ingredients: List of ingredient dicts (with name_en).
            nutrition_data: Dict mapping normalized name_en to USDA macros per 100g.
            servings: Number of servings the recipe yields.
            metadata: Recipe metadata (used to detect soup-type recipes).

        Returns:
            Nutrition profile dict with macros per serving + confidence.
        """
        from .services.nutrition_matcher import NutritionMatcher

        # Ingredients with negligible nutritional contribution
        # These are skipped from both lookup and counting
        _ALWAYS_NEGLIGIBLE = {
            # Salt
            "salt", "table salt", "sea salt", "fleur de sel", "coarse salt",
            # Pepper
            "black pepper", "white pepper", "pepper", "peppercorns",
            # Water / ice
            "water", "ice", "ice water", "cold water", "hot water",
            "mineral water", "sparkling water",
            # Leavening agents
            "baking soda", "baking powder",
            # Dried spices (always <5 kcal per typical use)
            "cinnamon", "nutmeg", "paprika", "cumin", "turmeric",
            "cayenne pepper", "chili powder", "curry powder",
            "cloves", "allspice", "cardamom", "coriander seeds",
            "saffron", "star anise", "anise seeds",
            "ras el hanout", "espelette pepper", "hot pepper",
            # Misc negligible
            "food coloring", "vanilla extract",
            "vanilla paste", "vanilla bean", "vanilla sugar",
        }

        # Herbs: negligible in small amounts but significant in cups/bunches
        _HERB_INGREDIENTS = {
            "basil", "basil leaves", "fresh basil",
            "parsley", "fresh parsley", "flat-leaf parsley",
            "cilantro", "fresh cilantro", "coriander leaves",
            "oregano", "fresh oregano",
            "thyme", "fresh thyme", "fresh thyme sprigs",
            "rosemary", "fresh rosemary",
            "chives", "fresh chives",
            "dill", "fresh dill",
            "mint", "fresh mint", "peppermint",
            "tarragon", "fresh tarragon",
            "bay leaf", "fresh bay leaf", "bay leaves",
            "sage", "fresh sage",
            "marjoram", "fresh marjoram",
        }

        # Units that indicate small herb quantities (always negligible)
        _SMALL_HERB_UNITS = {
            "sprig", "sprigs", "leaf", "leaves", "pinch",
            "dash", "tsp", "teaspoon", None,
        }

        def _is_negligible(key: str, ing: dict) -> bool:
            if key in _ALWAYS_NEGLIGIBLE:
                return True
            if key in _HERB_INGREDIENTS:
                unit = (ing.get("unit") or "").strip().lower()
                normalized_unit = NutritionMatcher._normalize_unit(unit) if unit else None
                if normalized_unit in _SMALL_HERB_UNITS or not unit:
                    return True
                # cup, bunch, tbsp = substantial herb → count it
                return False
            return False

        total = {
            "calories": 0.0,
            "protein": 0.0,
            "fat": 0.0,
            "carbs": 0.0,
            "fiber": 0.0,
        }
        resolved_count = 0
        matched_count = 0
        total_count = 0
        negligible_count = 0
        liquid_retention_applied = False
        issues: List[Dict[str, str]] = []

        is_soup = _is_soup_recipe(metadata or {})

        for ing in ingredients:
            name_en = ing.get("name_en", "")
            name_orig = ing.get("name", "")

            if not name_en:
                total_count += 1
                issues.append({
                    "ingredient": name_orig or "?",
                    "issue": "no_translation",
                    "detail": "Missing English name (name_en) — cannot look up nutrition",
                })
                continue

            key = name_en.strip().lower()

            if _is_negligible(key, ing):
                negligible_count += 1
                continue

            total_count += 1

            nut = nutrition_data.get(key)
            if not nut or nut.get("not_found"):
                issues.append({
                    "ingredient": key,
                    "issue": "no_match",
                    "detail": "Not found in OpenNutrition index",
                })
                continue

            matched_count += 1

            grams = ing.get("estimatedWeightGrams")
            if grams is None:
                quantity = ing.get("quantity")
                unit = ing.get("unit")
                grams = NutritionMatcher.estimate_grams(quantity, unit, name_en)

            if grams is None or grams <= 0:
                reason = "no quantity" if ing.get("quantity") is None else "weight estimation failed"
                issues.append({
                    "ingredient": key,
                    "issue": "no_weight",
                    "detail": f"Matched in DB but {reason} — excluded from calorie total",
                })
                continue

            # --- Liquid retention heuristic ---
            retention = 1.0
            liquid_category = _classify_liquid(key, is_soup)
            if liquid_category is not None:
                volume_ml = grams
                threshold = (
                    _FRYING_OIL_THRESHOLD_ML
                    if liquid_category in ("frying_oil", "confit_fat")
                    else _LIQUID_VOLUME_THRESHOLD_ML
                )
                if volume_ml > threshold:
                    retention = _LIQUID_RETENTION_FACTORS.get(liquid_category, 1.0)
                    liquid_retention_applied = True
                    logger.info(
                        f"Liquid retention: '{name_en}' ({volume_ml:.0f}ml) "
                        f"→ category='{liquid_category}', factor={retention:.0%}"
                        f"{' (soup detected)' if is_soup else ''}"
                    )

            factor = (grams / 100.0) * retention
            total["calories"] += (nut.get("energy_kcal", 0) or 0) * factor
            total["protein"] += (nut.get("protein_g", 0) or 0) * factor
            total["fat"] += (nut.get("fat_g", 0) or 0) * factor
            total["carbs"] += (nut.get("carbs_g", 0) or 0) * factor
            total["fiber"] += (nut.get("fiber_g", 0) or 0) * factor

            resolved_count += 1

        # Divide by servings
        if servings and servings > 0:
            for key in total:
                total[key] = round(total[key] / servings, 1)

        # Determine confidence based on resolved (actually computed) ratio
        # "high" = 90%+ resolved → reliable enough for meal planning
        # "medium" = 50-89% → displayed but flagged
        # "low" = <50% → unreliable, not used in meal planner
        if total_count == 0:
            confidence = "none"
        elif resolved_count / total_count >= 0.9:
            confidence = "high"
        elif resolved_count / total_count >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        result = {
            **total,
            "confidence": confidence,
            "resolvedIngredients": resolved_count,
            "matchedIngredients": matched_count,
            "totalIngredients": total_count,
            "negligibleIngredients": negligible_count,
            "source": "OpenNutrition",
        }

        if liquid_retention_applied:
            result["liquidRetentionApplied"] = True

        if issues:
            result["issues"] = issues

        return result

    def _derive_nutrition_tags(self, profile: Dict[str, Any]) -> List[str]:
        """
        Derive qualitative nutrition tags from the nutrition profile.
        
        Args:
            profile: Nutrition profile dict with macros per serving.
            
        Returns:
            List of tag strings.
        """
        tags = []
        
        calories = profile.get("calories", 0)
        protein = profile.get("protein", 0)
        fat = profile.get("fat", 0)
        carbs = profile.get("carbs", 0)
        fiber = profile.get("fiber", 0)
        confidence = profile.get("confidence", "none")
        
        # Only derive tags if we have reasonable confidence
        if confidence in ("none", "low"):
            return []
        
        # High protein: > 25g per serving
        if protein > 25:
            tags.append("high-protein")
        
        # Low calorie: < 400 kcal per serving
        if calories > 0 and calories < 400:
            tags.append("low-calorie")
        
        # High fiber: > 8g per serving
        if fiber > 8:
            tags.append("high-fiber")
        
        # Indulgent: > 700 kcal or > 40g fat per serving
        if calories > 700 or fat > 40:
            tags.append("indulgent")
        
        # Balanced: protein 15-35%, carbs 40-65%, fat 20-35% of calories
        if calories > 0:
            pct_protein = (protein * 4 / calories) * 100
            pct_carbs = (carbs * 4 / calories) * 100
            pct_fat = (fat * 9 / calories) * 100
            
            if (15 <= pct_protein <= 35 and
                40 <= pct_carbs <= 65 and
                20 <= pct_fat <= 35):
                tags.append("balanced")
        
        return tags

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