"""
Nutrition matcher using BGE-small embeddings + OpenNutrition local index.

Matches English ingredient names to nutritional data using:
- BAAI/bge-small-en-v1.5 embeddings for semantic similarity
- Heuristic keyword validation to prevent false positives
- Local caching of match results

Zero false positives design: every match is validated by requiring
that key food-identifying words from the query appear in the matched
entry's name.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent.parent / "data"
_INDEX_FILE = _DATA_DIR / "opennutrition_index.json"
_EMBEDDINGS_FILE = _DATA_DIR / "opennutrition_embeddings.npy"
_CACHE_FILE = _DATA_DIR / "nutrition_cache.json"

# ---------------------------------------------------------------------------
# Embedding config
# ---------------------------------------------------------------------------
_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_SIMILARITY_THRESHOLD = 0.75

# ---------------------------------------------------------------------------
# Validation v3 — stopwords, stems, preprocessing
# ---------------------------------------------------------------------------

_STOPWORDS = {
    # Cooking/preparation
    "raw", "cooked", "fresh", "dried", "ground", "whole", "large", "small",
    "medium", "thin", "thick", "light", "heavy", "hot", "cold", "sweet",
    "sour", "spicy", "organic", "plain", "instant", "frozen", "canned",
    "sliced", "chopped", "minced", "crushed", "smoked", "roasted", "fried",
    "boiled", "baked", "grilled", "steamed", "braised", "sauteed",
    "boneless", "skinless", "unsalted", "salted", "enriched", "refined",
    "virgin", "extra", "all", "purpose", "new", "old", "young",
    "softened", "pureed", "wild", "dry", "liquid", "low", "fat", "free",
    "reduced", "nonfat", "full", "half", "mini", "baby", "jumbo",
    "flaky", "crispy", "crunchy", "creamy", "smooth",
    "pure", "natural", "regular", "classic", "traditional", "homemade",
    "style", "type", "kind", "mix", "mixed", "blend", "blended",
    # Colors
    "red", "green", "yellow", "white", "black", "dark", "brown",
    # Articles/prepositions
    "de", "of", "and", "or", "with", "in", "for", "the", "a", "an",
    # Form / unit / presentation words (NOT food-identifying)
    "clove", "cloves", "clov",
    "leaf", "leaves", "leav",
    "sprig", "sprigs",
    "slice", "slices", "slic",
    "cube", "cubes",
    "piece", "pieces", "piec",
    "noodle", "noodles",
    "strip", "strips",
    "sheet", "sheets",
    "stalk", "stalks",
    "bunch", "bunches",
    "fillet", "filet", "fillets", "filets",
    # Preparation methods (not changing food identity nutritionally much)
    "compote", "coulis",
}

_STEM_MAP = {
    "tomato": "tomato", "tomatoe": "tomato", "tomatoes": "tomato",
    "potato": "potato", "potatoe": "potato", "potatoes": "potato",
    "berry": "berry", "berrie": "berry", "berries": "berry",
    "onion": "onion", "chicken": "chicken", "pork": "pork",
    "beef": "beef", "lamb": "lamb", "veal": "veal",
    "egg": "egg", "eggs": "egg", "sugar": "sugar", "cream": "cream",
    "milk": "milk", "rice": "rice", "flour": "flour",
    "oil": "oil", "wine": "wine", "sauce": "sauce",
    "broth": "broth", "stock": "broth",  # stock = broth for matching
    "bouillon": "bouillon",
    "cheese": "cheese", "bread": "bread", "pasta": "pasta",
    "sausage": "sausage", "sausages": "sausage",
    "bacon": "bacon", "ham": "ham",
    "butter": "butter", "lard": "lard", "pepper": "pepper",
    "peppers": "pepper",
    "garlic": "garlic", "ginger": "ginger", "lemon": "lemon",
    "carrot": "carrot", "carrots": "carrot",
    "celery": "celery", "cabbage": "cabbage",
    "mushroom": "mushroom", "mushrooms": "mushroom",
    "chocolate": "chocolate",
    "honey": "honey", "yogurt": "yogurt", "vanilla": "vanilla",
    "juniper": "juniper", "elderberry": "elderberry",
    "plantain": "plantain",
    "cola": "cola", "yolk": "yolk",
    "enchilada": "enchilada", "enchiladas": "enchilada",
    "relish": "relish", "tongue": "tongue",
    "jam": "jam", "jelly": "jam",
    "neck": "neck", "butt": "butt", "shoulder": "shoulder",
    "thigh": "thigh", "breast": "breast", "wing": "wing",
    "leg": "leg", "loin": "loin", "rib": "rib", "ribs": "rib",
    "lasagna": "lasagna",
    "ditalini": "ditalini",
    "udon": "udon",
}


def _normalize_word(w: str) -> str:
    """Normalize a word using stem map and basic depluralization."""
    w = w.lower()
    if w in _STEM_MAP:
        return _STEM_MAP[w]
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("oes"):
        w = w[:-2]
    elif w.endswith("es") and len(w) > 3:
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        w = w[:-1]
    return w


def _get_key_words(text: str) -> List[str]:
    """
    Extract key food-identifying words from text.

    Filters out stopwords (cooking adjectives, form/unit words, colors, etc.)
    and normalizes via stem map + basic depluralization.
    """
    words = re.findall(r"[a-z]+", text.lower())
    result = []
    for w in words:
        if w in _STOPWORDS:
            continue
        nw = _normalize_word(w)
        if nw in _STOPWORDS:
            continue
        if len(nw) > 2:
            result.append(nw)
    return result


_COMPOSITE_BLOCKLIST = {
    "vinaigrette", "dressing", "marinade", "glaze", "rub",
    "aioli", "remoulade", "hollandaise", "béchamel", "bechamel",
    "beurre blanc", "chimichurri", "gremolata", "salsa verde",
    "compound butter", "herb butter", "garlic butter",
}

_COMPOSITE_SUFFIXES = (
    " dressing", " vinaigrette", " marinade",
    " glaze", " rub", " relish", " chutney",
)

# Standard commercial sauces with reliable nutrition data in OpenNutrition.
# These are whitelisted from the " sauce" composite filter.
_KNOWN_SAUCES = {
    "soy sauce", "hot sauce", "tomato sauce", "fish sauce",
    "worcestershire sauce", "barbecue sauce", "bbq sauce",
    "hoisin sauce", "teriyaki sauce", "sriracha sauce",
    "oyster sauce", "chili sauce", "chili garlic sauce",
    "adobo sauce", "marinara sauce", "pizza sauce",
    "cranberry sauce", "applesauce", "enchilada sauce",
    "buffalo sauce", "ponzu sauce",
    "light soy sauce", "dark soy sauce", "sweet soy sauce",
    "reduced-sodium soy sauce", "tamari soy sauce",
    "sriracha hot sauce", "hot chili sauce",
}


def _is_composite_ingredient(text: str) -> bool:
    """Detect prepared/composite ingredients whose nutrition cannot be
    reliably matched to a single raw food item in the database.

    Standard commercial sauces (soy sauce, hot sauce, etc.) are whitelisted
    because they have reliable per-100g nutrition data.

    Returns True if the ingredient should be skipped by the matcher
    (better to return None than a wildly wrong match)."""
    lower = text.lower().strip()
    if lower in _KNOWN_SAUCES:
        return False
    if lower in _COMPOSITE_BLOCKLIST:
        return True
    if lower.endswith(" sauce"):
        return True
    for suffix in _COMPOSITE_SUFFIXES:
        if lower.endswith(suffix):
            return True
    return False


def _preprocess_query(text: str) -> str:
    """
    Handle composite queries by taking the first option.

    - "Butter/lard" -> "Butter"
    - "Ditalini or small shell pasta" -> "Ditalini"
    """
    if "/" in text:
        text = text.split("/")[0].strip()
    parts = re.split(r"\bor\b", text, flags=re.IGNORECASE)
    if len(parts) > 1:
        text = parts[0].strip()
    return text


def _validate_match(query: str, matched_name: str) -> bool:
    """
    Validate that a semantic match is a true positive.

    Requires min(len(query_keys), 2) key food words from the query
    to appear in the matched entry's name. This prevents matches like
    "chicken bouillon cubes" -> "Chicken Enchiladas".

    Args:
        query: English ingredient name from the recipe.
        matched_name: Name of the matched OpenNutrition entry.

    Returns:
        True if the match is valid, False if it should be rejected.
    """
    query = _preprocess_query(query)
    query_keys = _get_key_words(query)
    if not query_keys:
        return True

    match_keys = set(_get_key_words(matched_name))
    overlap = sum(1 for k in query_keys if k in match_keys)

    required = min(len(query_keys), 2)
    return overlap >= required


class NutritionMatcher:
    """
    Matches ingredient names to nutritional data using BGE-small embeddings
    and a local OpenNutrition index.

    Features:
    - Semantic search via cosine similarity (BAAI/bge-small-en-v1.5)
    - Zero false positives via keyword validation (v3)
    - Local JSON caching of match results
    - Pre-computed embeddings for the 5K+ food database (cached as .npy)
    """

    def __init__(
        self,
        index_path: Optional[Path] = None,
        embeddings_path: Optional[Path] = None,
        cache_path: Optional[Path] = None,
        similarity_threshold: float = _SIMILARITY_THRESHOLD,
    ):
        """
        Initialize the nutrition matcher.

        Args:
            index_path: Path to the slim OpenNutrition JSON index.
            embeddings_path: Path to pre-computed .npy embeddings.
            cache_path: Path to the match cache JSON.
            similarity_threshold: Minimum cosine similarity for a match.
        """
        self._index_path = index_path or _INDEX_FILE
        self._embeddings_path = embeddings_path or _EMBEDDINGS_FILE
        self._cache_path = cache_path or _CACHE_FILE
        self._threshold = similarity_threshold

        # Lazy-loaded resources
        self._index: Optional[List[Dict[str, Any]]] = None
        self._db_embeddings: Optional[np.ndarray] = None
        self._db_texts: Optional[List[str]] = None
        self._model = None

        # Cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._dirty = False
        self._load_cache()

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _load_cache(self) -> None:
        """Load match cache from disk, filtering out legacy USDA entries."""
        if self._cache_path.exists():
            try:
                with open(self._cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Only keep entries matched by the new embedding system.
                # Skip legacy USDA entries (including their not_found markers)
                # so they get re-matched with the better embedding approach.
                self._cache = {}
                skipped = 0
                for k, v in data.items():
                    if k.startswith("_"):
                        continue
                    if v.get("matching") == "bge-small-embedding":
                        self._cache[k] = v
                    else:
                        skipped += 1
                if skipped:
                    logger.info(
                        f"Skipped {skipped} legacy USDA cache entries "
                        f"(will re-match with embeddings)"
                    )
                    self._dirty = True  # Will save the cleaned cache
                logger.info(f"Loaded {len(self._cache)} cached nutrition entries")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load nutrition cache: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def save_cache(self) -> None:
        """Persist cache to disk if changed."""
        if not self._dirty:
            return

        data = {
            "_meta": {
                "description": "Cache of OpenNutrition embedding-matched nutrition data.",
                "source": "OpenNutrition (BGE-small embedding match)",
                "matching": "BAAI/bge-small-en-v1.5 + validation v3",
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(self._cache),
            }
        }
        data.update(dict(sorted(self._cache.items())))

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._dirty = False
        logger.info(f"Saved {len(self._cache)} nutrition entries to cache")

    def _normalize_key(self, name_en: str) -> str:
        """Normalize an English name for cache key."""
        return name_en.strip().lower()

    # ------------------------------------------------------------------
    # Index & model loading (lazy)
    # ------------------------------------------------------------------

    def _load_index(self) -> None:
        """Load the OpenNutrition slim index and build search texts."""
        if self._index is not None:
            return

        if not self._index_path.exists():
            raise FileNotFoundError(
                f"OpenNutrition index not found at {self._index_path}. "
                "Run the build script first."
            )

        with open(self._index_path, "r", encoding="utf-8") as f:
            self._index = json.load(f)

        # Build search texts: name + top 3 alternates
        self._db_texts = []
        for entry in self._index:
            text = entry["name"]
            alts = entry.get("alt", [])
            if alts:
                text += ", " + ", ".join(alts[:3])
            self._db_texts.append(text)

        logger.info(f"Loaded OpenNutrition index: {len(self._index)} entries")

    def _load_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for nutrition matching. "
                "Install it with: poetry add sentence-transformers"
            )

        logger.info(f"Loading embedding model: {_MODEL_NAME}")
        self._model = SentenceTransformer(_MODEL_NAME)
        logger.info("Embedding model loaded")

    def _load_db_embeddings(self) -> None:
        """Load or compute database embeddings."""
        if self._db_embeddings is not None:
            return

        self._load_index()

        # Try loading pre-computed embeddings
        if self._embeddings_path.exists():
            self._db_embeddings = np.load(str(self._embeddings_path))
            if len(self._db_embeddings) == len(self._index):
                logger.info(
                    f"Loaded pre-computed embeddings: {self._db_embeddings.shape}"
                )
                return
            else:
                logger.warning(
                    f"Embeddings shape mismatch ({len(self._db_embeddings)} vs "
                    f"{len(self._index)} entries) — recomputing"
                )

        # Compute embeddings
        self._load_model()
        logger.info(f"Computing embeddings for {len(self._db_texts)} entries...")
        self._db_embeddings = self._model.encode(
            self._db_texts,
            batch_size=128,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        # Cache to disk
        self._embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(self._embeddings_path), self._db_embeddings)
        logger.info(
            f"Saved embeddings ({self._db_embeddings.shape}) to {self._embeddings_path}"
        )

    # ------------------------------------------------------------------
    # Exact name lookup (faster, more reliable than embeddings)
    # ------------------------------------------------------------------

    def _build_exact_index(self) -> None:
        """Build a lowercased name -> entry dict for O(1) exact lookup."""
        if hasattr(self, "_exact_index") and self._exact_index is not None:
            return
        self._load_index()
        self._exact_index: Dict[str, Dict[str, Any]] = {}
        for entry in self._index:
            name = entry.get("name", "").lower().strip()
            if name and name not in self._exact_index:
                self._exact_index[name] = entry
            for alt in entry.get("alt", []):
                alt_lower = alt.lower().strip()
                if alt_lower and alt_lower not in self._exact_index:
                    self._exact_index[alt_lower] = entry

        logger.info(f"Built exact lookup index: {len(self._exact_index)} entries")

    def _exact_match(self, name_en: str) -> Optional[Dict[str, Any]]:
        """Try an exact name match (case-insensitive) before using embeddings.

        Tries the full name first, then progressively shorter sub-phrases
        (e.g. "fresh green beans" -> "green beans" -> "beans").
        """
        self._build_exact_index()
        query = name_en.lower().strip()

        # Direct lookup
        if query in self._exact_index:
            return self._exact_index[query]

        # Try sub-phrases (longest first, from the end — head noun is usually last)
        words = query.split()
        for length in range(len(words) - 1, 0, -1):
            for start in range(len(words) - length, -1, -1):
                candidate = " ".join(words[start:start + length])
                if candidate in self._exact_index:
                    return self._exact_index[candidate]

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(self, name_en: str) -> Optional[Dict[str, Any]]:
        """
        Match a single ingredient name to nutrition data.

        Strategy (in order):
        1. Cache hit → return immediately
        2. Exact name match (O(1) lookup, no model needed) → fast & reliable
        3. Embedding similarity (BGE-small cosine) → semantic fallback

        Args:
            name_en: English ingredient name.

        Returns:
            Dict with macros per 100g (energy_kcal, protein_g, fat_g,
            carbs_g, fiber_g, etc.), or None if no good match.
        """
        key = self._normalize_key(name_en)

        # Cache hit?
        cached = self._cache.get(key)
        if cached is not None:
            if cached.get("not_found"):
                return None
            return cached

        # --- Step 0: Skip composite ingredients (sauces, dressings, etc.) ---
        if _is_composite_ingredient(name_en):
            logger.info(f"Skipping composite ingredient '{name_en}' (unreliable match)")
            self._cache[key] = {"not_found": True, "reason": "composite", "cached_at": datetime.now().isoformat()}
            self._dirty = True
            return None

        # --- Step 1: Exact name match (fast, no model) ---
        exact_entry = self._exact_match(name_en)
        if exact_entry is not None:
            result = self._build_result(exact_entry, score=1.0)
            result["matching"] = "exact-name-lookup"
            self._cache[key] = result
            self._dirty = True
            logger.info(
                f"Exact match '{name_en}' -> '{exact_entry['name']}' "
                f"({result['energy_kcal']} kcal/100g)"
            )
            return result

        # --- Step 2: Embedding similarity (semantic fallback) ---
        self._load_db_embeddings()
        self._load_model()

        # Encode query
        q_emb = self._model.encode(
            [name_en],
            normalize_embeddings=True,
        )

        # Cosine similarity (both normalized → dot product)
        scores = (q_emb @ self._db_embeddings.T)[0]
        top_indices = np.argsort(scores)[::-1][:10]

        # Find best validated match
        for idx in top_indices:
            score = float(scores[idx])
            if score < self._threshold:
                break

            entry = self._index[idx]
            if _validate_match(name_en, entry["name"]):
                result = self._build_result(entry, score)
                self._cache[key] = result
                self._dirty = True
                logger.info(
                    f"Embedding match '{name_en}' -> '{entry['name']}' "
                    f"(cos={score:.3f}, {result['energy_kcal']} kcal/100g)"
                )
                return result

        # No valid match found
        self._cache[key] = {
            "not_found": True,
            "cached_at": datetime.now().isoformat(),
        }
        self._dirty = True
        logger.info(f"No valid match for '{name_en}'")
        return None

    def match_batch(
        self, names_en: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Match multiple ingredient names to nutrition data.

        Strategy: exact name lookup first, then batch embedding for the rest.

        Args:
            names_en: List of English ingredient names.

        Returns:
            Dict mapping normalized name to nutrition data (or None).
        """
        results: Dict[str, Optional[Dict[str, Any]]] = {}
        need_embedding_names: List[str] = []
        need_embedding_keys: List[str] = []

        exact_hits = 0

        for name in names_en:
            if not name:
                continue
            key = self._normalize_key(name)

            # 0. Cache hit
            cached = self._cache.get(key)
            if cached is not None:
                results[key] = None if cached.get("not_found") else cached
                continue

            # 1. Skip composite ingredients
            if _is_composite_ingredient(name):
                logger.info(f"Skipping composite ingredient '{name}'")
                self._cache[key] = {"not_found": True, "reason": "composite", "cached_at": datetime.now().isoformat()}
                self._dirty = True
                results[key] = None
                continue

            # 2. Exact name match (no model needed)
            exact_entry = self._exact_match(name)
            if exact_entry is not None:
                result = self._build_result(exact_entry, score=1.0)
                result["matching"] = "exact-name-lookup"
                self._cache[key] = result
                self._dirty = True
                results[key] = result
                exact_hits += 1
                logger.debug(f"Exact match '{name}' -> '{exact_entry['name']}'")
                continue

            # 3. Need embedding
            need_embedding_names.append(name)
            need_embedding_keys.append(key)

        if exact_hits:
            logger.info(f"Exact name lookup resolved {exact_hits} ingredients")

        if not need_embedding_names:
            self.save_cache()
            return results

        # Load DB and model for the remaining
        self._load_db_embeddings()
        self._load_model()

        # Batch encode queries
        logger.info(
            f"Encoding {len(need_embedding_names)} ingredient queries "
            f"(after {exact_hits} exact matches)..."
        )
        q_emb = self._model.encode(
            need_embedding_names,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        # Compute similarity matrix
        sim_matrix = q_emb @ self._db_embeddings.T

        for i, (name, key) in enumerate(
            zip(need_embedding_names, need_embedding_keys)
        ):
            scores = sim_matrix[i]
            top_indices = np.argsort(scores)[::-1][:10]

            found = False
            for idx in top_indices:
                score = float(scores[idx])
                if score < self._threshold:
                    break

                entry = self._index[idx]
                if _validate_match(name, entry["name"]):
                    result = self._build_result(entry, score)
                    self._cache[key] = result
                    self._dirty = True
                    results[key] = result
                    found = True
                    logger.debug(
                        f"Embedding match '{name}' -> '{entry['name']}' "
                        f"(cos={score:.3f})"
                    )
                    break

            if not found:
                self._cache[key] = {
                    "not_found": True,
                    "cached_at": datetime.now().isoformat(),
                }
                self._dirty = True
                results[key] = None
                logger.debug(f"No valid match for '{name}'")

        # Save cache
        self.save_cache()
        logger.info(
            f"Batch match complete: {sum(1 for v in results.values() if v)} / "
            f"{len(results)} matched "
            f"({exact_hits} exact + "
            f"{sum(1 for v in results.values() if v) - exact_hits} embedding)"
        )
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(entry: Dict[str, Any], score: float) -> Dict[str, Any]:
        """
        Build a nutrition result dict from an OpenNutrition entry.

        Maps OpenNutrition field names to the format expected by
        the recipe enricher's _compute_nutrition_profile.
        """
        return {
            "energy_kcal": entry.get("kcal", 0),
            "protein_g": entry.get("protein", 0),
            "fat_g": entry.get("fat", 0),
            "carbs_g": entry.get("carbs", 0),
            "fiber_g": entry.get("fiber", 0),
            "sugar_g": entry.get("sugar", 0),
            "saturated_fat_g": entry.get("sat_fat", 0),
            "on_id": entry.get("id", ""),
            "on_description": entry.get("name", ""),
            "similarity_score": round(score, 3),
            "matching": "bge-small-embedding",
            "cached_at": datetime.now().isoformat(),
        }

    # Unit adjectives to strip during normalization (e.g. "small cloves" → "cloves")
    _UNIT_ADJECTIVES = {
        "small", "large", "big", "medium", "heaped", "heaping",
        "rounded", "level", "generous", "good", "thick", "thin",
        "whole", "fresh", "scant", "packed", "loosely", "tightly",
        "firmly", "lightly",
    }

    # Map of normalized unit aliases → canonical unit name
    _UNIT_ALIASES: Dict[str, str] = {
        # Spoons
        "tablespoon": "tbsp", "tablespoons": "tbsp",
        "teaspoon": "tsp", "teaspoons": "tsp",
        "dessertspoon": "tsp", "dessertspoons": "tsp",
        # Volume
        "cup": "cup", "cups": "cup",
        "liter": "l", "litre": "l", "liters": "l", "litres": "l",
        # Weight
        "gram": "g", "grams": "g",
        "kilogram": "kg", "kilograms": "kg",
        "ounce": "oz", "ounces": "oz",
        "pound": "lb", "pounds": "lb",
        # Piece-like
        "clove": "clove", "cloves": "clove",
        "sprig": "sprig", "sprigs": "sprig",
        "slice": "slice", "slices": "slice",
        "piece": "piece", "pieces": "piece",
        "bunch": "bunch", "bunches": "bunch",
        "leaf": "leaf", "leaves": "leaf",
        "stalk": "stalk", "stalks": "stalk",
        "head": "head", "heads": "head",
        "bulb": "bulb", "bulbs": "bulb",
        "spear": "spear", "spears": "spear",
        "sheet": "sheet", "sheets": "sheet",
        "strip": "strip", "strips": "strip",
        "fillet": "fillet", "filet": "fillet",
        "fillets": "fillet", "filets": "fillet",
        "can": "can", "cans": "can",
        "jar": "jar", "jars": "jar",
        "packet": "packet", "packets": "packet",
        "package": "packet", "packages": "packet",
        "stick": "stick", "sticks": "stick",
        "knob": "knob", "knobs": "knob",
        "handful": "handful", "handfuls": "handful",
        "drop": "drop", "drops": "drop",
        "square": "square", "squares": "square",
        "cube": "cube", "cubes": "cube",
    }

    # Ingredient-specific portion weights (lazy-loaded from JSON)
    _portion_weights: Optional[Dict[str, Dict[str, float]]] = None
    _PORTION_WEIGHTS_PATH = Path(__file__).parent.parent / "data" / "portion_weights.json"

    @classmethod
    def _get_portion_weights(cls) -> Dict[str, Dict[str, float]]:
        """Lazy-load ingredient-specific unit-to-gram conversions from USDA data."""
        if cls._portion_weights is None:
            if cls._PORTION_WEIGHTS_PATH.exists():
                with open(cls._PORTION_WEIGHTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cls._portion_weights = {
                    k: v for k, v in data.items() if not k.startswith("_")
                }
                logger.info(
                    f"Loaded {len(cls._portion_weights)} ingredient-specific "
                    f"portion weight entries"
                )
            else:
                cls._portion_weights = {}
                logger.warning(
                    f"Portion weights file not found at {cls._PORTION_WEIGHTS_PATH}"
                )
        return cls._portion_weights

    # All units that should trigger a PIECE_WEIGHTS lookup
    _PIECE_LIKE_UNITS = {
        "piece", "slice", "bunch", "sprig", "clove",
        "leaf", "stalk", "head", "bulb", "spear",
        "sheet", "strip", "fillet", "stick", "square",
    }

    # Default gram weights per unit type (used when ingredient not in PIECE_WEIGHTS)
    _DEFAULT_UNIT_GRAMS: Dict[str, float] = {
        "handful": 30.0,
        "knob": 15.0,
        "drop": 0.05,
        "leaf": 2.0,
        "sprig": 3.0,
        "stalk": 40.0,
        "head": 300.0,
        "bulb": 250.0,
        "spear": 20.0,
        "sheet": 15.0,
        "square": 5.0,
        "cube": 10.0,
        "stick": 15.0,
    }

    # Weight/volume units that should short-circuit compound unit parsing.
    # When these appear as the first word in "g bulbs" or "ml water",
    # return the unit directly since the rest is a descriptor.
    _WEIGHT_VOLUME_UNITS = {"g", "kg", "ml", "l", "cl", "dl", "oz", "lb"}

    @classmethod
    def _normalize_unit(cls, unit: str) -> str:
        """
        Normalize a unit string by stripping adjectives and resolving aliases.

        Examples:
            "small cloves" → "clove"
            "heaped tablespoons" → "tbsp"
            "g bulbs" → "g"
            "ml water" → "ml"
        """
        stripped = unit.lower().strip()
        if not stripped:
            return ""

        words = stripped.split()

        # Short-circuit: if first word is a weight/volume unit, return it
        # (handles compound units like "g bulbs", "ml water", "kg boneless")
        if words[0] in cls._WEIGHT_VOLUME_UNITS:
            return words[0]

        # Strip adjective prefixes
        core_words = [w for w in words if w not in cls._UNIT_ADJECTIVES]
        if not core_words:
            core_words = words

        # Try multi-word first, then first word, then last word
        candidate = " ".join(core_words)
        if candidate in cls._UNIT_ALIASES:
            return cls._UNIT_ALIASES[candidate]

        first_word = core_words[0]
        if first_word in cls._UNIT_ALIASES:
            return cls._UNIT_ALIASES[first_word]

        last_word = core_words[-1]
        if last_word in cls._UNIT_ALIASES:
            return cls._UNIT_ALIASES[last_word]

        return candidate

    @staticmethod
    def estimate_grams(
        quantity: Optional[float],
        unit: Optional[str],
        name_en: str,
    ) -> Optional[float]:
        """
        Estimate weight in grams for an ingredient quantity.

        Resolution layers (first match wins):
        - No unit → PIECE_WEIGHTS lookup ("2 eggs" → 2 × 60g)
        - Known unit (g, kg, tbsp, cup…) → direct conversion
        - Piece-like unit (clove, leaf, head…) → PIECE_WEIGHTS, then default
        - Default unit weight (handful → 30g, knob → 15g…)
        - None → unresolvable (handled by LLM fallback in enricher)

        Args:
            quantity: Numeric quantity (e.g., 200, 2, 0.5).
            unit: Unit of measurement (e.g., "g", "cup", "piece", None).
            name_en: English ingredient name (for piece weight lookup).

        Returns:
            Estimated weight in grams, or None if can't determine.
        """
        import re as _re
        from .nutrition_lookup import UNIT_TO_GRAMS, PIECE_WEIGHTS

        if quantity is None:
            return None

        # Pre-sort keys longest-first so "cherry tomato" matches before "tomato"
        _PIECE_KEYS_SORTED = sorted(PIECE_WEIGHTS, key=len, reverse=True)

        def _lookup_piece_weight(en_name: str) -> Optional[float]:
            name_lower = en_name.lower().strip()
            # 1. Exact match (fast path)
            if name_lower in PIECE_WEIGHTS:
                return quantity * PIECE_WEIGHTS[name_lower]
            # 2. Word-boundary match (longest key first to prefer specific matches)
            #    Prevents "egg" matching "eggplant" or "egg white"
            for key in _PIECE_KEYS_SORTED:
                if _re.search(rf'\b{_re.escape(key)}\b', name_lower):
                    return quantity * PIECE_WEIGHTS[key]
            return None

        def _lookup_portion_weight(en_name: str, unit_key: str) -> Optional[float]:
            """Look up ingredient-specific unit conversion from USDA portion data."""
            portion_data = NutritionMatcher._get_portion_weights()
            name_lower = en_name.lower().strip()

            # 1) Exact match
            entry = portion_data.get(name_lower)
            if entry and unit_key in entry:
                return quantity * entry[unit_key]

            # 2) Try each word of the ingredient name (e.g. "fresh cilantro" → "cilantro")
            words = name_lower.split()
            for word in reversed(words):
                entry = portion_data.get(word)
                if entry and unit_key in entry:
                    return quantity * entry[unit_key]

            # 3) Check if ingredient name contains a known portion key
            #    Only match keys >= 4 chars to avoid false positives
            for key in portion_data:
                if len(key) >= 4 and key in name_lower:
                    entry = portion_data[key]
                    if unit_key in entry:
                        return quantity * entry[unit_key]

            return None

        if unit is None:
            return _lookup_piece_weight(name_en)

        # Normalize unit: strip adjectives, resolve aliases, depluralize
        normalized = NutritionMatcher._normalize_unit(unit)

        # 0. Ingredient-specific unit conversion (USDA portion measures)
        #    e.g., "1 cup flour" = 125g, not 240g
        portion_result = _lookup_portion_weight(name_en, normalized)
        if portion_result is not None:
            return portion_result

        # 1. Generic unit conversion (fallback)
        if normalized in UNIT_TO_GRAMS and UNIT_TO_GRAMS[normalized] is not None:
            return quantity * UNIT_TO_GRAMS[normalized]

        # 2. Piece-like unit → ingredient-specific weight lookup
        if normalized in NutritionMatcher._PIECE_LIKE_UNITS:
            pw = _lookup_piece_weight(name_en)
            if pw is not None:
                return pw
            # 3. Default weight per unit type (e.g. leaf=2g, stalk=40g)
            if normalized in NutritionMatcher._DEFAULT_UNIT_GRAMS:
                return quantity * NutritionMatcher._DEFAULT_UNIT_GRAMS[normalized]

        # 3b. Units with default weights that aren't piece-like (handful, knob, drop)
        if normalized in NutritionMatcher._DEFAULT_UNIT_GRAMS:
            return quantity * NutritionMatcher._DEFAULT_UNIT_GRAMS[normalized]

        return None
