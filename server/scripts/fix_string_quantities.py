"""
Fix string quantity and servings values in recipe JSONs.

Coerces string values to proper types:
  - "null", "", "unspecified", "to taste" → null
  - "4" → 4
  - "~3" → 3
  - "2 to 3" → 2.5
  - "1/2" → 0.5

Usage:
    python -m scripts.fix_string_quantities [--dry-run]
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Union

SERVER_ROOT = Path(__file__).parent.parent
RECIPES_DIR = SERVER_ROOT / "data" / "recipes"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_NULL_VALUES = {"null", "none", "", "unspecified", "to taste", "as needed", "optional"}

_RANGE_RE = re.compile(r"^([\d.]+)\s*(?:to|-|–|—)\s*([\d.]+)$")
_APPROX_RE = re.compile(r"^[~≈≃]?\s*([\d.]+)$")
_FRACTION_RE = re.compile(r"^(\d+)/(\d+)$")
_MIXED_RE = re.compile(r"^(\d+)\s+(\d+)/(\d+)$")


def coerce_quantity(val: Union[str, int, float, None]) -> Optional[float]:
    """Coerce a possibly-string quantity to float or None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return None

    s = val.strip().lower()
    if s in _NULL_VALUES:
        return None

    m = _RANGE_RE.match(s)
    if m:
        return round((float(m.group(1)) + float(m.group(2))) / 2, 2)

    m = _APPROX_RE.match(s)
    if m:
        return float(m.group(1))

    m = _FRACTION_RE.match(s)
    if m:
        return round(int(m.group(1)) / int(m.group(2)), 3)

    m = _MIXED_RE.match(s)
    if m:
        return round(int(m.group(1)) + int(m.group(2)) / int(m.group(3)), 3)

    try:
        return float(s)
    except ValueError:
        return None


def coerce_servings(val: Union[str, int, float, None]) -> Optional[int]:
    """Coerce servings to int or None."""
    result = coerce_quantity(val)
    if result is None:
        return None
    return max(1, round(result))


def main():
    dry_run = "--dry-run" in sys.argv
    fixed_qty = 0
    fixed_srv = 0
    unfixable_qty = []
    files_modified = 0

    for path in sorted(RECIPES_DIR.glob("*.recipe.json")):
        with open(path) as f:
            recipe = json.load(f)

        modified = False

        for ing in recipe.get("ingredients", []):
            raw_qty = ing.get("quantity")
            if isinstance(raw_qty, str):
                coerced = coerce_quantity(raw_qty)
                if coerced != raw_qty:
                    ing["quantity"] = coerced
                    modified = True
                    fixed_qty += 1
                    if coerced is None and raw_qty.strip().lower() not in _NULL_VALUES:
                        unfixable_qty.append((path.stem, ing.get("name", "?"), raw_qty))

        raw_srv = recipe.get("metadata", {}).get("servings")
        if isinstance(raw_srv, str):
            coerced_srv = coerce_servings(raw_srv)
            if coerced_srv is not None:
                recipe["metadata"]["servings"] = coerced_srv
            else:
                recipe["metadata"]["servings"] = 4
            modified = True
            fixed_srv += 1

        if modified and not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(recipe, f, indent=2, ensure_ascii=False)

        if modified:
            files_modified += 1

    logger.info(f"Files modified: {files_modified}")
    logger.info(f"Quantities fixed: {fixed_qty}")
    logger.info(f"Servings fixed: {fixed_srv}")

    if unfixable_qty:
        logger.info(f"\nUnfixable quantities ({len(unfixable_qty)}) → set to null:")
        for stem, name, raw in unfixable_qty[:20]:
            logger.info(f"  {stem}: '{name}' had quantity={raw!r}")


if __name__ == "__main__":
    main()
