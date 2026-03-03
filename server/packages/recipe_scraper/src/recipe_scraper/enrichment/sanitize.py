"""Type sanitization for LLM-produced recipe data."""

import logging
import re as _re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unit aliases (normalised to singular lowercase)
# ---------------------------------------------------------------------------

_VOLUME_UNITS = {"cup", "cups", "tbsp", "tsp", "ml", "l", "cl", "dl", "cs", "cc"}
_COUNTABLE_UNITS = {"piece", "pieces", "slice", "slices"}
_FRACTION_SAFE_UNITS = _VOLUME_UNITS | _COUNTABLE_UNITS | {"pinch", "handful", "bunch"}

# Per-unit thresholds for "implausibly large" quantities.
# Anything above these values is almost certainly a parsing artefact.
_IMPLAUSIBLE_QTY_THRESHOLDS: Dict[str, float] = {
    "cup": 20, "cups": 20,
    "tbsp": 50, "tsp": 100,
    "cs": 50, "cc": 100,
    "piece": 50, "pieces": 50,
    "slice": 50, "slices": 50,
}

# Patterns to parse "N unit" quantity strings inside name_en
_QTY_UNIT_PATTERN = _re.compile(
    r"^(\d+(?:\.\d+)?)\s+"
    r"(tablespoons?|tbsp|teaspoons?|tsp|cups?|pieces?|pinch(?:es)?|ml|g|oz|lb)\b"
    r"\s+(?:plus\s+)?",
    _re.IGNORECASE,
)
_COMPOUND_QTY_PATTERN = _re.compile(
    r"^(\d+)\s+(tablespoons?|tbsp)\s+plus\s+(\d+)\s+(teaspoons?|tsp)\s+(.+)",
    _re.IGNORECASE,
)

_UNIT_TO_TSP = {
    "tablespoon": 3.0, "tablespoons": 3.0, "tbsp": 3.0,
    "teaspoon": 1.0, "teaspoons": 1.0, "tsp": 1.0,
}


# ---------------------------------------------------------------------------
# Fraction repair
# ---------------------------------------------------------------------------

def _parse_broken_fraction_unit(unit: str) -> Optional[Tuple[float, str]]:
    """Parse a unit like '/2 cup' → (0.5, 'cup') or '/4 piece' → (0.25, 'piece').

    Returns (divisor_fraction, clean_unit) or None if not a broken fraction.
    """
    m = _re.match(r"^/(\d+)\s+(.+)", unit)
    if m:
        divisor = int(m.group(1))
        if divisor > 0:
            return (1.0 / divisor, m.group(2).strip())
    return None


def repair_ingredient_fractions(ingredients: List[Dict[str, Any]]) -> int:
    """Repair broken fraction patterns in ingredient quantity/unit fields.

    Mutates ingredients in-place. Returns the number of repairs made.

    Handles three classes of errors from LLM structuring:
    1. Broken fraction in unit: qty=1, unit="/2 cup" → qty=0.5, unit="cup"
    2. Quantity string stuck in name_en: name_en="1 tablespoon plus 1 teaspoon
       baking powder" with qty=250 → extract and fix
    3. Implausible large quantity with small unit: qty=120, unit="cup" → reset
       to None (let LLM re-estimate or mark as no_weight)
    """
    repairs = 0

    for ing in ingredients:
        raw_unit = ing.get("unit") or ""
        raw_qty = ing.get("quantity")
        name_en = ing.get("name_en") or ""
        name = ing.get("name") or ""

        # --- Case 1: Broken fraction in unit (e.g. "/2 cup", "/4 piece") ---
        parsed = _parse_broken_fraction_unit(raw_unit)
        if parsed:
            frac, clean_unit = parsed
            old_qty = raw_qty if raw_qty is not None else 1.0
            new_qty = round(max(old_qty, 1.0) * frac, 4)
            logger.info(
                f"[Fraction repair] '{name or name_en}': "
                f"{raw_qty} '{raw_unit}' → {new_qty} '{clean_unit}'"
            )
            ing["quantity"] = new_qty
            ing["unit"] = clean_unit
            repairs += 1
            continue

        # --- Case 2: Compound quantity in name_en ---
        # e.g. name_en="1 tablespoon plus 1 teaspoon baking powder", qty=250, unit="tsp"
        if name_en:
            compound = _COMPOUND_QTY_PATTERN.match(name_en)
            if compound:
                n1 = int(compound.group(1))
                u1 = compound.group(2).lower()
                n2 = int(compound.group(3))
                u2 = compound.group(4).lower()
                real_name = compound.group(5).strip()
                tsp_total = n1 * _UNIT_TO_TSP.get(u1, 1) + n2 * _UNIT_TO_TSP.get(u2, 1)
                logger.info(
                    f"[Fraction repair] '{name_en}': compound qty "
                    f"({n1} {u1} + {n2} {u2} = {tsp_total} tsp) → "
                    f"qty={tsp_total}, unit='tsp', name_en='{real_name}'"
                )
                ing["quantity"] = tsp_total
                ing["unit"] = "tsp"
                ing["name_en"] = real_name
                repairs += 1
                continue

            simple = _QTY_UNIT_PATTERN.match(name_en)
            if simple and (raw_qty is None or (isinstance(raw_qty, (int, float)) and raw_qty > 50)):
                extracted_qty = float(simple.group(1))
                extracted_unit = simple.group(2).lower()
                rest = name_en[simple.end():].strip()
                if rest:
                    logger.info(
                        f"[Fraction repair] '{name_en}': qty in name_en "
                        f"→ qty={extracted_qty}, unit='{extracted_unit}', name_en='{rest}'"
                    )
                    ing["quantity"] = extracted_qty
                    ing["unit"] = extracted_unit
                    ing["name_en"] = rest
                    repairs += 1
                    continue

        # --- Case 3: Implausible quantity with small volume/count unit ---
        # e.g. qty=120, unit="cup" — likely a parsing artefact.
        # Metric ml/l/cl/dl are excluded: 400 ml coconut milk is perfectly normal.
        unit_lower = raw_unit.strip().lower()
        threshold = _IMPLAUSIBLE_QTY_THRESHOLDS.get(unit_lower)
        if (threshold is not None
                and isinstance(raw_qty, (int, float))
                and raw_qty > threshold):
            logger.warning(
                f"[Fraction repair] '{name or name_en}': "
                f"qty={raw_qty} '{raw_unit}' exceeds {threshold} — resetting to None"
            )
            ing["quantity"] = None
            ing["unit"] = raw_unit
            repairs += 1

    return repairs


# ---------------------------------------------------------------------------
# Type coercion
# ---------------------------------------------------------------------------

def sanitize_types(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coerce fields to their expected types.

    Fixes common LLM output issues:
    - servings as string -> int
    - ingredient quantity as range string -> float (midpoint)
    - broken fractions in unit field (e.g. '/2 cup')
    """
    metadata = recipe_data.get("metadata", {})

    servings = metadata.get("servings")
    if servings is not None and not isinstance(servings, (int, float)):
        original = servings
        match = _re.search(r"(\d+)", str(servings))
        if match:
            metadata["servings"] = int(match.group(1))
        else:
            metadata["servings"] = 1
        logger.warning(f"[Sanitize] servings coerced: {repr(original)} -> {metadata['servings']}")

    for ing in recipe_data.get("ingredients", []):
        qty = ing.get("quantity")
        if qty is not None and not isinstance(qty, (int, float)):
            original = qty
            qty_str = str(qty)
            range_match = _re.search(
                r"(\d+(?:[.,]\d+)?)\s*(?:to|à|a|-)\s*(\d+(?:[.,]\d+)?)",
                qty_str,
            )
            if range_match:
                lo = float(range_match.group(1).replace(",", "."))
                hi = float(range_match.group(2).replace(",", "."))
                ing["quantity"] = round((lo + hi) / 2, 1)
            else:
                num_match = _re.search(r"(\d+(?:[.,]\d+)?)", qty_str)
                if num_match:
                    ing["quantity"] = float(num_match.group(1).replace(",", "."))
                else:
                    ing["quantity"] = None
            logger.warning(
                f"[Sanitize] ingredient '{ing.get('name', '?')}' quantity coerced: "
                f"{repr(original)} -> {ing['quantity']}"
            )

    # Run fraction repair after type coercion (needs numeric quantities)
    n_repairs = repair_ingredient_fractions(recipe_data.get("ingredients", []))
    if n_repairs:
        logger.info(f"[Sanitize] Repaired {n_repairs} broken fractions")

    return recipe_data
