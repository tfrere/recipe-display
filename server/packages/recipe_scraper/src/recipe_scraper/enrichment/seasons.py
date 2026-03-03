"""Seasonal availability based on produce ingredients (ADEME Impact CO2 data)."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional

logger = logging.getLogger(__name__)

_SEASONAL_DATA_PATH = Path(__file__).parent.parent / "data" / "seasonal_produce.json"


def _load_seasonal_data() -> dict:
    """Load seasonal produce data from JSON file."""
    try:
        with open(_SEASONAL_DATA_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Seasonal data file not found: {_SEASONAL_DATA_PATH}")
        return {"produce": {"vegetables": [], "fruits": []}}


SEASONAL_DATA = _load_seasonal_data()

YEAR_ROUND_STAPLES: Set[str] = set(
    SEASONAL_DATA.get("year_round_staples", [
        "lemon", "lime", "garlic", "onion", "potato", "ginger",
        "shallot", "sweet potato",
    ])
)


def _build_seasonal_index(data: dict) -> Dict[str, dict]:
    """Build a normalized lookup index from SEASONAL_DATA with plural handling."""
    index: Dict[str, dict] = {}
    for produce_type in ["vegetables", "fruits"]:
        for item in data.get("produce", {}).get(produce_type, []):
            name = item["name"].lower()
            index[name] = item
            if name.endswith("y") and not name.endswith(("ay", "ey", "oy", "uy")):
                index[name[:-1] + "ies"] = item
            elif name.endswith("o"):
                index[name + "es"] = item
                index[name + "s"] = item
            elif name.endswith(("s", "sh", "ch", "x", "z")):
                index[name + "es"] = item
            else:
                index[name + "s"] = item
    return index


_SEASONAL_INDEX = _build_seasonal_index(SEASONAL_DATA)

_MONTH_TO_SEASON = {
    "December": "winter", "January": "winter", "February": "winter",
    "March": "spring", "April": "spring", "May": "spring",
    "June": "summer", "July": "summer", "August": "summer",
    "September": "autumn", "October": "autumn", "November": "autumn",
}


def _months_to_seasons(months: Set[str]) -> List[str]:
    """Convert months to seasons."""
    seasons = {_MONTH_TO_SEASON[m] for m in months if m in _MONTH_TO_SEASON}
    return list(seasons) if seasons else ["all"]


def match_seasonal_item(ingredient_name: str) -> Optional[dict]:
    """
    Match an ingredient name against the seasonal index using n-gram lookup.

    Tries all contiguous sub-phrases by decreasing length for best precision.
    """
    words = ingredient_name.lower().split()
    n = len(words)
    for length in range(n, 0, -1):
        for start in range(n - length, -1, -1):
            candidate = " ".join(words[start:start + length])
            if candidate in _SEASONAL_INDEX:
                return _SEASONAL_INDEX[candidate]
    return None


def determine_seasons(recipe_json: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Determine seasons and peak months based on produce ingredients.
    Only seasons common to all relevant produce are returned.

    Returns (seasons, peak_months).
    """
    ingredient_seasons: Dict[str, set] = {}
    all_peak_months: set = set()

    for ingredient in recipe_json.get("ingredients", []):
        name_en = ingredient.get("name_en", "").lower()
        name_orig = ingredient.get("name", "").lower()
        name = name_en if name_en else name_orig
        display_name = f"{name_orig} ({name_en})" if name_en and name_en != name_orig else name_orig
        category = ingredient.get("category", "").lower()

        if not name or category != "produce":
            continue

        item = match_seasonal_item(name)
        if item is None:
            continue

        item_name = item["name"].lower()
        if item_name in YEAR_ROUND_STAPLES:
            continue

        peak_months = set(item.get("peak_months", []))
        if not peak_months or len(peak_months) >= 12:
            continue

        seasons = set(_months_to_seasons(peak_months))
        ingredient_seasons[display_name] = seasons
        all_peak_months.update(peak_months)

    if not ingredient_seasons:
        return ["all"], []

    # Intersection of all ingredient seasons
    common_seasons = None
    for seasons in ingredient_seasons.values():
        common_seasons = seasons if common_seasons is None else common_seasons & seasons

    # Majority vote fallback if intersection is empty
    if not common_seasons:
        season_votes: Dict[str, int] = {}
        for seasons in ingredient_seasons.values():
            for s in seasons:
                season_votes[s] = season_votes.get(s, 0) + 1
        threshold = len(ingredient_seasons) / 2
        common_seasons = {s for s, c in season_votes.items() if c >= threshold}
        if not common_seasons:
            common_seasons = set(season_votes.keys())

    seasons_list = ["all"] if len(common_seasons) >= 4 else sorted(common_seasons)

    final_peak_months = {
        m for m in all_peak_months
        if _MONTH_TO_SEASON.get(m) in common_seasons or "all" in seasons_list
    }

    return seasons_list, sorted(final_peak_months)
