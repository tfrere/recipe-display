"""
Shared constants and utilities used across recipe_structurer and recipe_scraper.

Centralizes:
  - ISO 8601 duration parsing
  - Equipment keywords
  - Ingredient categories
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# INGREDIENT CATEGORIES (single source of truth)
# ═══════════════════════════════════════════════════════════════════

INGREDIENT_CATEGORIES = (
    "meat", "poultry", "seafood", "produce", "dairy", "egg",
    "grain", "legume", "nuts_seeds", "oil", "herb",
    "pantry", "spice", "condiment", "beverage", "other",
)


# ═══════════════════════════════════════════════════════════════════
# EQUIPMENT KEYWORDS (steps allowed to have empty `uses`)
# ═══════════════════════════════════════════════════════════════════

EQUIPMENT_KEYWORDS = frozenset({
    "preheat", "préchauffer", "allumer", "préparer le four",
})


# ═══════════════════════════════════════════════════════════════════
# ISO 8601 DURATION PARSING
# ═══════════════════════════════════════════════════════════════════

_ISO_RE = re.compile(
    r"^PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$",
    re.IGNORECASE,
)


def parse_iso8601_minutes(duration: Optional[str]) -> Optional[float]:
    """Parse an ISO 8601 duration string to minutes.

    Supports decimals (PT1.5H) and any combination of H, M, S.
    Returns None if the input is None, empty, or not a valid ISO 8601 duration.

    >>> parse_iso8601_minutes("PT1H30M")
    90.0
    >>> parse_iso8601_minutes("PT5M")
    5.0
    >>> parse_iso8601_minutes("PT45S")
    0.75
    >>> parse_iso8601_minutes(None)
    """
    if not duration or not isinstance(duration, str):
        return None

    m = _ISO_RE.match(duration.strip())
    if not m:
        return None

    hours = float(m.group(1) or 0)
    mins = float(m.group(2) or 0)
    secs = float(m.group(3) or 0)
    total = hours * 60 + mins + secs / 60
    return total if total > 0 else 0.0


def minutes_to_iso8601(minutes: float) -> str:
    """Convert minutes to ISO 8601 duration string.

    >>> minutes_to_iso8601(90)
    'PT1H30M'
    >>> minutes_to_iso8601(5)
    'PT5M'
    >>> minutes_to_iso8601(0)
    'PT0M'
    """
    if minutes <= 0:
        return "PT0M"
    h = int(minutes // 60)
    m = int(minutes % 60)
    parts = ["PT"]
    if h:
        parts.append(f"{h}H")
    if m or not h:
        parts.append(f"{m}M")
    return "".join(parts)


def is_valid_iso8601_duration(duration: Optional[str]) -> bool:
    """Check if a string is a valid ISO 8601 duration."""
    if not duration or not isinstance(duration, str):
        return False
    return _ISO_RE.match(duration.strip()) is not None


# ═══════════════════════════════════════════════════════════════════
# TITLE CLEANUP
# ═══════════════════════════════════════════════════════════════════

_TRAILING_PARENS_RE = re.compile(r"\s*\([^)]*\)\s*$")


def clean_title(title: str) -> str:
    """Strip trailing parenthetical from a recipe title.

    Removes content like "(Vegan + GF)", "(en 25 minutes)", "(Sans Gluten)"
    that appears at the end of titles. Does not touch parentheses in the
    middle of a title.

    >>> clean_title("Banana Cream Pie (Vegan + GF)")
    'Banana Cream Pie'
    >>> clean_title("Sauce BBQ maison (en 25 minutes)")
    'Sauce BBQ maison'
    >>> clean_title("Arroz Con Pollo (Cuban Chicken with Rice)")
    'Arroz Con Pollo'
    >>> clean_title("Simple recipe without parens")
    'Simple recipe without parens'
    >>> clean_title("Recipe (mid) title (trailing)")
    'Recipe (mid) title'
    """
    if not title:
        return title
    return _TRAILING_PARENS_RE.sub("", title).strip()
