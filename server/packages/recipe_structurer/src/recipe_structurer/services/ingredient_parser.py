"""
Ingredient Parser Service — Pass 1.5 of the pipeline.

Parses ingredient lines from Pass 1 preformatted output into Ingredient objects.
Uses a combination of:
  - Regex to extract annotations («clean_name», [full english line], {category}, (optionnel))
  - strangetom/ingredient-parser (CRF model) to parse qty/unit/name from the English translation
  - Deterministic ID correction: suffix strip + original-name lookup (replaces Levenshtein)

The LLM (Pass 1) translates each ingredient line to English.
The CRF parser deterministically extracts structured data from that English line.
Each component does what it does best: LLM for translation, CRF for structure.
"""

import logging
import re
from fractions import Fraction
from typing import Optional

from unidecode import unidecode

from ..models.recipe import Ingredient
from ..shared import INGREDIENT_CATEGORIES

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
# POST-CRF QUANTITY NORMALIZATION (deterministic layer)
# ═══════════════════════════════════════════════════════════════════

_KNOWN_UNITS = {
    "pinch", "handful", "dash", "splash", "sprig", "bunch", "slice",
    "piece", "clove", "leaf", "stalk", "head", "drop", "dollop",
    "knob", "strip", "sheet", "stick", "wedge", "ear", "bulb",
    "grating", "segment", "scoop",
    "cup", "tbsp", "tsp", "g", "kg", "ml", "l", "cl", "dl",
    "oz", "lb", "can",
}

_PLURAL_UNITS = {
    "drops": "drop", "dollops": "dollop", "splashes": "splash",
    "dashes": "dash", "gratings": "grating", "grinds": "grind",
    "segments": "segment", "scoops": "scoop",
    "thin slices": "slice", "thin slice": "slice",
}

_MODIFIERS = {
    "scant", "heaping", "heaped", "generous", "big", "small", "large",
    "level", "rounded", "tiny", "good",
}

_BARE_MODIFIER_DEFAULTS = {
    "scant": (0.85, "tsp"),
    "heaping": (1.25, "tbsp"),
    "heaped": (1.25, "tbsp"),
    "generous": (1.25, "tbsp"),
    "tiny": (0.5, "tsp"),
    "good": (1.25, "tbsp"),
}

_MODIFIER_MULTIPLIERS = {
    "scant": 0.85,
    "tiny": 0.5,
    "small": 0.75,
    "level": 1.0,
    "good": 1.15,
    "rounded": 1.15,
    "heaping": 1.25,
    "generous": 1.25,
    "big": 1.5,
    "large": 1.5,
}


def normalize_quantity_post_crf(
    quantity: Optional[float],
    unit: Optional[str],
) -> tuple[Optional[float], Optional[str], Optional[str], Optional[str]]:
    """
    Fix known CRF failure modes after parsing.

    Returns (quantity, unit, quantitySource, modifier_note).
    - quantitySource is "inferred" when we applied a deterministic rule.
    - modifier_note captures stripped modifiers (e.g. "scant", "heaping").
    """
    if unit is None:
        return quantity, unit, None, None

    unit_lower = unit.strip().lower()

    # Resolve plural forms first: "drops" → "drop", "thin slices" → "slice"
    if unit_lower in _PLURAL_UNITS:
        unit_lower = _PLURAL_UNITS[unit_lower]

    # Handle compound modifier+unit: "scant teaspoon", "big handful", "heaping tablespoon"
    words = unit_lower.split()
    if len(words) >= 2 and words[0] in _MODIFIERS:
        modifier = words[0]
        real_unit_raw = " ".join(words[1:])
        real_unit = normalize_unit(real_unit_raw) or _PLURAL_UNITS.get(real_unit_raw, real_unit_raw)

        if real_unit in _KNOWN_UNITS or real_unit_raw in UNIT_NORMALIZE:
            resolved_qty = quantity if quantity is not None else 1.0
            multiplier = _MODIFIER_MULTIPLIERS.get(modifier, 1.0)
            resolved_qty = round(resolved_qty * multiplier, 2)
            logger.debug(
                f"Modifier fix: unit='{unit}' → qty={resolved_qty}, "
                f"unit='{real_unit}', modifier='{modifier}'"
            )
            return resolved_qty, real_unit, "inferred", modifier

    # Handle bare modifier without base unit (legacy): "scant", "heaping"
    if unit_lower in _BARE_MODIFIER_DEFAULTS and quantity is None:
        mult, default_unit = _BARE_MODIFIER_DEFAULTS[unit_lower]
        logger.debug(
            f"Bare modifier fix: unit='{unit}' → qty={mult}, "
            f"unit='{default_unit}', modifier='{unit_lower}'"
        )
        return mult, default_unit, "inferred", unit_lower

    # Normalize the unit for subsequent checks
    normalized = normalize_unit(unit_lower) or unit_lower

    # Handle implicit qty=1 for recognized units when CRF returns qty=None
    if quantity is None and normalized in _KNOWN_UNITS:
        logger.debug(f"Implicit qty: unit='{normalized}' → qty=1")
        return 1.0, normalized, "inferred", None

    return quantity, normalized if normalized != unit_lower else unit, None, None


# ═══════════════════════════════════════════════════════════════════
# ID GENERATION
# ═══════════════════════════════════════════════════════════════════

def make_ingredient_id(name_en: str) -> str:
    """Convert an English name to a snake_case ID.

    Uses unidecode to transliterate accented characters so that
    ``"crème fraîche"`` becomes ``"creme_fraiche"`` instead of
    ``"crme_frache"``.
    """
    transliterated = unidecode(name_en)
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", transliterated.lower().strip())
    return re.sub(r"\s+", "_", clean)


# ═══════════════════════════════════════════════════════════════════
# DETERMINISTIC ID CORRECTION (replaces Levenshtein fuzzy matching)
# ═══════════════════════════════════════════════════════════════════

_SUFFIX_RE = re.compile(r"^(.+?)_(\d+)$")


def _suffix_strip_match(ref: str, valid_ids: set[str]) -> Optional[str]:
    """Try stripping or varying the _N dedup suffix to find an exact match."""
    m = _SUFFIX_RE.match(ref)
    if not m:
        return None
    base = m.group(1)
    if base in valid_ids:
        return base
    for n in range(1, 6):
        candidate = f"{base}_{n}"
        if candidate in valid_ids:
            return candidate
    return None


def _name_lookup_match(
    ref: str,
    name_to_id: dict[str, str],
) -> Optional[str]:
    """Try matching a ref against ingredient original-language names.

    Resolution order:
      1. Exact match (case-insensitive, underscore-tolerant)
      2. Word-boundary substring match — picks the shortest name that
         contains the ref (or vice-versa) to avoid "egg" matching
         "eggplant" when "egg" also exists.
    """
    ref_normalized = ref.lower().replace("_", " ").strip()
    if not ref_normalized:
        return None

    for name, ing_id in name_to_id.items():
        name_normalized = name.lower().strip()
        if ref_normalized == name_normalized:
            return ing_id
        if ref_normalized == name_normalized.replace(" ", "_"):
            return ing_id

    ref_re = re.compile(rf"\b{re.escape(ref_normalized)}\b")
    best_id: Optional[str] = None
    best_len = float("inf")

    for name, ing_id in name_to_id.items():
        name_normalized = name.lower().strip()
        if not name_normalized:
            continue
        name_re = re.compile(rf"\b{re.escape(name_normalized)}\b")
        if ref_re.search(name_normalized) or name_re.search(ref_normalized):
            if len(name_normalized) < best_len:
                best_len = len(name_normalized)
                best_id = ing_id

    return best_id


def resolve_ref(
    ref: str,
    valid_ids: set[str],
    name_to_id: dict[str, str],
) -> Optional[str]:
    """
    Deterministic ref resolution chain:
      1. Exact match against valid IDs
      2. Suffix strip (_N) then exact match
      3. Lookup against ingredient original-language names
    Returns the resolved ID or None.
    """
    if ref in valid_ids:
        return ref

    match = _suffix_strip_match(ref, valid_ids)
    if match:
        return match

    match = _name_lookup_match(ref, name_to_id)
    if match:
        return match

    return None


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

    # ── Require «» annotations — reject lines without them ─────
    name_guillemets = re.search(r"«([^»]+)»", line)
    if not name_guillemets:
        logger.debug(f"Skipping line without «» annotation: {line[:80]}")
        return None

    name_original = name_guillemets.group(1).strip()

    # ── Extract annotations ────────────────────────────────────
    category_match = re.search(r"\{(\w+)\}", line)
    category = category_match.group(1) if category_match else "other"

    en_matches = re.findall(r"\[([^\]]+)\]", line)
    en_full_line = en_matches[0] if en_matches else ""

    line_lower = line.lower()
    optional = (
        "(optionnel)" in line_lower
        or "(optional)" in line_lower
        or "(à volonté)" in line_lower
    )

    notes = None
    for m in re.finditer(r"\(([^)]+)\)", line):
        text = m.group(1)
        if text.lower() not in ("optionnel", "optional", "à volonté"):
            notes = text
            break

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
        crf_available = False
        try:
            _ensure_parser()
            from ingredient_parser import parse_ingredient
            crf_available = True
        except (ImportError, ModuleNotFoundError):
            logger.debug("CRF parser not available, using English line as fallback")
            name_en = en_full_line

        if crf_available:
            try:
                result = parse_ingredient(en_full_line)

                if result.name:
                    name_en = result.name[0].text if isinstance(result.name, list) else result.name.text

                if result.amount:
                    amt = result.amount[0]
                    try:
                        quantity = float(amt.quantity) if amt.quantity is not None else None
                    except (ValueError, TypeError):
                        if isinstance(amt.quantity, Fraction):
                            quantity = float(amt.quantity)

                    unit = normalize_unit(amt.unit)

                if result.preparation:
                    if isinstance(result.preparation, list):
                        preparation_en = result.preparation[0].text if result.preparation else None
                    else:
                        preparation_en = result.preparation.text

            except Exception as e:
                logger.error(f"CRF parser failed on '{en_full_line}': {e}")
                name_en = en_full_line

    # ── Post-CRF quantity normalization ──────────────────────
    quantity_source: Optional[str] = None
    quantity, unit, quantity_source, modifier_note = normalize_quantity_post_crf(quantity, unit)

    if modifier_note:
        existing_notes = notes or ""
        notes = f"{modifier_note}; {existing_notes}" if existing_notes else modifier_note

    # ── Build Ingredient ─────────────────────────────────────
    preparation = preparation_original or preparation_en
    final_name_en = name_en or en_full_line or name_original
    ingredient_id = make_ingredient_id(final_name_en)

    if category not in INGREDIENT_CATEGORIES:
        logger.warning(f"Unknown category '{category}' for '{final_name_en}', defaulting to 'other'")
        category = "other"

    logger.debug(
        f"Parsed: «{name_original}» → name_en='{final_name_en}' "
        f"qty={quantity} unit={unit} prep='{preparation}' "
        f"quantitySource={quantity_source}"
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
        quantitySource=quantity_source,
    )


def parse_ingredients_from_preformat(preformatted_text: str) -> list[Ingredient]:
    """
    Extract and parse all ingredient lines from a Pass 1 preformatted output.

    Finds the INGREDIENTS section and parses each line using the CRF parser.
    Returns a list of Ingredient objects with deduplicated IDs (suffix _2, _3, etc.).
    Duplicate ingredients are kept separate to preserve preparation context for the DAG.
    """
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

    ingredient_lines = []
    for l in lines:
        if l.startswith("**"):
            continue
        if "«" in l and "»" in l:
            ingredient_lines.append(l)
        elif l.startswith("- ") or (l and l[0].isdigit()):
            logger.debug(f"Ingredient line without «» annotations, keeping: {l[:80]}")
            ingredient_lines.append(l)

    logger.info(f"Found {len(ingredient_lines)} ingredient lines to parse")

    parsed: list[Ingredient] = []
    seen_ids: dict[str, int] = {}

    for line in ingredient_lines:
        try:
            ingredient = parse_ingredient_line(line)
            if ingredient is None:
                continue

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
    ingredients: list[Ingredient] | None = None,
) -> list:
    """
    Post-process step references using deterministic ID resolution.

    Resolution chain per ref:
      1. Exact match against ingredient IDs or produced states
      2. Suffix strip (_N) then exact match
      3. Lookup against ingredient original-language names

    Args:
        steps: list of Step objects from Pass 2
        ingredient_ids: set of valid ingredient IDs
        produced_states: set of valid produced state IDs
        ingredients: list of Ingredient objects (needed for name lookup)
    """
    all_valid = ingredient_ids | produced_states

    name_to_id: dict[str, str] = {}
    if ingredients:
        for ing in ingredients:
            if ing.name:
                name_to_id[ing.name] = ing.id
            if ing.name_en:
                name_to_id[ing.name_en] = ing.id

    corrections = 0

    for step in steps:
        corrected_uses = []
        for ref in step.uses:
            resolved = resolve_ref(ref, all_valid, name_to_id)
            if resolved:
                if resolved != ref:
                    logger.warning(
                        f"Auto-corrected step '{step.id}' ref: '{ref}' → '{resolved}'"
                    )
                    corrections += 1
                corrected_uses.append(resolved)
            else:
                logger.error(
                    f"Step '{step.id}' references unknown ID '{ref}', "
                    f"no match found — dropping reference"
                )

        step.uses = corrected_uses

        corrected_requires = []
        for ref in step.requires:
            resolved = resolve_ref(ref, produced_states, name_to_id)
            if resolved:
                if resolved != ref:
                    logger.warning(
                        f"Auto-corrected step '{step.id}' requires: '{ref}' → '{resolved}'"
                    )
                    corrections += 1
                corrected_requires.append(resolved)
            else:
                logger.error(
                    f"Step '{step.id}' requires unknown state '{ref}', "
                    f"no match found — dropping reference"
                )

        step.requires = corrected_requires

    if corrections:
        logger.info(f"Deterministic correction resolved {corrections} ID references")

    return steps
