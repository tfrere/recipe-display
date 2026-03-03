"""Diet classification (vegan, vegetarian, omnivorous, pescatarian)."""

import json
import logging
import re as _re
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_DIET_CLASSIFICATION_PATH = Path(__file__).parent.parent / "data" / "diet_classification.json"

_diet_lists: Optional[Dict[str, List[str]]] = None


def _get_diet_lists() -> Dict[str, List[str]]:
    """Lazy-load the curated diet classification lists."""
    global _diet_lists
    if _diet_lists is None:
        if _DIET_CLASSIFICATION_PATH.exists():
            with open(_DIET_CLASSIFICATION_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            _diet_lists = {k: v for k, v in data.items() if not k.startswith("_")}
            logger.info(
                f"Loaded diet classification lists: "
                f"{', '.join(f'{k}({len(v)})' for k, v in _diet_lists.items())}"
            )
        else:
            _diet_lists = {}
            logger.warning("diet_classification.json not found, using category fallback only")
    return _diet_lists


def _matches_list(name_lower: str, items: List[str]) -> bool:
    """Check if name matches any item via word-boundary matching."""
    for item in sorted(items, key=len, reverse=True):
        if _re.search(rf'\b{_re.escape(item)}\b', name_lower):
            return True
    return False


def determine_diets(recipe_json: Dict[str, Any]) -> List[str]:
    """
    Determine applicable diets based on ingredient names (curated lists)
    with LLM category as fallback.

    Returns a list of applicable diets (most restrictive first).
    """
    diet_lists = _get_diet_lists()

    has_meat = False
    has_seafood = False
    has_dairy = False
    has_egg = False
    has_non_vegan_other = False

    ingredients = recipe_json.get("ingredients", [])

    for ingredient in ingredients:
        name_en = (ingredient.get("name_en") or "").lower().strip()
        name = (ingredient.get("name") or "").lower().strip()
        category = (ingredient.get("category") or "").lower()
        is_optional = ingredient.get("optional", False)

        if not name_en and not name:
            continue

        check_name = name_en or name
        matched = False

        if diet_lists.get("meat") and _matches_list(check_name, diet_lists["meat"]):
            if not is_optional:
                has_meat = True
            matched = True
        elif diet_lists.get("seafood") and _matches_list(check_name, diet_lists["seafood"]):
            if not is_optional:
                has_seafood = True
            matched = True
        elif diet_lists.get("dairy") and _matches_list(check_name, diet_lists["dairy"]):
            if not is_optional:
                has_dairy = True
            matched = True
        elif diet_lists.get("egg") and _matches_list(check_name, diet_lists["egg"]):
            if not is_optional:
                has_egg = True
            matched = True
        elif diet_lists.get("non_vegan_other") and _matches_list(check_name, diet_lists["non_vegan_other"]):
            if not is_optional:
                has_non_vegan_other = True
            matched = True

        if not matched and category:
            if category in ("meat", "poultry"):
                if not is_optional:
                    has_meat = True
            elif category == "seafood":
                if not is_optional:
                    has_seafood = True
            elif category == "dairy":
                if not is_optional:
                    has_dairy = True
            elif category == "egg":
                if not is_optional:
                    has_egg = True

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

    if not has_meat and has_seafood:
        diets.append("pescatarian")
        logger.info("Recipe also classified as: pescatarian")

    return diets
