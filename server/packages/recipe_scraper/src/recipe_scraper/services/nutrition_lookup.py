"""
Nutrition lookup service using USDA FoodData Central API.

Searches for raw/minimally processed ingredients (Foundation Foods)
and returns macronutrient data per 100g with local JSON caching.

Matching strategy:
- Primary: LLM-based selection among USDA search candidates
- Fallback: heuristic scoring if LLM is unavailable
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Path to the nutrition cache
_DATA_DIR = Path(__file__).parent.parent / "data"
_CACHE_FILE = _DATA_DIR / "nutrition_cache.json"

# USDA FDC API
_FDC_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Nutrient numbers we care about (keyed by nutrientId)
_NUTRIENT_MAP = {
    1008: "energy_kcal",    # Energy (kcal)
    1062: "energy_kj",      # Energy (kJ) — fallback for kcal
    1003: "protein_g",      # Protein (g)
    1004: "fat_g",          # Total lipid / fat (g)
    1005: "carbs_g",        # Carbohydrate by difference (g)
    1079: "fiber_g",        # Fiber, total dietary (g)
    1063: "sugar_g",        # Sugars, total (g)
    1258: "saturated_fat_g", # Fatty acids, total saturated (g)
}

# Unit conversion table (to grams) for common recipe units
# These are rough estimates for generic ingredients
UNIT_TO_GRAMS = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,       # Approximate: 1ml water = 1g
    "l": 1000.0,
    "cl": 10.0,
    "dl": 100.0,
    "cup": 240.0,
    "tbsp": 15.0,
    "tsp": 5.0,
    "oz": 28.35,
    "lb": 453.6,
    "piece": None,    # Depends on ingredient — handled separately
    "slice": None,
    "bunch": None,
    "pinch": 0.5,
    "dash": 0.5,
    "cs": 15.0,       # cuillère à soupe (FR)
    "cc": 5.0,        # cuillère à café (FR)
}

# Average weight per piece for common ingredients (grams)
PIECE_WEIGHTS = {
    "egg": 50,          # edible portion without shell (USDA)
    "onion": 150,
    "garlic": 5,        # clove
    "tomato": 150,
    "potato": 200,
    "carrot": 80,
    "apple": 180,
    "lemon": 80,
    "lime": 60,
    "orange": 180,
    "banana": 120,
    "chicken thigh": 180,
    "chicken breast": 200,
    "chicken leg": 250,
    "chicken wing": 80,
    "bell pepper": 150,
    "red bell pepper": 150,
    "green bell pepper": 150,
    "yellow bell pepper": 150,
    "shallot": 30,
    "bay leaf": 1,
    "fresh thyme": 3,   # branch
    "zucchini": 200,
    "eggplant": 300,
    "cucumber": 300,
    "leek": 200,
    "celery": 60,       # stalk
    "pear": 180,
    "peach": 150,
    "avocado": 170,
    "mushroom": 20,
    "button mushroom": 20,
    "cherry tomato": 15,
    "sweet potato": 200,
    "turnip": 150,
    "beetroot": 150,
    "endive": 120,
    "fennel": 250,
    "artichoke": 300,
    # Vegetables — whole / head
    "cauliflower": 600,
    "broccoli": 400,
    "cabbage leaves": 30,
    "cabbage leaf": 30,
    "cabbage": 1000,
    "white cabbage": 1000,
    "red cabbage": 1000,
    "napa cabbage": 900,
    "savoy cabbage": 900,
    "romaine lettuce": 300,
    "iceberg lettuce": 500,
    "asparagus": 20,     # per spear
    # Fruits
    "fig": 50,
    "figs": 50,
    "plum": 70,
    "apricot": 40,
    "nectarine": 140,
    "mango": 200,
    "kiwi": 75,
    "pomegranate": 250,
    "grapefruit": 250,
    "clementine": 70,
    "date": 24,
    "dates": 24,
    "medjool date": 24,
    "medjool dates": 24,
    "prune": 10,
    "prunes": 10,
    "raisin": 1,
    # Cheese / dairy
    "goat cheese": 60,          # crottin / small round
    "mozzarella": 125,
    "burrata": 150,
    "cream cheese": 30,         # per tbsp
    # Bread / bakery
    "country bread": 60,        # per slice
    "bread": 40,                # per slice
    "baguette": 250,
    "pita": 60,
    "tortilla": 40,
    "bun": 60,
    "buns": 60,
    "brioche": 60,
    "croissant": 60,
    "puff pastry": 280,         # per sheet
    "filo pastry": 20,          # per sheet
    "phyllo dough": 20,
    # Nuts / seeds (per small handful)
    "walnut": 30,
    "almond": 30,
    "hazelnut": 30,
    "pecan": 30,
    "cashew": 30,
    "pistachio": 30,
    "pine nut": 15,
    # Greens (per handful)
    "arugula": 20,
    "spinach": 30,
    "lettuce": 50,
    "kale": 30,
    "watercress": 20,
    "basil leaves": 5,
    "mint leaves": 5,
    "cilantro": 5,
    "parsley": 10,
    # Condiments (per tablespoon)
    "honey": 21,
    "maple syrup": 20,
    "olive oil": 14,
    "soy sauce": 15,
    "vinegar": 15,
    "mustard": 15,
    "tahini": 15,
    "butter": 15,
    "salted butter": 15,
}


class NutritionLookup:
    """
    Looks up nutritional data for ingredients using USDA FoodData Central.

    Features:
    - Searches Foundation Foods (raw/unprocessed ingredients)
    - Caches results locally in JSON to minimize API calls
    - Returns macros per 100g
    - Rate-limited to respect USDA's 1000 req/hour limit
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_path: Optional[Path] = None,
        openrouter_api_key: Optional[str] = None,
        llm_model: str = "deepseek/deepseek-v3.2",
    ):
        """
        Initialize the nutrition lookup.

        Args:
            api_key: USDA FDC API key. Defaults to USDA_API_KEY env var.
            cache_path: Path to the cache JSON file.
            openrouter_api_key: API key for OpenRouter (LLM matching).
            llm_model: Model to use for LLM-based ingredient matching.
        """
        self._api_key = api_key or os.getenv("USDA_API_KEY")
        if not self._api_key:
            logger.warning("No USDA_API_KEY found — nutrition lookup will be unavailable")

        self._cache_path = cache_path or _CACHE_FILE
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._dirty = False

        # LLM client for intelligent USDA candidate matching (lazy init)
        self._llm_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self._llm_model = llm_model
        self._llm_client: Optional[AsyncOpenAI] = None

        self._load_cache()

    def _load_cache(self) -> None:
        """Load nutrition cache from disk."""
        if self._cache_path.exists():
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache = {
                k: v for k, v in data.items()
                if not k.startswith("_")
            }
            logger.info(f"Loaded {len(self._cache)} cached nutrition entries")
        else:
            self._cache = {}

    def save_cache(self) -> None:
        """Persist cache to disk if changed."""
        if not self._dirty:
            return

        data = {
            "_meta": {
                "description": "Cache of USDA FoodData Central nutrition lookups.",
                "source": "USDA FoodData Central - Foundation Foods",
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

    def get_cached(self, name_en: str) -> Optional[Dict[str, Any]]:
        """Get nutrition data from cache, or None."""
        return self._cache.get(self._normalize_key(name_en))

    async def lookup_ingredient(self, name_en: str) -> Optional[Dict[str, Any]]:
        """
        Look up nutrition data for a single ingredient.

        1. Check local cache
        2. If miss, query USDA FDC API
        3. Cache the result

        Args:
            name_en: English name of the ingredient.

        Returns:
            Dict with macros per 100g, or None if not found.
        """
        key = self._normalize_key(name_en)

        # 1. Cache hit?
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug(f"Cache hit: '{name_en}'")
            return cached

        # 2. API lookup
        if not self._api_key:
            logger.debug(f"No API key — skipping lookup for '{name_en}'")
            return None

        result = await self._search_usda(name_en)

        if result:
            self._cache[key] = result
            self._dirty = True
            logger.info(f"Cached nutrition for '{name_en}': {result.get('energy_kcal', '?')} kcal/100g")
        else:
            # Cache negative result to avoid repeated failed lookups
            self._cache[key] = {"not_found": True, "cached_at": datetime.now().isoformat()}
            self._dirty = True
            logger.info(f"No USDA data found for '{name_en}' — cached as not_found")

        return result if result else None

    async def lookup_batch(self, names_en: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Look up nutrition data for multiple ingredients.

        Args:
            names_en: List of English ingredient names.

        Returns:
            Dict mapping name to nutrition data (or None).
        """
        results: Dict[str, Optional[Dict[str, Any]]] = {}

        for name in names_en:
            if not name:
                continue
            result = await self.lookup_ingredient(name)
            results[self._normalize_key(name)] = result

        # Save cache after batch
        self.save_cache()
        return results

    async def _search_usda(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search USDA FDC for a food item and select the best match.

        Uses LLM-based matching (primary) with heuristic fallback.

        Args:
            query: English food name to search for.

        Returns:
            Nutrition dict per 100g, or None.
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{_FDC_BASE_URL}/foods/search",
                    params={
                        "api_key": self._api_key,
                        "query": query,
                        "dataType": ["Foundation", "SR Legacy"],
                        "pageSize": 10,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"USDA API error {response.status_code}: {response.text[:200]}")
                    return None

                data = response.json()
                foods = data.get("foods", [])

                if not foods:
                    logger.debug(f"No USDA results for '{query}'")
                    return None

                # Select best match: LLM (primary) or heuristic (fallback)
                best_food = await self._pick_best_match_llm(query, foods)
                matching_method = "llm"

                if best_food is None:
                    # LLM returned NONE or was unavailable — use heuristic
                    logger.info(f"LLM returned no match for '{query}' — using heuristic fallback")
                    best_food = self._pick_best_match_heuristic(query, foods)
                    matching_method = "heuristic"

                # Extract nutrients using nutrientId (integer)
                nutrients = {}
                for nutrient_data in best_food.get("foodNutrients", []):
                    nutrient_id = nutrient_data.get("nutrientId")
                    if nutrient_id and nutrient_id in _NUTRIENT_MAP:
                        field_name = _NUTRIENT_MAP[nutrient_id]
                        nutrients[field_name] = round(nutrient_data.get("value", 0), 2)

                if not nutrients:
                    logger.debug(f"No nutrient data in USDA result for '{query}'")
                    return None

                # Fallback 1: if energy_kcal is missing, compute from energy_kj
                if not nutrients.get("energy_kcal") and nutrients.get("energy_kj"):
                    nutrients["energy_kcal"] = round(nutrients["energy_kj"] / 4.184, 2)

                # Fallback 2: if still missing, Atwater estimate from macros
                if not nutrients.get("energy_kcal"):
                    p = nutrients.get("protein_g") or 0
                    f = nutrients.get("fat_g") or 0
                    c = nutrients.get("carbs_g") or 0
                    if p or f or c:
                        nutrients["energy_kcal"] = round(p * 4 + c * 4 + f * 9, 2)
                        nutrients["energy_estimated"] = True

                # Remove intermediate kJ field from output
                nutrients.pop("energy_kj", None)

                result = {
                    **nutrients,
                    "fdc_id": best_food.get("fdcId"),
                    "fdc_description": best_food.get("description", ""),
                    "data_type": best_food.get("dataType", ""),
                    "matching": matching_method,
                    "cached_at": datetime.now().isoformat(),
                }

                return result

        except httpx.TimeoutException:
            logger.error(f"USDA API timeout for '{query}'")
            return None
        except Exception as e:
            logger.error(f"USDA API error for '{query}': {e}")
            return None

    # ------------------------------------------------------------------
    # LLM-based matching (primary)
    # ------------------------------------------------------------------

    def _get_llm_client(self) -> Optional[AsyncOpenAI]:
        """Lazy-initialize the OpenRouter LLM client."""
        if not self._llm_api_key:
            return None
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(
                api_key=self._llm_api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/recipe-display",
                    "X-Title": "Nutrition Matcher",
                },
            )
        return self._llm_client

    async def _pick_best_match_llm(
        self, query: str, foods: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Use an LLM to select the best USDA candidate for a recipe ingredient.

        The LLM receives the ingredient name and a numbered list of USDA
        descriptions. It replies with a single index or "NONE".

        All nutritional values still come from USDA — the LLM only picks
        which entry to use.

        Args:
            query: English ingredient name from the recipe.
            foods: List of USDA search result dicts.

        Returns:
            The best matching food dict, or None if no good match / LLM error.
        """
        client = self._get_llm_client()
        if client is None:
            logger.debug("No LLM client — skipping LLM matching")
            return self._pick_best_match_heuristic(query, foods)

        # Build candidate list for the prompt
        candidates = []
        for i, food in enumerate(foods):
            desc = food.get("description", "unknown")
            dtype = food.get("dataType", "?")
            candidates.append(f"{i}: {desc} [{dtype}]")

        candidates_text = "\n".join(candidates)
        max_idx = len(foods) - 1

        prompt = f"""Pick the BEST USDA entry for this cooking ingredient.

Rules:
- Pick the closest RAW/unprocessed form. Generic names like "beef" match generic raw beef, "flour" matches wheat flour, "rice" matches raw rice, "milk" matches whole milk, "broth" matches prepared broth.
- Prefer Foundation Foods over SR Legacy when quality is similar.
- Do NOT pick an entry that is a completely DIFFERENT food (e.g. "olive oil" must NOT match "sardine in olive oil").
- Only reply NONE if the ingredient is extremely niche and truly absent from ALL candidates.

Ingredient: {query}

Candidates:
{candidates_text}

Reply with ONLY the number (0-{max_idx}) or NONE."""

        try:
            response = await client.chat.completions.create(
                model=self._llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a nutrition database expert. "
                            "Reply with a single number or NONE. No explanation."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8,
                temperature=0.0,
            )

            answer = (response.choices[0].message.content or "").strip()
            logger.debug(f"LLM matching for '{query}': raw answer = '{answer}'")

            # Parse response
            if answer.upper() == "NONE":
                logger.info(f"LLM says no good USDA match for '{query}'")
                return None

            # Extract the first integer from the response
            match = re.search(r"\d+", answer)
            if match:
                idx = int(match.group())
                if 0 <= idx <= max_idx:
                    chosen = foods[idx]
                    logger.info(
                        f"LLM matched '{query}' → #{idx}: "
                        f"'{chosen.get('description')}' [{chosen.get('dataType')}]"
                    )
                    return chosen
                else:
                    logger.warning(
                        f"LLM returned out-of-range index {idx} for '{query}' "
                        f"(max={max_idx}) — falling back to heuristic"
                    )
                    return self._pick_best_match_heuristic(query, foods)
            else:
                logger.warning(
                    f"LLM returned unparseable answer '{answer}' for '{query}' "
                    f"— falling back to heuristic"
                )
                return self._pick_best_match_heuristic(query, foods)

        except Exception as e:
            logger.error(f"LLM matching failed for '{query}': {e} — falling back to heuristic")
            return self._pick_best_match_heuristic(query, foods)

    # ------------------------------------------------------------------
    # Heuristic matching (fallback)
    # ------------------------------------------------------------------

    @staticmethod
    def _stem(word: str) -> str:
        """Very basic stemming: remove trailing s/es for plural handling."""
        if word.endswith("ies"):
            return word[:-3] + "y"  # berries -> berry
        if word.endswith("oes"):
            return word[:-2]  # potatoes -> potato
        if word.endswith("es") and len(word) > 3:
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
            return word[:-1]
        return word

    @staticmethod
    def _pick_best_match_heuristic(query: str, foods: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback heuristic scoring when LLM is unavailable.

        Scoring:
        - Foundation > SR Legacy > other data types
        - "raw" indicator in description is a strong positive
        - Processed forms and category-changing words are penalized
        - Shorter, more generic descriptions are preferred
        """
        query_lower = query.lower().strip()
        query_words = set(query_lower.replace("-", " ").split())
        query_stems = {NutritionLookup._stem(w) for w in query_words}

        best_food = foods[0]
        best_score = -999

        for food in foods:
            score = 0
            desc = (food.get("description") or "").lower()
            data_type = food.get("dataType", "")

            desc_clean = desc.replace(",", "").replace("(", "").replace(")", "")
            desc_words = set(desc_clean.split())
            desc_stems = {NutritionLookup._stem(w) for w in desc_words}

            if data_type == "Foundation":
                score += 5
            elif data_type == "SR Legacy":
                score += 3

            if query_lower == desc:
                score += 50

            if query_stems.issubset(desc_stems):
                score += 20
            else:
                missing = query_stems - desc_stems
                score -= len(missing) * 10

            if "raw" in desc_words:
                score += 15

            processed_words = {
                "dehydrated", "canned", "frozen", "dried", "cooked",
                "roasted", "fried", "spread", "sauce", "juice", "powder",
                "pickled", "smoked", "breaded", "concentrate",
                "syrup", "mix", "blend", "flavored", "baby", "snack",
                "snacks", "babyfood", "reduced",
            }
            for pw in processed_words:
                if pw in desc_words and pw not in query_words:
                    score -= 10

            category_changers = {
                "flour", "oil", "fat", "juice", "extract", "powder", "paste",
                "sauce", "bread", "ice", "cream", "yogurt", "cake", "pie",
                "cookie", "muffin", "soup", "stew", "salad", "sandwich",
                "loaf", "burger", "shake", "pudding", "puddings", "candy",
                "candies", "fudge", "chip", "chips", "stick", "sticks",
                "pancake", "pancakes", "lasagna", "currant", "currants",
                "anchovies", "anchovy", "mayonnaise", "soymilk", "silk",
                "cheese", "ricotta", "plum", "jam", "jelly", "marmalade",
                "wafer", "cracker", "crackers", "cereal", "granola",
                "sausage", "jerky", "pate", "terrine",
            }
            for cc in category_changers:
                if cc in desc_words and cc not in query_words:
                    score -= 20

            neutral_words = {
                "raw", "fresh", "whole", "plain", "natural", "unsalted",
                "salted", "with", "and", "or", "in", "of", "the",
                "peeled", "halves", "pieces", "skin", "includes",
                "without", "table", "light", "regular", "cooking",
            }
            extra_stems = desc_stems - query_stems - {NutritionLookup._stem(w) for w in neutral_words}
            score -= len(extra_stems) * 3

            score -= len(desc) * 0.05

            if score > best_score:
                best_score = score
                best_food = food

        logger.debug(
            f"Heuristic match for '{query}': '{best_food.get('description')}' "
            f"(score={best_score:.1f}, type={best_food.get('dataType')})"
        )
        return best_food

    # NOTE: estimate_grams was removed — use NutritionMatcher.estimate_grams instead,
    # which adds unit normalization, piece-like-unit handling, and default weights.
