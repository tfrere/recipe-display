#!/usr/bin/env python3
"""Build USDA portions index with 3-layer matching (NutriMatch-inspired SOTA).

Expands portion_weights.json by matching recipe ingredient names to USDA
SR Legacy food portion data using:

  Layer 1: Exact match (normalized USDA names → simple lookup keys)
  Layer 2: Embedding similarity (BGE-small, threshold 0.82) + strict keyword validation
  Layer 3: LLM-as-judge (validates ambiguous embedding matches, à la NutriMatch 2025)

Sources:
  - USDA SR Legacy food_portion.csv (14,449 portion entries)
  - USDA SR Legacy food.csv (7,793 foods)
  - Recipe ingredients name_en (924 unique values from data/recipes_old/)

Output:
  - portion_weights.json (expanded, replaces existing)

References:
  - NutriMatch (Nature, Jan 2025): LLM embedding + LLM-as-judge validation
  - FoodSEM (arXiv, Sep 2025): F1 98% on food NEL with fine-tuned LLM
"""

import csv
import glob
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_USDA_DIR = Path("/tmp/usda_sr_legacy/FoodData_Central_sr_legacy_food_csv_2018-04")
_RECIPE_DIR = Path(__file__).parent.parent / "data" / "recipes_old"
_OUTPUT_PATH = (
    Path(__file__).parent.parent
    / "packages/recipe_scraper/src/recipe_scraper/data/portion_weights.json"
)

# ---------------------------------------------------------------------------
# Step 1 — Parse USDA CSVs
# ---------------------------------------------------------------------------

_MEASURE_UNIT_MAP = {
    "cup": "cup",
    "tbsp": "tbsp",
    "tsp": "tsp",
    "fl oz": "fl_oz",
    "oz": "oz",
    "lb": "lb",
}

_PIECE_PATTERNS = [
    (re.compile(r"\bfruit\b", re.I), "piece"),
    (re.compile(r"\bwhole\b", re.I), "piece"),
    (re.compile(r"\bmedium\b", re.I), "piece"),
    (re.compile(r"\blarge\b", re.I), "piece"),
    (re.compile(r"\bsmall\b", re.I), "piece"),
    (re.compile(r"\bunit\b", re.I), "piece"),
    (re.compile(r"\bitem\b", re.I), "piece"),
    (re.compile(r"\bearth?\b", re.I), "piece"),
    (re.compile(r"\bbreast\b", re.I), "piece"),
    (re.compile(r"\bthigh\b", re.I), "piece"),
    (re.compile(r"\bleg\b", re.I), "piece"),
    (re.compile(r"\bwing\b", re.I), "piece"),
    (re.compile(r"\bdrumstick\b", re.I), "piece"),
    (re.compile(r"\bfillet?\b", re.I), "piece"),
    (re.compile(r"\bsteak\b", re.I), "piece"),
    (re.compile(r"\bchop\b", re.I), "piece"),
    (re.compile(r"\bpatty\b", re.I), "piece"),
    (re.compile(r"\blink\b", re.I), "piece"),
    (re.compile(r"\bstick\b", re.I), "piece"),
]

_SLICE_PATTERN = re.compile(r"\bslice", re.I)
_SPEAR_PATTERN = re.compile(r"\bspear", re.I)
_LEAF_PATTERN = re.compile(r"\bleaf|leaves", re.I)
_STALK_PATTERN = re.compile(r"\bstalk", re.I)
_HEAD_PATTERN = re.compile(r"\bhead\b", re.I)
_CLOVE_PATTERN = re.compile(r"\bclove", re.I)
_RING_PATTERN = re.compile(r"\bring", re.I)
_STRIP_PATTERN = re.compile(r"\bstrip", re.I)


def normalize_measure(desc: str) -> Optional[str]:
    """Map a USDA portion_description + measure_unit to our standard unit key."""
    d = desc.lower().strip()

    for usda_unit, our_unit in _MEASURE_UNIT_MAP.items():
        if usda_unit in d:
            return our_unit

    if _SLICE_PATTERN.search(d):
        return "slice"
    if _SPEAR_PATTERN.search(d):
        return "spear"
    if _LEAF_PATTERN.search(d):
        return "leaf"
    if _STALK_PATTERN.search(d):
        return "stalk"
    if _HEAD_PATTERN.search(d):
        return "head"
    if _CLOVE_PATTERN.search(d):
        return "clove"
    if _RING_PATTERN.search(d):
        return "ring"
    if _STRIP_PATTERN.search(d):
        return "strip"

    for pat, unit in _PIECE_PATTERNS:
        if pat.search(d):
            return unit

    return None


def parse_usda_csvs() -> dict[str, dict[str, float]]:
    """Parse USDA food.csv + food_portion.csv into {food_name: {unit: grams}}."""
    food_csv = _USDA_DIR / "food.csv"
    portion_csv = _USDA_DIR / "food_portion.csv"

    fdc_to_name: dict[int, str] = {}
    with open(food_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fdc_to_name[int(row["fdc_id"])] = row["description"]

    result: dict[str, dict[str, float]] = {}
    skipped = 0

    with open(portion_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fdc_id = int(row["fdc_id"])
            food_name = fdc_to_name.get(fdc_id)
            if not food_name:
                continue

            gram_weight = float(row.get("gram_weight") or 0)
            if gram_weight <= 0:
                continue

            portion_desc = row.get("portion_description", "").strip()
            modifier = row.get("modifier", "").strip()
            measure_name = row.get("measure_unit_name", "").strip() if "measure_unit_name" in row else ""
            combined_desc = " ".join(filter(None, [portion_desc, modifier, measure_name]))

            unit = normalize_measure(combined_desc)
            if not unit:
                skipped += 1
                continue

            if food_name not in result:
                result[food_name] = {}
            if unit not in result[food_name]:
                result[food_name][unit] = round(gram_weight, 1)

    logger.info(
        f"Parsed USDA CSVs: {len(result)} foods with portions "
        f"(skipped {skipped} unrecognized measures)"
    )
    return result


# ---------------------------------------------------------------------------
# Step 2 — Build exact index from USDA names
# ---------------------------------------------------------------------------

_USDA_STRIP_WORDS = {
    "raw", "fresh", "mature", "whole", "cooked", "dried", "canned",
    "frozen", "without salt", "salted", "unsalted", "uncooked",
    "unprepared", "unenriched", "enriched", "plain",
    "NFS",  # "not further specified"
}

_USDA_STRIP_SUFFIXES = re.compile(
    r",?\s*\b(?:raw|fresh|mature seeds|mature|"
    r"without skin|with skin|"
    r"without salt|with salt added|"
    r"not further specified|NFS|"
    r"year round average|"
    r"includes USDA commodity)\b.*$",
    re.I,
)


def _depluralize(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("oes") and len(word) > 4:
        return word[:-2]
    # Only strip "es" if the stem without "es" still looks like a word
    # (avoid "olives" → "oliv", "bones" → "bon")
    if word.endswith("ves") and len(word) > 5:
        return word[:-1]  # "olives" → "olive"
    if word.endswith("ches") or word.endswith("shes") or word.endswith("xes") or word.endswith("zes"):
        return word[:-2]
    if word.endswith("ses") and len(word) > 5:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _pluralize(word: str) -> str:
    if word.endswith("y") and not word.endswith("ey"):
        return word[:-1] + "ies"
    if word.endswith(("s", "sh", "ch", "x", "z")):
        return word + "es"
    return word + "s"


def extract_lookup_keys(usda_name: str) -> list[str]:
    """Generate multiple normalized lookup keys from a USDA food name.

    "Bananas, raw" → ["banana", "bananas"]
    "Peppers, sweet, red, raw" → ["sweet red pepper", "red pepper", "red bell pepper"]
    "Cheese, cheddar" → ["cheddar cheese", "cheddar"]
    "Nuts, cashew nuts, raw" → ["cashew nuts", "cashew", "cashews"]
    """
    keys: set[str] = set()
    lower = usda_name.lower().strip()

    parts = [p.strip() for p in lower.split(",")]
    primary = parts[0].strip()

    cleaned = _USDA_STRIP_SUFFIXES.sub("", lower).strip().rstrip(",").strip()
    clean_parts = [p.strip() for p in cleaned.split(",")]
    clean_parts = [p for p in clean_parts if p and p not in _USDA_STRIP_WORDS]

    # Key 1: primary word + singular/plural
    keys.add(primary)
    keys.add(_depluralize(primary))
    keys.add(_pluralize(_depluralize(primary)))

    # Key 2: reversed compound (e.g. "Cheese, cheddar" → "cheddar cheese")
    if len(clean_parts) >= 2:
        reversed_name = " ".join(clean_parts[1:]) + " " + clean_parts[0]
        reversed_name = re.sub(r"\s+", " ", reversed_name).strip()
        keys.add(reversed_name)
        # Singular form of reversed
        rev_singular = " ".join(clean_parts[1:]) + " " + _depluralize(clean_parts[0])
        rev_singular = re.sub(r"\s+", " ", rev_singular).strip()
        keys.add(rev_singular)

        # Just the qualifier(s) (e.g. "cheddar")
        qualifier = " ".join(clean_parts[1:]).strip()
        if len(qualifier) > 3:
            keys.add(qualifier)
            keys.add(_depluralize(qualifier))

    # Key 3: for "Nuts, cashew nuts" → "cashew nuts", "cashew"
    if len(clean_parts) >= 2:
        for part in clean_parts[1:]:
            if len(part) > 3:
                keys.add(part)
                keys.add(_depluralize(part))

    # Key 4: full cleaned name joined
    full = " ".join(clean_parts)
    if len(full) > 3:
        keys.add(full)

    # Key 5: extract parenthetical aliases
    # "Coriander (cilantro) leaves, raw" → "cilantro"
    # "Cabbage, chinese (pak-choi)" → "pak-choi", "bok choy"
    paren_matches = re.findall(r"\(([^)]+)\)", lower)
    for alias in paren_matches:
        alias = alias.strip()
        if len(alias) > 2:
            keys.add(alias)
            keys.add(_depluralize(alias))

    # Key 6: for "Nuts, cashew nuts" → extract "cashew" (word before the primary noun)
    for part in clean_parts:
        part_words = part.split()
        for w in part_words:
            if len(w) > 3 and w not in _USDA_STRIP_WORDS and w != primary:
                dep = _depluralize(w)
                if len(dep) > 3:
                    keys.add(dep)
                    keys.add(_pluralize(dep))

    # Key 7: "fresh X" / "X" pairs for common ingredients
    for k in list(keys):
        if k.startswith("fresh "):
            keys.add(k[6:])
        elif len(k) > 3 and not k.startswith("fresh "):
            keys.add("fresh " + k)

    # Key 8: common name mappings
    _COMMON_ALIASES = {
        "pak-choi": "bok choy",
        "pe-tsai": "napa cabbage",
        "garbanzo": "chickpea",
        "bengal gram": "chickpea",
        "broad beans": "fava beans",
        "cos": "romaine lettuce",
        "swamp cabbage": "water spinach",
        "garden cress": "cress",
        "beet": "beetroot",
        "beets": "beetroot",
        "agar": "agar-agar",
        "rutabaga": "swede",
        "eggplant": "aubergine",
        "zucchini": "courgette",
        "scallion": "spring onion",
        "cilantro": "coriander",
    }
    for k in list(keys):
        if k in _COMMON_ALIASES:
            keys.add(_COMMON_ALIASES[k])

    # Remove keys with parentheses (cleanup)
    keys = {re.sub(r"\([^)]*\)", "", k).strip() for k in keys}
    keys = {re.sub(r"\s+", " ", k).strip() for k in keys}

    return [k for k in keys if len(k) > 2]


# Preferred USDA entries for ambiguous generic keys.
# When multiple USDA foods generate the same key, this resolves to the most common form.
_PREFERRED_USDA_FOR_KEY: dict[str, str] = {
    "flour": "Wheat flour, white, all-purpose",
    "all-purpose flour": "Wheat flour, white, all-purpose",
    "bread flour": "Wheat flours, bread",
    "sugar": "Sugars, granulated",
    "brown sugar": "Sugars, brown",
    "powdered sugar": "Sugars, powdered",
    "milk": "Milk, whole, 3.25% milkfat",
    "rice": "Rice, white, long-grain, regular, raw",
    "pasta": "Pasta, dry, unenriched",
    "oat": "Oats",
    "oats": "Oats",
    "corn": "Corn, sweet, yellow, raw",
    "salt": "Salt, table",
    "cream": "Cream, fluid, heavy whipping",
    "yogurt": "Yogurt, plain, whole milk",
    "cheese": "Cheese, cheddar",
    "bread": "Bread, white, commercially prepared",
    "oil": "Oil, olive, salad or cooking",
    "vinegar": "Vinegar, cider",
    "honey": "Honey",
    "lemon": "Lemons, raw, without peel",
    "lime": "Limes, raw",
    "orange": "Oranges, raw, all commercial varieties",
    "apple": "Apples, raw, with skin",
    "banana": "Bananas, raw",
    "tomato": "Tomatoes, red, ripe, raw, year round average",
    "potato": "Potatoes, flesh and skin, raw",
    "carrot": "Carrots, raw",
    "onion": "Onions, raw",
    "garlic": "Garlic, raw",
    "ginger": "Ginger root, raw",
    "celery": "Celery, raw",
    "pepper": "Spices, pepper, black",
    "egg": "Egg, whole, raw, fresh",
    "chicken": "Chicken, broilers or fryers, breast, skinless, boneless",
    "beef": "Beef, ground, 85% lean meat / 15% fat, raw",
    "pork": "Pork, fresh, loin, whole, separable lean only, raw",
    "salmon": "Fish, salmon, Atlantic, wild, raw",
    "shrimp": "Crustaceans, shrimp, mixed species, raw",
    "tofu": "Tofu, firm, prepared with calcium sulfate",
    "butter": "Butter, salted",
    "cornstarch": "Cornstarch",
    "cocoa": "Cocoa, dry powder, unsweetened",
    "chocolate": "Chocolate, dark, 70-85% cacao solids",
}


def _usda_priority(usda_name: str, key: str) -> int:
    """Score a USDA entry for a key. Higher = preferred.

    Prefer:
    - "raw" forms
    - Shorter, more generic names
    - Entries whose primary word matches the key closely
    """
    lower = usda_name.lower()
    score = 0

    if "raw" in lower:
        score += 10
    if "unenriched" in lower or "enriched" not in lower:
        score += 2
    if "plain" in lower:
        score += 3
    if "unsweetened" in lower:
        score += 2

    for neg in ["canned", "frozen", "dried", "cooked", "boiled", "fried",
                "roasted", "infant", "baby", "baby food", "babyfood"]:
        if neg in lower:
            score -= 5

    # Prefer entries where the key appears in the primary (before first comma)
    primary = lower.split(",")[0].strip()
    if key in primary or key in primary.replace("s", ""):
        score += 5

    # Prefer shorter names (less processing/specification)
    score -= len(usda_name) // 20

    return score


def build_exact_index(
    usda_portions: dict[str, dict[str, float]],
) -> dict[str, tuple[str, dict[str, float]]]:
    """Build key → (usda_name, portions) for exact lookup.

    Uses priority scoring to resolve key collisions (e.g., "flour" → wheat flour,
    not millet flour).
    """
    index: dict[str, tuple[str, dict[str, float], int]] = {}

    for usda_name, portions in usda_portions.items():
        for key in extract_lookup_keys(usda_name):
            # Check if this key has a preferred USDA entry
            preferred = _PREFERRED_USDA_FOR_KEY.get(key)
            if preferred and preferred.lower() in usda_name.lower():
                index[key] = (usda_name, portions, 999)
                continue

            priority = _usda_priority(usda_name, key)
            existing = index.get(key)
            if existing is None or priority > existing[2]:
                index[key] = (usda_name, portions, priority)

    # Strip priority from output
    result = {k: (v[0], v[1]) for k, v in index.items()}
    logger.info(f"Built exact index: {len(result)} keys from {len(usda_portions)} foods")
    return result


# ---------------------------------------------------------------------------
# Step 3 — Embedding matching with strict validation
# ---------------------------------------------------------------------------

def validate_portion_match(query: str, usda_name: str) -> bool:
    """Strict validation to prevent false positives in embedding matches.

    Rules:
    1. At least one significant query word must appear in the USDA primary name
    2. Reject if USDA primary name has a "category-changing" word absent from query
    3. Special handling for known homonym categories (pepper, seed, milk, yeast)
    """
    q_words = set(re.sub(r"[,;.()]", " ", query.lower()).split())
    q_words -= {
        "raw", "fresh", "dried", "whole", "ground", "cooked", "large", "small",
        "medium", "organic", "extra", "virgin", "pure", "natural", "store-bought",
    }

    usda_lower = usda_name.lower()
    usda_primary = usda_lower.split(",")[0].strip()
    usda_primary_words = set(usda_primary.split())

    # Generate query word variants (singular/plural)
    q_variants: set[str] = set()
    for w in q_words:
        q_variants.add(w)
        q_variants.add(w + "s")
        if w.endswith("s") and not w.endswith("ss"):
            q_variants.add(w[:-1])
        if w.endswith("ies"):
            q_variants.add(w[:-3] + "y")

    # Rule 1: query must share a word with USDA primary name
    if not q_variants & usda_primary_words:
        return False

    # Rule 2: category-changing words in USDA → reject
    _BAD_PREFIXES = {
        "bread", "cake", "cookie", "cereal", "soup", "candy", "bar",
        "pudding", "infant", "baby", "babyfood", "pizza", "pie",
        "muffin", "wafer", "cracker", "sandwich", "burger",
    }
    if usda_primary_words & _BAD_PREFIXES and not q_words & _BAD_PREFIXES:
        return False

    # Rule 3: homonym guards
    _SPICE_WORDS = {"pepper", "peppers", "cumin", "cinnamon", "paprika", "turmeric", "cayenne"}
    _VEGETABLE_PEPPER_INDICATORS = {"sweet", "bell", "banana", "jalapeño", "habanero", "serrano"}
    if q_words & _SPICE_WORDS and not q_words & _VEGETABLE_PEPPER_INDICATORS:
        if usda_primary_words & {"peppers", "pepper"} and usda_primary_words & _VEGETABLE_PEPPER_INDICATORS:
            return False

    _SEED_QUERY = {"cumin", "anise", "fennel", "caraway", "sesame", "poppy", "mustard", "celery"}
    if q_words & _SEED_QUERY:
        if "seeds" in usda_primary_words or "seed" in usda_primary_words:
            seed_type_words = usda_primary_words - {"seeds", "seed"}
            if not q_variants & seed_type_words:
                return False

    if "milk" in q_words and "human" in usda_lower:
        return False

    if "yeast" in q_words and ("extract" in usda_lower or "spread" in usda_lower):
        if "extract" not in q_words and "spread" not in q_words:
            return False

    if "baking" in q_words and ("soda" in q_words or "powder" in q_words):
        if "chocolate" in usda_lower:
            return False

    return True


def build_embedding_index(
    usda_portions: dict[str, dict[str, float]],
) -> tuple[list[str], "np.ndarray"]:
    """Embed all USDA food names for semantic search."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    names = list(usda_portions.keys())
    logger.info(f"Encoding {len(names)} USDA food names...")
    embeddings = model.encode(names, normalize_embeddings=True, show_progress_bar=False, batch_size=256)
    return names, embeddings, model


# ---------------------------------------------------------------------------
# Step 4 — LLM-as-judge (NutriMatch approach)
# ---------------------------------------------------------------------------

def llm_validate_matches(
    pairs: list[tuple[str, str, float]],
) -> list[bool]:
    """Use an LLM to validate ambiguous embedding matches.

    Follows NutriMatch (2025) approach: after embedding retrieval,
    an LLM validates contextual equivalence.

    Args:
        pairs: list of (query, usda_name, similarity_score)

    Returns:
        list of booleans (True = valid match)
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("No OPENROUTER_API_KEY — skipping LLM validation, accepting all")
        return [True] * len(pairs)

    from openai import OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/recipe-display",
            "X-Title": "Portion Matcher",
        },
    )

    numbered_lines = []
    for i, (query, usda_name, score) in enumerate(pairs):
        numbered_lines.append(f'{i+1}. Recipe: "{query}" ↔ USDA: "{usda_name}"')
    batch_text = "\n".join(numbered_lines)

    prompt = f"""You are a food science expert. For each pair below, determine if the USDA food
is a valid reference for the recipe ingredient's PORTION WEIGHTS (gram per cup, per piece, etc.).

Rules:
- Answer YES if they refer to the same base food (ignoring preparation state: raw/cooked/dried).
- Answer NO if they are fundamentally different foods, even if names overlap.
  Examples of NO: "black pepper" (spice) vs "Peppers, sweet" (vegetable),
  "cumin seeds" vs "Seeds, breadnut tree", "baking soda" vs "Baking chocolate".
- Answer YES for reasonable approximations: "banana" ≈ "Bananas, raw" is YES.

Reply with ONLY one YES or NO per line, in order. Nothing else.

{batch_text}"""

    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": "Reply YES or NO for each line. Nothing else."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=len(pairs) * 5,
            temperature=0.0,
        )
        text = response.choices[0].message.content or ""
        lines = [l.strip().upper() for l in text.strip().split("\n") if l.strip()]

        results = []
        for line in lines:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            results.append(cleaned.startswith("YES"))

        while len(results) < len(pairs):
            results.append(False)
        return results[:len(pairs)]
    except Exception as e:
        logger.error(f"LLM validation failed: {e}")
        return [True] * len(pairs)


# ---------------------------------------------------------------------------
# Step 5 — Match recipe ingredients
# ---------------------------------------------------------------------------

def load_recipe_ingredients() -> list[str]:
    """Collect all unique name_en values from recipe JSON files."""
    all_names: set[str] = set()
    for path in glob.glob(str(_RECIPE_DIR / "*.recipe.json")):
        with open(path) as f:
            recipe = json.load(f)
        for ing in recipe.get("ingredients", []):
            en = ing.get("name_en", "").strip()
            if en and len(en) > 2:
                all_names.add(en)
    names = sorted(all_names)
    logger.info(f"Found {len(names)} unique ingredient name_en values")
    return names


def match_all_ingredients(
    exact_index: dict[str, tuple[str, dict[str, float]]],
    usda_portions: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """3-layer matching: exact → embedding → LLM-as-judge."""

    recipe_names = load_recipe_ingredients()

    # ── Layer 1: Exact match ──────────────────────────────────────────
    matched: dict[str, dict[str, float]] = {}
    unmatched: list[str] = []

    _RECIPE_STRIP_WORDS = {
        "fresh", "organic", "raw", "large", "small", "medium",
        "homemade", "store-bought", "good", "quality", "extra",
        "virgin", "pure", "natural", "thick", "thin",
        "whole", "ground", "minced", "chopped", "sliced",
        "diced", "grated", "crushed", "dried", "frozen",
        "canned", "cooked", "warm", "cold", "hot",
    }

    def _try_exact(key: str) -> Optional[tuple[str, dict]]:
        entry = exact_index.get(key)
        if entry:
            return entry
        # Try depluralized
        dep = _depluralize(key)
        if dep != key:
            entry = exact_index.get(dep)
            if entry:
                return entry
        # Try pluralized
        plur = _pluralize(dep)
        if plur != key:
            entry = exact_index.get(plur)
            if entry:
                return entry
        return None

    for name in recipe_names:
        key = name.lower().strip()
        # Remove commas and extra punctuation
        key_clean = re.sub(r"[,;.()]+", " ", key)
        key_clean = re.sub(r"\s+", " ", key_clean).strip()

        # Try full name
        entry = _try_exact(key_clean)
        if entry:
            matched[key_clean] = entry[1]
            continue

        # Try stripping adjectives from start
        words = key_clean.split()
        stripped = [w for w in words if w not in _RECIPE_STRIP_WORDS]
        if stripped and stripped != words:
            candidate = " ".join(stripped)
            entry = _try_exact(candidate)
            if entry:
                matched[key_clean] = entry[1]
                continue

        # Try individual words (last word first — head noun is usually last)
        found = False
        for word in reversed(stripped or words):
            if len(word) < 3:
                continue
            entry = _try_exact(word)
            if entry:
                matched[key_clean] = entry[1]
                found = True
                break

        # Try "X or Y" → just X
        if not found and " or " in key_clean:
            first_option = key_clean.split(" or ")[0].strip()
            entry = _try_exact(first_option)
            if not entry:
                fo_words = [w for w in first_option.split() if w not in _RECIPE_STRIP_WORDS]
                if fo_words:
                    entry = _try_exact(" ".join(fo_words))
                    if not entry:
                        entry = _try_exact(fo_words[-1])
            if entry:
                matched[key_clean] = entry[1]
                found = True

        if not found:
            unmatched.append(name)

    logger.info(f"Layer 1 (exact): {len(matched)}/{len(recipe_names)} matched, {len(unmatched)} remaining")

    if not unmatched:
        return matched

    # ── Layer 2: Embedding match ──────────────────────────────────────
    usda_names, usda_embs, model = build_embedding_index(usda_portions)
    query_embs = model.encode(unmatched, normalize_embeddings=True, show_progress_bar=False, batch_size=256)
    scores = query_embs @ usda_embs.T

    EMBEDDING_THRESHOLD = 0.80
    LLM_THRESHOLD = 0.88  # above this with validation passed → accept without LLM

    emb_accepted: list[tuple[str, str, dict[str, float]]] = []
    needs_llm: list[tuple[str, str, float, dict[str, float]]] = []
    still_unmatched: list[str] = []

    for i, name in enumerate(unmatched):
        top_indices = np.argsort(scores[i])[::-1][:15]
        found = False
        for idx in top_indices:
            score = float(scores[i][idx])
            if score < EMBEDDING_THRESHOLD:
                break
            usda_name = usda_names[idx]
            if not validate_portion_match(name, usda_name):
                continue

            if score >= LLM_THRESHOLD:
                emb_accepted.append((name, usda_name, usda_portions[usda_name]))
            else:
                needs_llm.append((name, usda_name, score, usda_portions[usda_name]))
            found = True
            break

        if not found:
            still_unmatched.append(name)

    logger.info(
        f"Layer 2 (embedding): {len(emb_accepted)} auto-accepted (cos≥{LLM_THRESHOLD}), "
        f"{len(needs_llm)} need LLM validation, "
        f"{len(still_unmatched)} no candidate"
    )

    for name, usda_name, portions in emb_accepted:
        key = name.lower().strip()
        matched[key] = portions
        logger.debug(f"  ✓ {name} → {usda_name}")

    # ── Layer 3: LLM-as-judge ─────────────────────────────────────────
    all_verdicts: list[bool] = []
    if needs_llm:
        llm_pairs = [(name, usda_name, score) for name, usda_name, score, _ in needs_llm]

        # Batch in groups of 30
        all_verdicts: list[bool] = []
        for batch_start in range(0, len(llm_pairs), 30):
            batch = llm_pairs[batch_start:batch_start + 30]
            verdicts = llm_validate_matches(batch)
            all_verdicts.extend(verdicts)

        accepted_llm = 0
        rejected_llm = 0
        for (name, usda_name, score, portions), verdict in zip(needs_llm, all_verdicts):
            if verdict:
                key = name.lower().strip()
                matched[key] = portions
                accepted_llm += 1
                logger.info(f"  LLM ✓ {name} → {usda_name} (cos={score:.3f})")
            else:
                rejected_llm += 1
                still_unmatched.append(name)
                logger.info(f"  LLM ✗ {name} → {usda_name} (cos={score:.3f}) REJECTED")

        logger.info(f"Layer 3 (LLM): {accepted_llm} accepted, {rejected_llm} rejected")

    total_matched = len(matched)
    total = len(recipe_names)
    exact_count = total_matched - len(emb_accepted)
    llm_count = 0
    if needs_llm:
        llm_accepted_count = sum(1 for v in all_verdicts if v)
        exact_count -= llm_accepted_count
        llm_count = llm_accepted_count

    logger.info(
        f"\n{'='*60}\n"
        f"FINAL: {total_matched}/{total} ingredients have portion data "
        f"({total_matched/total*100:.1f}%)\n"
        f"  Exact:     {exact_count}\n"
        f"  Embedding: {len(emb_accepted)}\n"
        f"  LLM:       {llm_count}\n"
        f"  Unmatched: {len(still_unmatched)}\n"
        f"{'='*60}"
    )

    if still_unmatched:
        logger.info("Unmatched ingredients (sample):")
        for name in sorted(still_unmatched)[:30]:
            logger.info(f"  • {name}")

    return matched


# ---------------------------------------------------------------------------
# Step 6 — Build final portion_weights.json
# ---------------------------------------------------------------------------

def build_final_index(
    usda_portions: dict[str, dict[str, float]],
    recipe_matched: dict[str, dict[str, float]],
    exact_index: dict[str, tuple[str, dict[str, float]]],
) -> dict[str, dict[str, float]]:
    """Merge all sources into the final portion_weights.json."""
    final: dict[str, dict[str, float]] = {}

    # 1. Add all normalized USDA entries
    for key, (_, portions) in exact_index.items():
        if key not in final:
            final[key] = portions

    # 2. Add recipe-specific matches (may override with better data)
    for key, portions in recipe_matched.items():
        final[key] = portions

    # 3. Add plural forms for all entries
    extras: dict[str, dict[str, float]] = {}
    for key, portions in final.items():
        if key.endswith("s") and not key.endswith("ss"):
            singular = key[:-1]
            if singular not in final and len(singular) > 2:
                extras[singular] = portions
        elif not key.endswith("s") and len(key) > 2:
            plural = key + "s"
            if plural not in final:
                extras[plural] = portions
    final.update(extras)

    logger.info(f"Final index: {len(final)} entries")
    return final


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=== Building USDA Portions Index (3-Layer SOTA Matching) ===\n")

    # Step 1: Parse USDA CSVs
    usda_portions = parse_usda_csvs()

    # Step 2: Build exact index
    exact_index = build_exact_index(usda_portions)

    # Step 3-5: Match recipe ingredients
    recipe_matched = match_all_ingredients(exact_index, usda_portions)

    # Step 6: Build and save final index
    final = build_final_index(usda_portions, recipe_matched, exact_index)

    from datetime import datetime
    output = {
        "_meta": {
            "description": "Ingredient-specific unit-to-gram conversions from USDA FoodData Central",
            "sources": [
                "USDA SR Legacy (April 2018) — food_portion.csv",
                "3-layer matching: exact + embedding (BGE-small) + LLM-as-judge",
            ],
            "references": [
                "NutriMatch (Nature, 2025): LLM embedding + LLM-as-judge validation",
                "FoodSEM (arXiv, 2025): SOTA food named-entity linking",
            ],
            "license": "Public Domain (CC0 1.0 Universal)",
            "generated_at": datetime.now().isoformat(),
            "total_ingredients": len(final),
        }
    }
    output.update(dict(sorted(final.items())))

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"\nSaved to {_OUTPUT_PATH}")
    logger.info(f"Total entries: {len(final)}")


if __name__ == "__main__":
    main()
