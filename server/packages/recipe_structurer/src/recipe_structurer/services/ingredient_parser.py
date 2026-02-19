"""
Ingredient Parser Service — Pass 1.5 of the pipeline.

Parses ingredient lines from Pass 1 preformatted output into Ingredient objects.
Uses a combination of:
  - Regex to extract annotations («clean_name», [full english line], {category}, (optionnel))
  - strangetom/ingredient-parser (CRF model) to parse qty/unit/name from the English translation
  - Fuzzy matching for ID correction (Levenshtein distance)

The LLM (Pass 1) translates each ingredient line to English.
The CRF parser deterministically extracts structured data from that English line.
Each component does what it does best: LLM for translation, CRF for structure.
"""

import logging
import re
from fractions import Fraction
from typing import Optional

from ..models.recipe import Ingredient

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# CRF PARSER (lazy-loaded singleton)
# ═══════════════════════════════════════════════════════════════════

_parser_loaded = False


def _ensure_parser():
    """Ensure the ingredient-parser-nlp CRF model is loaded (happens on first import)."""
    global _parser_loaded
    if not _parser_loaded:
        logger.info("Loading ingredient-parser-nlp (CRF model)...")
        from ingredient_parser import parse_ingredient  # noqa: F401
        _parser_loaded = True
        logger.info("ingredient-parser-nlp loaded successfully")


# ═══════════════════════════════════════════════════════════════════
# UNIT NORMALIZATION
# ═══════════════════════════════════════════════════════════════════

UNIT_NORMALIZE = {
    # Volumes
    "tablespoons": "tbsp", "tablespoon": "tbsp",
    "teaspoons": "tsp", "teaspoon": "tsp",
    "cups": "cup",
    "liters": "l", "liter": "l", "litres": "l", "litre": "l",
    "milliliters": "ml", "milliliter": "ml",
    "centiliters": "cl", "centiliter": "cl",
    "deciliters": "dl", "deciliter": "dl",
    # Weights
    "grams": "g", "gram": "g",
    "kilograms": "kg", "kilogram": "kg",
    "pounds": "lb", "pound": "lb",
    "ounces": "oz", "ounce": "oz",
    # Countable (singularize)
    "cloves": "clove", "sprigs": "sprig", "leaves": "leaf",
    "slices": "slice", "pieces": "piece", "bunches": "bunch",
    "pinches": "pinch", "stalks": "stalk", "heads": "head",
    "handfuls": "handful", "cans": "can",
    "small handful": "handful", "small handfuls": "handful",
    "large handful": "handful", "large handfuls": "handful",
}


def normalize_unit(raw_unit) -> Optional[str]:
    """Normalize a CRF unit to its canonical short form."""
    if raw_unit is None:
        return None
    # The CRF parser may return pint Unit objects — convert to string
    clean = str(raw_unit).strip().lower()
    if not clean:
        return None
    return UNIT_NORMALIZE.get(clean, clean)


# ═══════════════════════════════════════════════════════════════════
# ID GENERATION
# ═══════════════════════════════════════════════════════════════════

def make_ingredient_id(name_en: str) -> str:
    """Convert an English name to a snake_case ID."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", name_en.lower().strip())
    return re.sub(r"\s+", "_", clean)


# ═══════════════════════════════════════════════════════════════════
# FUZZY MATCHING (for post-Pass 2 ID correction)
# ═══════════════════════════════════════════════════════════════════

def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            curr_row.append(min(
                prev_row[j + 1] + 1,
                curr_row[j] + 1,
                prev_row[j] + (c1 != c2),
            ))
        prev_row = curr_row
    return prev_row[-1]


def fuzzy_match_id(
    ref: str,
    valid_ids: set[str],
    max_distance: int = 3,
) -> Optional[str]:
    """Find the closest valid ID by Levenshtein distance."""
    if ref in valid_ids:
        return ref
    best_match = None
    best_dist = max_distance + 1
    for valid_id in valid_ids:
        dist = levenshtein_distance(ref, valid_id)
        if dist < best_dist:
            best_dist = dist
            best_match = valid_id
    return best_match if best_dist <= max_distance else None


# ═══════════════════════════════════════════════════════════════════
# MAIN PARSING FUNCTION
# ═══════════════════════════════════════════════════════════════════

def parse_ingredient_line(line: str) -> Optional[Ingredient]:
    """
    Parse a single ingredient line from Pass 1 output into an Ingredient.

    Expected format from Pass 1:
      "- 250g «champignons de Paris» [250g mushrooms, sliced] {produce}, émincés"
      "- «sel» [salt] {spice} (à volonté)"

    Flow:
      1. Extract «clean_name» → name (original language)
      2. Extract [full english line] → send to CRF parser
      3. CRF parser returns: qty, unit, name_en, preparation
      4. Build Ingredient
    """
    line = line.strip()
    if not line:
        return None

    # Remove leading "- " from list format
    if line.startswith("- "):
        line = line[2:]

    # ── Extract annotations ────────────────────────────────────
    # Category {category}
    category_match = re.search(r"\{(\w+)\}", line)
    category = category_match.group(1) if category_match else "other"

    # Full English translation [full english line]
    en_matches = re.findall(r"\[([^\]]+)\]", line)
    en_full_line = en_matches[0] if en_matches else ""

    # Optional flag
    line_lower = line.lower()
    optional = (
        "(optionnel)" in line_lower
        or "(optional)" in line_lower
        or "(à volonté)" in line_lower
    )

    # Notes (parenthetical text that is NOT an optional marker)
    notes = None
    for m in re.finditer(r"\(([^)]+)\)", line):
        text = m.group(1)
        if text.lower() not in ("optionnel", "optional", "à volonté"):
            notes = text
            break

    # ── Extract original-language name from «» annotation ──────
    name_guillemets = re.search(r"«([^»]+)»", line)
    if name_guillemets:
        name_original = name_guillemets.group(1).strip()
    else:
        # Fallback: use the first part before any annotation
        first_bracket = line.find("[")
        raw_part = line[:first_bracket].strip() if first_bracket > 0 else line
        raw_part = raw_part.split(",")[0].strip()
        name_original = re.sub(r"^[\d½¼¾⅓⅔/.,\-\s]+", "", raw_part).strip()
        if not name_original:
            name_original = raw_part
        logger.warning(f"No «» annotation found, falling back to raw: '{name_original}'")

    # ── Extract original-language preparation (after annotations + comma) ──
    preparation_original = None
    prep_match = re.search(
        r"\}\s*(?:\((?:optionnel|optional|à volonté)\)\s*)?,\s*(.+?)$",
        line,
    )
    if prep_match:
        # Clean: remove any remaining annotations from preparation text
        prep_text = prep_match.group(1).strip()
        prep_text = re.sub(r"\[[^\]]+\]", "", prep_text).strip().rstrip(",").strip()
        if prep_text:
            preparation_original = prep_text

    # ── Parse English line with CRF parser ─────────────────────
    quantity = None
    unit = None
    name_en = None
    preparation_en = None

    if en_full_line:
        _ensure_parser()
        from ingredient_parser import parse_ingredient

        try:
            result = parse_ingredient(en_full_line)

            # Extract name
            if result.name:
                name_en = result.name[0].text if isinstance(result.name, list) else result.name.text

            # Extract quantity
            if result.amount:
                amt = result.amount[0]
                try:
                    quantity = float(amt.quantity) if amt.quantity is not None else None
                except (ValueError, TypeError):
                    # Fraction objects
                    if isinstance(amt.quantity, Fraction):
                        quantity = float(amt.quantity)

                unit = normalize_unit(amt.unit)

            # Extract preparation
            if result.preparation:
                if isinstance(result.preparation, list):
                    preparation_en = result.preparation[0].text if result.preparation else None
                else:
                    preparation_en = result.preparation.text

        except Exception as e:
            logger.error(f"CRF parser failed on '{en_full_line}': {e}")
            # Fallback: use the English line as name_en
            name_en = en_full_line

    # ── Build Ingredient ─────────────────────────────────────
    preparation = preparation_original or preparation_en
    final_name_en = name_en or en_full_line or name_original
    ingredient_id = make_ingredient_id(final_name_en)

    # Validate category
    valid_categories = {
        "meat", "poultry", "seafood", "produce", "dairy", "egg",
        "grain", "legume", "nuts_seeds", "oil", "herb",
        "pantry", "spice", "condiment", "beverage", "other",
    }
    if category not in valid_categories:
        logger.warning(f"Unknown category '{category}' for '{final_name_en}', defaulting to 'other'")
        category = "other"

    logger.debug(
        f"Parsed: «{name_original}» → name_en='{final_name_en}' "
        f"qty={quantity} unit={unit} prep='{preparation}'"
    )

    return Ingredient(
        id=ingredient_id,
        name=name_original,
        name_en=final_name_en or None,
        quantity=quantity,
        unit=unit,
        category=category,
        preparation=preparation,
        notes=notes,
        optional=optional,
    )


def parse_ingredients_from_preformat(preformatted_text: str) -> list[Ingredient]:
    """
    Extract and parse all ingredient lines from a Pass 1 preformatted output.

    Finds the INGREDIENTS section and parses each line using the CRF parser.
    Returns a list of Ingredient objects with deduplicated IDs.
    """
    # Find the INGREDIENTS section
    ingredients_match = re.search(
        r"^INGREDIENTS:\s*\n(.*?)(?=\n(?:INSTRUCTIONS|TOOLS|NOTES):|\Z)",
        preformatted_text,
        re.MULTILINE | re.DOTALL,
    )

    if not ingredients_match:
        logger.warning("No INGREDIENTS section found in preformatted text")
        return []

    ingredients_text = ingredients_match.group(1)
    lines = [l.strip() for l in ingredients_text.split("\n") if l.strip()]

    # Filter lines that look like section headers (sub-recipe headers like "**Toppings:**")
    ingredient_lines = [
        l for l in lines
        if l.startswith("- ") or (l and l[0].isdigit()) or (l and not l.startswith("**"))
    ]

    logger.info(f"Found {len(ingredient_lines)} ingredient lines to parse")

    # Parse each line
    parsed: list[Ingredient] = []
    seen_ids: dict[str, int] = {}

    for line in ingredient_lines:
        try:
            ingredient = parse_ingredient_line(line)
            if ingredient is None:
                continue

            # Deduplicate IDs by appending a suffix
            base_id = ingredient.id
            if base_id in seen_ids:
                seen_ids[base_id] += 1
                ingredient.id = f"{base_id}_{seen_ids[base_id]}"
            else:
                seen_ids[base_id] = 0

            parsed.append(ingredient)

        except Exception as e:
            logger.error(f"Failed to parse ingredient line: '{line}' — {e}")
            continue

    logger.info(
        f"Parsed {len(parsed)} ingredients "
        f"({sum(1 for p in parsed if p.quantity is not None)} with quantities)"
    )

    return parsed


def correct_step_references(
    steps: list,
    ingredient_ids: set[str],
    produced_states: set[str],
) -> list:
    """
    Post-process step references to fix LLM ID mismatches using fuzzy matching.

    If a step references an ingredient ID that doesn't exist, try to find the
    closest valid ID. Log corrections and errors.
    """
    all_valid = ingredient_ids | produced_states
    corrections = 0

    for step in steps:
        corrected_uses = []
        for ref in step.uses:
            if ref in all_valid:
                corrected_uses.append(ref)
            else:
                match = fuzzy_match_id(ref, all_valid)
                if match:
                    logger.warning(
                        f"Auto-corrected step '{step.id}' ref: '{ref}' → '{match}'"
                    )
                    corrected_uses.append(match)
                    corrections += 1
                else:
                    logger.error(
                        f"Step '{step.id}' references unknown ID '{ref}', "
                        f"no close match found — dropping reference"
                    )
                    # Do NOT keep the invalid ref; re-validation will catch
                    # any resulting graph inconsistencies

        step.uses = corrected_uses

        # Also check requires
        corrected_requires = []
        for ref in step.requires:
            if ref in produced_states:
                corrected_requires.append(ref)
            else:
                match = fuzzy_match_id(ref, produced_states)
                if match:
                    logger.warning(
                        f"Auto-corrected step '{step.id}' requires: '{ref}' → '{match}'"
                    )
                    corrected_requires.append(match)
                    corrections += 1
                else:
                    logger.error(
                        f"Step '{step.id}' requires unknown state '{ref}', "
                        f"no close match found — dropping reference"
                    )

        step.requires = corrected_requires

    if corrections:
        logger.info(f"Fuzzy matching corrected {corrections} ID references")

    return steps
