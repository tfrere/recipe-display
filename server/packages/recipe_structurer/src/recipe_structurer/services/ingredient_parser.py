"""
Ingredient Parser Service — Pass 1.5 of the pipeline.

Parses ingredient lines from Pass 1 preformatted output into IngredientV2 objects.
Uses a combination of:
  - Regex to extract annotations ([english_name], {category}, (optionnel))
  - NER model (edwardjross/xlm-roberta-base-finetuned-recipe-all) to parse qty/unit/name/state
  - Unit normalization to canonical short forms (g, ml, tbsp, tsp, etc.)
  - Fuzzy matching for ID correction (Levenshtein distance)
"""

import logging
import re
from collections import defaultdict
from typing import Optional

from ..models.recipe_v2 import IngredientV2

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# NER MODEL (lazy-loaded singleton)
# ═══════════════════════════════════════════════════════════════════

_ner_pipeline = None

NER_MODEL_NAME = "edwardjross/xlm-roberta-base-finetuned-recipe-all"


def get_ner_pipeline():
    """Lazy-load the NER model (downloaded once, then cached by HuggingFace)."""
    global _ner_pipeline
    if _ner_pipeline is None:
        logger.info(f"Loading NER model: {NER_MODEL_NAME}")
        from transformers import (
            AutoModelForTokenClassification,
            AutoTokenizer,
            pipeline,
        )

        tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
        model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME)
        _ner_pipeline = pipeline(
            "token-classification",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
        )
        logger.info("NER model loaded successfully")
    return _ner_pipeline


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
    # Poids
    "grams": "g", "gram": "g",
    "kilograms": "kg", "kilogram": "kg",
    "pounds": "lb", "pound": "lb",
    "ounces": "oz", "ounce": "oz",
    # Comptables (singulariser)
    "cloves": "clove", "sprigs": "sprig", "leaves": "leaf",
    "slices": "slice", "pieces": "piece", "bunches": "bunch",
    "pinches": "pinch", "stalks": "stalk", "heads": "head",
}


def normalize_unit(raw_unit: str) -> Optional[str]:
    """Normalize a NER unit to its canonical short form."""
    if not raw_unit:
        return None
    clean = raw_unit.strip().lower()
    return UNIT_NORMALIZE.get(clean, clean)


# ═══════════════════════════════════════════════════════════════════
# QUANTITY PARSING
# ═══════════════════════════════════════════════════════════════════

_FRACTION_MAP = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 0.333, "⅔": 0.667}


def parse_quantity(qty_str: str) -> Optional[float]:
    """Convert a quantity string to float."""
    if not qty_str:
        return None

    qty_str = qty_str.strip()

    # Unicode fractions
    for frac, val in _FRACTION_MAP.items():
        if frac in qty_str:
            rest = qty_str.replace(frac, "").strip()
            return float(rest) + val if rest else val

    # Text fractions: "1/2", "3/4"
    if "/" in qty_str:
        parts = qty_str.split()
        total = 0.0
        for part in parts:
            if "/" in part:
                num, den = part.split("/")
                total += float(num) / float(den)
            else:
                total += float(part)
        return total

    # Range: "1-2" → take the first
    if "-" in qty_str:
        return float(qty_str.split("-")[0])

    try:
        return float(qty_str)
    except ValueError:
        return None


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
# REGEX FOR EXTRACTING ANNOTATIONS FROM PASS 1 OUTPUT
# ═══════════════════════════════════════════════════════════════════

# FR→EN unit translation for building the English NER input
_UNIT_FR_TO_EN = {
    "cuillères à soupe": "tablespoons", "cuillère à soupe": "tablespoon",
    "cuillères à café": "teaspoons", "cuillère à café": "teaspoon",
    "gousses": "cloves", "gousse": "clove",
    "branches": "sprigs", "branche": "sprig",
    "brins": "sprigs", "brin": "sprig",
    "feuilles": "leaves", "feuille": "leaf",
    "tranches": "slices", "tranche": "slice",
}

# Regex to extract qty+unit from the beginning of the cleaned line
# Long/composite units FIRST, then short units with word boundary
_QTY_UNIT_RE = re.compile(
    r"^([\d½¼¾⅓⅔/.,\-\s]+)\s*("
    r"cuillères?\s+à\s+(?:soupe|café)|"
    r"gousses?|branches?|brins?|feuilles?|tranches?|"
    r"tablespoons?|teaspoons?|pounds?|ounces?|cloves?|"
    r"cups?|pieces?|pinch|bunch|sprigs?|"
    r"kg\b|ml\b|cl\b|lb\b|oz\b|tbsp\b|tsp\b|"
    r"g\b|l\b"
    r")\s+",
    re.IGNORECASE,
)

# Quantity only (countable ingredients: "4 carottes", "2 eggs")
_QTY_ONLY_RE = re.compile(r"^([\d½¼¾⅓⅔/.,\-]+)\s+", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════
# MAIN PARSING FUNCTION
# ═══════════════════════════════════════════════════════════════════

def parse_ingredient_line(line: str) -> Optional[IngredientV2]:
    """
    Parse a single ingredient line from Pass 1 output into an IngredientV2.

    Expected format from Pass 1:
      "250g champignons de Paris [mushrooms] {produce}, émincés [sliced]"
      "sel [salt] {spice} (à volonté)"

    Uses the NER model to extract qty/unit/name from the English translation,
    then normalizes units and generates a snake_case ID.
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

    # English translations [english_name], optionally [english_state]
    en_matches = re.findall(r"\[([^\]]+)\]", line)
    name_en = en_matches[0] if en_matches else ""
    preparation_en = en_matches[1] if len(en_matches) > 1 else None

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

    # ── Clean the line (remove annotations) ────────────────────
    clean_line = re.sub(r"\{[^}]+\}", "", line)
    clean_line = re.sub(r"\[[^\]]+\]", "", clean_line)
    clean_line = re.sub(r"\([^)]+\)", "", clean_line)
    clean_line = clean_line.strip().rstrip(",").strip()

    # Extract the original-language name (without qty/unit)
    name_line = re.sub(
        r"^[\d½¼¾⅓⅔/.,\-\s]+\s*"
        r"(?:cuillères?\s+à\s+(?:soupe|café)|"
        r"gousses?|branches?|brins?|feuilles?|tranches?|"
        r"tablespoons?|teaspoons?|pounds?|ounces?|cloves?|"
        r"cups?|pieces?|pinch|bunch|sprigs?|"
        r"kg\b|ml\b|cl\b|lb\b|oz\b|tbsp\b|tsp\b|g\b|l\b)?\s*",
        "", clean_line, count=1, flags=re.IGNORECASE,
    )
    name_original = name_line.strip().rstrip(",").strip() if name_line.strip() else clean_line

    # ── Build English text for NER ─────────────────────────────
    en_text_for_ner = ""
    if name_en:
        qty_unit_match = _QTY_UNIT_RE.match(clean_line)
        qty_only_match = None

        if qty_unit_match:
            qty_str = qty_unit_match.group(1).strip()
            unit_str = qty_unit_match.group(2).strip()
            unit_en = _UNIT_FR_TO_EN.get(unit_str.lower(), unit_str)
            en_text_for_ner = f"{qty_str} {unit_en} {name_en}"
        else:
            qty_only_match = _QTY_ONLY_RE.match(clean_line)
            if qty_only_match:
                qty_str = qty_only_match.group(1).strip()
                en_text_for_ner = f"{qty_str} {name_en}"
            else:
                en_text_for_ner = name_en

        if preparation_en:
            en_text_for_ner += f", {preparation_en}"

    if not en_text_for_ner:
        en_text_for_ner = clean_line

    # ── NER parsing ────────────────────────────────────────────
    ner = get_ner_pipeline()
    results = ner(en_text_for_ner)

    entities: dict[str, list[dict]] = defaultdict(list)
    for entity in results:
        tag = entity["entity_group"]
        word = entity["word"].strip()
        score = entity["score"]
        entities[tag].append({"text": word, "score": score})

    # Extract NER values
    ner_qty_raw = " ".join(e["text"] for e in entities.get("QUANTITY", []))
    ner_unit_raw = " ".join(e["text"] for e in entities.get("UNIT", []))
    ner_state = " ".join(e["text"] for e in entities.get("STATE", []))
    ner_name = " ".join(e["text"] for e in entities.get("NAME", []))

    # Confidence
    all_scores = [e["score"] for ents in entities.values() for e in ents]
    avg_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # ── Build IngredientV2 ─────────────────────────────────────
    quantity = parse_quantity(ner_qty_raw)
    unit = normalize_unit(ner_unit_raw)
    preparation = preparation_en or (ner_state if ner_state else None)
    final_name_en = name_en if name_en else ner_name
    ingredient_id = make_ingredient_id(final_name_en) if final_name_en else make_ingredient_id(name_original)

    # Validate category
    valid_categories = {
        "meat", "poultry", "seafood", "produce", "dairy", "egg",
        "pantry", "spice", "condiment", "beverage", "other",
    }
    if category not in valid_categories:
        logger.warning(f"Unknown category '{category}' for '{name_en}', defaulting to 'other'")
        category = "other"

    logger.debug(
        f"Parsed ingredient: {name_original} [{final_name_en}] "
        f"qty={quantity} unit={unit} conf={avg_confidence:.1%}"
    )

    return IngredientV2(
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


def parse_ingredients_from_preformat(preformatted_text: str) -> list[IngredientV2]:
    """
    Extract and parse all ingredient lines from a Pass 1 preformatted output.

    Finds the INGREDIENTS section and parses each line using the NER model.
    Returns a list of IngredientV2 objects with deduplicated IDs.
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
    parsed: list[IngredientV2] = []
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
                        f"Step '{step.id}' references unknown ID '{ref}', no close match found"
                    )
                    corrected_uses.append(ref)  # Keep as-is, let Pydantic validation catch it

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
                    corrected_requires.append(ref)

        step.requires = corrected_requires

    if corrections:
        logger.info(f"Fuzzy matching corrected {corrections} ID references")

    return steps
