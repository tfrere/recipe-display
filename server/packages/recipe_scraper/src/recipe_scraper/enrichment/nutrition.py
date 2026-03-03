"""Nutrition profile computation, liquid retention heuristics, weight estimation, and tags."""

import asyncio
import json
import logging
import os
import re as _re
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Liquid retention heuristics
# ---------------------------------------------------------------------------

_LIQUID_KEYWORDS = {
    "broth", "stock", "bouillon", "fond",
    "wine", "white wine", "red wine", "beer", "cognac", "brandy", "marsala",
    "rum", "port", "sherry", "vermouth",
    "pasta water", "blanching water", "cooking water",
}

_ALCOHOL_KEYWORDS = {
    "wine", "white wine", "red wine", "beer", "cognac", "brandy", "marsala",
    "rum", "port", "sherry", "vermouth",
}

_DISCARD_KEYWORDS = {"pasta water", "blanching water", "cooking water"}

_SOUP_KEYWORDS = {
    "soupe", "soup", "velouté", "veloute", "potage", "bisque",
    "minestrone", "bouillon", "consommé", "consomme", "chowder",
    "gazpacho", "harira", "chorba",
}

_FRYING_OIL_KEYWORDS = {
    "peanut oil", "vegetable oil", "canola oil", "sunflower oil",
    "corn oil", "soybean oil", "frying oil", "neutral oil",
}
_CONFIT_FAT_KEYWORDS = {
    "duck fat", "goose fat", "lard", "schmaltz", "tallow",
    "rendered fat", "bacon fat", "beef dripping",
}
_FRYING_OIL_THRESHOLD_ML = 400.0

_LIQUID_RETENTION_FACTORS = {
    "discard": 0.0,
    "alcohol": 0.20,
    "soup_broth": 0.80,
    "braising": 0.30,
    "frying_oil": 0.15,
    "confit_fat": 0.20,
}
_LIQUID_VOLUME_THRESHOLD_ML = 250.0


def _is_soup_recipe(metadata: Dict[str, Any]) -> bool:
    title = (metadata.get("title") or "").lower()
    recipe_type = (metadata.get("type") or "").lower()
    combined = f"{title} {recipe_type}"
    return any(kw in combined for kw in _SOUP_KEYWORDS)


def _classify_liquid(name_en: str, is_soup: bool) -> Optional[str]:
    for kw in _DISCARD_KEYWORDS:
        if kw in name_en:
            return "discard"
    for kw in _ALCOHOL_KEYWORDS:
        if kw in name_en:
            return "alcohol"
    broth_keywords = {"broth", "stock", "bouillon", "fond"}
    for kw in broth_keywords:
        if kw in name_en:
            return "soup_broth" if is_soup else "braising"
    for kw in _CONFIT_FAT_KEYWORDS:
        if kw in name_en:
            return "confit_fat"
    for kw in _FRYING_OIL_KEYWORDS:
        if kw in name_en:
            return "frying_oil"
    if "oil" in name_en:
        return "frying_oil"
    return None


# ---------------------------------------------------------------------------
# Default quantities for ingredients commonly listed without a quantity.
# Based on USDA FNDDS "default amounts" methodology.
# Format: name_en_lower → (quantity, unit)
# ---------------------------------------------------------------------------

_DEFAULT_QUANTITIES: Dict[str, tuple] = {
    "olive oil": (1, "tbsp"),
    "extra-virgin olive oil": (1, "tbsp"),
    "extra virgin olive oil": (1, "tbsp"),
    "oil": (1, "tbsp"),
    "vegetable oil": (1, "tbsp"),
    "sunflower oil": (1, "tbsp"),
    "canola oil": (1, "tbsp"),
    "rapeseed oil": (1, "tbsp"),
    "coconut oil": (1, "tbsp"),
    "sesame oil": (1, "tsp"),
    "truffle oil": (1, "tsp"),
    "neutral oil": (1, "tbsp"),
    "frying oil": (2, "tbsp"),
    "butter": (1, "tbsp"),
    "unsalted butter": (1, "tbsp"),
    "salted butter": (1, "tbsp"),
    "ghee": (1, "tbsp"),
    "honey": (1, "tbsp"),
    "maple syrup": (1, "tbsp"),
    "agave syrup": (1, "tbsp"),
    "sugar": (1, "tsp"),
    "powdered sugar": (1, "tbsp"),
    "brown sugar": (1, "tsp"),
    "balsamic vinegar": (1, "tbsp"),
    "soy sauce": (1, "tbsp"),
    "fish sauce": (1, "tsp"),
    "sriracha": (1, "tsp"),
    "hot sauce": (1, "tsp"),
    "cream": (2, "tbsp"),
    "heavy cream": (2, "tbsp"),
    "sour cream": (1, "tbsp"),
    "feta cheese": (30, "g"),
    "parmesan": (10, "g"),
    "parmesan cheese": (10, "g"),
}


def _lookup_default_quantity(name_en: str) -> Optional[tuple]:
    """Return (quantity, unit) for an ingredient commonly listed without a qty."""
    key = name_en.strip().lower()
    if key in _DEFAULT_QUANTITIES:
        return _DEFAULT_QUANTITIES[key]
    for dq_key in sorted(_DEFAULT_QUANTITIES, key=len, reverse=True):
        if dq_key in key:
            return _DEFAULT_QUANTITIES[dq_key]
    return None


# ---------------------------------------------------------------------------
# Negligible ingredients
# ---------------------------------------------------------------------------

_ALWAYS_NEGLIGIBLE = {
    "salt", "table salt", "sea salt", "fleur de sel", "coarse salt",
    "kosher salt", "flaky salt", "himalayan salt", "smoked salt",
    "black pepper", "white pepper", "pepper", "peppercorns",
    "ground pepper", "cracked pepper", "szechuan pepper",
    "water", "ice", "ice water", "cold water", "hot water",
    "mineral water", "sparkling water", "boiling water",
    "baking soda", "baking powder",
    "cinnamon", "ground cinnamon", "nutmeg", "ground nutmeg",
    "paprika", "smoked paprika", "sweet paprika",
    "cumin", "ground cumin", "cumin seeds",
    "turmeric", "ground turmeric",
    "cayenne pepper", "cayenne", "chili powder", "chili flakes",
    "red pepper flakes", "crushed red pepper",
    "curry powder", "garam masala", "baharat",
    "cloves", "ground cloves", "allspice", "ground allspice",
    "cardamom", "ground cardamom", "cardamom pods",
    "coriander seeds", "ground coriander",
    "saffron", "saffron threads",
    "star anise", "anise seeds", "fennel seeds",
    "ras el hanout", "espelette pepper", "hot pepper",
    "za'atar", "sumac", "fenugreek", "mustard seeds",
    "caraway seeds", "celery seeds",
    "juniper berries", "mace", "grains of paradise",
    "msg", "monosodium glutamate",
    "sea salt flakes", "fleur de sel flakes", "maldon salt",
    "nigella seeds",
    "red deadnettle", "deadnettle", "cleavers",
    "dried pansies", "dried flowers", "edible flowers",
    "food coloring", "vanilla extract",
    "vanilla paste", "vanilla bean", "vanilla sugar",
    "cooking spray", "nonstick spray",
    "parchment paper", "wax paper", "aluminum foil", "plastic wrap",
    "cling film", "cheesecloth", "muslin cloth",
    "toothpicks", "toothpick", "skewers", "skewer",
    "bamboo skewers", "wooden skewers", "cocktail picks",
    "kitchen twine", "butcher's twine", "kitchen string",
    "paper towels", "paper towel",
    "cupcake liners", "muffin liners",
    "popsicle sticks", "ice cream sticks",
    "piping bag", "pastry bag",
}

_HERB_INGREDIENTS = {
    "basil", "basil leaves", "fresh basil",
    "parsley", "fresh parsley", "flat-leaf parsley",
    "cilantro", "fresh cilantro", "coriander leaves",
    "oregano", "fresh oregano",
    "thyme", "fresh thyme", "fresh thyme sprigs",
    "rosemary", "fresh rosemary",
    "chives", "fresh chives",
    "dill", "fresh dill",
    "mint", "fresh mint", "peppermint",
    "tarragon", "fresh tarragon",
    "bay leaf", "fresh bay leaf", "bay leaves",
    "sage", "fresh sage",
    "marjoram", "fresh marjoram",
}

_SMALL_HERB_UNITS = {
    "sprig", "sprigs", "leaf", "leaves", "pinch", "dash", "tsp", "teaspoon",
    "piece", "bunch", "handful", "stalk",  # herbs in these units are still negligible
    None,
}


# ---------------------------------------------------------------------------
# Weight estimation
# ---------------------------------------------------------------------------

_WEIGHT_CACHE_PATH = Path(__file__).parent.parent / "data" / "weight_estimates_cache.json"


def _load_weight_cache() -> Dict[str, float]:
    if _WEIGHT_CACHE_PATH.exists():
        try:
            with open(_WEIGHT_CACHE_PATH) as f:
                data = json.load(f)
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_weight_cache(cache: Dict[str, float]) -> None:
    data = {
        "_meta": {
            "description": "LLM-estimated weight per unit for ingredients (grams).",
            "format": "cache_key → grams_per_unit.",
        }
    }
    data.update(dict(sorted(cache.items())))
    _WEIGHT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_WEIGHT_CACHE_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _weight_cache_key(unit: Optional[str], name_en: str) -> str:
    from ..services.nutrition_matcher import NutritionMatcher
    normalized = NutritionMatcher._normalize_unit(unit) if unit else "none"
    return f"{normalized}|{name_en.lower().strip()}"


def _get_weight_llm_client():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None
    from openai import AsyncOpenAI
    return AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/recipe-display",
            "X-Title": "Weight Estimator",
        },
    )


async def _batch_estimate_weights_llm(lines: List[str]) -> List[Optional[float]]:
    client = _get_weight_llm_client()
    if client is None:
        logger.warning("No OpenRouter API key — skipping LLM weight estimation")
        return [None] * len(lines)

    numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
    prompt = f"""Estimate the total weight in grams for each ingredient line.
Reply with ONLY one number per line (the weight in grams), in the same order.
Use common culinary knowledge. No units, no text, just the number.

{numbered}"""

    try:
        response = await client.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[
                {
                    "role": "system",
                    "content": "You are a culinary expert. Estimate ingredient weights in grams. Reply with one number per line, nothing else.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=256,
            temperature=0.0,
            extra_body={"provider": {"sort": "throughput", "allow_fallbacks": True}},
        )
        result_text = response.choices[0].message.content or ""
        result_lines = [l.strip() for l in result_text.strip().split("\n") if l.strip()]

        estimates: List[Optional[float]] = []
        for line in result_lines:
            m = _re.search(r"[\d.]+", line)
            estimates.append(float(m.group()) if m else None)

        while len(estimates) < len(lines):
            estimates.append(None)
        return estimates[:len(lines)]
    except Exception as e:
        logger.error(f"LLM weight estimation failed: {e}")
        return [None] * len(lines)


async def fill_missing_weights_llm(
    ingredients: List[Dict[str, Any]],
    nutrition_data: Dict[str, Any],
) -> None:
    """
    For ingredients where estimate_grams returns None, ask an LLM
    to estimate the weight per unit and cache the result.
    """
    from ..services.nutrition_matcher import NutritionMatcher

    cache = _load_weight_cache()
    to_ask: List[Dict[str, Any]] = []

    for ing in ingredients:
        name_en = ing.get("name_en", "")
        if not name_en:
            continue
        key = name_en.strip().lower()
        nut = nutrition_data.get(key)
        if not nut or nut.get("not_found"):
            continue
        qty = ing.get("quantity")
        unit = ing.get("unit")
        grams = NutritionMatcher.estimate_grams(qty, unit, name_en)
        if grams is not None:
            continue
        if qty is None or not isinstance(qty, (int, float)):
            continue
        ck = _weight_cache_key(unit, name_en)
        if ck in cache:
            ing["estimatedWeightGrams"] = qty * cache[ck]
            continue
        to_ask.append(ing)

    if not to_ask:
        return

    logger.info(f"Estimating weights via LLM for {len(to_ask)} unresolved ingredients...")
    lines = [f"{ing.get('quantity', 1)} {ing.get('unit') or 'piece'} {ing.get('name_en', '')}" for ing in to_ask]
    estimates = await _batch_estimate_weights_llm(lines)

    for ing, est_grams in zip(to_ask, estimates):
        if est_grams is None or est_grams <= 0:
            continue
        if est_grams > 2_000:
            logger.warning(f"LLM weight estimate {est_grams}g for '{ing.get('name_en')}' exceeds 2kg — ignoring")
            continue
        qty = ing.get("quantity", 1) or 1
        if not isinstance(qty, (int, float)):
            try:
                qty = float(qty)
            except (ValueError, TypeError):
                qty = 1
        unit = ing.get("unit")
        name_en = ing.get("name_en", "")
        per_unit = est_grams / qty
        ck = _weight_cache_key(unit, name_en)
        cache[ck] = round(per_unit, 1)
        ing["estimatedWeightGrams"] = round(est_grams, 1)
        logger.info(f"LLM weight: '{ck}' → {per_unit:.1f}g/unit (total {est_grams:.1f}g)")

    _save_weight_cache(cache)


# ---------------------------------------------------------------------------
# LLM quantity estimation (Layer 2 — recipe-context aware)
# ---------------------------------------------------------------------------

_QTY_ESTIMATE_CACHE_PATH = _DATA_DIR / "qty_estimates_cache.json"


def _load_qty_estimate_cache() -> Dict[str, Dict[str, Any]]:
    if _QTY_ESTIMATE_CACHE_PATH.exists():
        with open(_QTY_ESTIMATE_CACHE_PATH) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


def _save_qty_estimate_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    data = {
        "_meta": {
            "description": "LLM-estimated quantities for ingredients missing qty+unit.",
            "format": "cache_key → {quantity, unit, rationale}",
        }
    }
    data.update(dict(sorted(cache.items())))
    _QTY_ESTIMATE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_QTY_ESTIMATE_CACHE_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _batch_estimate_quantities_llm(
    items: List[Dict[str, Any]],
    recipe_context: str,
    steps_text: str = "",
) -> List[Optional[Dict[str, Any]]]:
    """Ask an LLM to estimate quantity+unit for ingredients missing quantities.

    Uses structured JSON output to get reliable, parseable responses with
    a mandatory confidence field. Only "high" confidence estimates are
    considered reliable enough to use in nutrition calculations.

    The full recipe steps are passed so the LLM can distinguish usage
    context (e.g. "heat oil for deep frying" vs "drizzle olive oil").

    Model choice (Feb 2026):
        google/gemini-2.0-flash-001 via OpenRouter
        - $0.10/M input, $0.40/M output (vs DeepSeek V3: $0.20/$0.80)
        - Native JSON schema support (response_format with strict schema)
        - Well-calibrated: says "null" when uncertain instead of hallucinating
        For ~873 recipes × ~10 ingredients/call ≈ $0.05–0.10 total.
    """
    client = _get_weight_llm_client()
    if client is None:
        logger.warning("No OpenRouter API key — skipping LLM quantity estimation")
        return [None] * len(items)

    ingredient_lines = []
    for i, item in enumerate(items):
        line = f'{i+1}. "{item["name_en"]}"'
        if item.get("unit") and item["unit"] != "none":
            line += f" (unit from source: {item['unit']})"
        if item.get("notes"):
            line += f' — notes: "{item["notes"]}"'
        if item.get("preparation"):
            line += f' — prep: "{item["preparation"]}"'
        ingredient_lines.append(line)
    numbered = "\n".join(ingredient_lines)

    all_ingredients_ctx = item.get("all_ingredients_summary", "")

    steps_section = ""
    if steps_text:
        steps_section = f"""
Recipe steps (use these to understand HOW each ingredient is used):
{steps_text}
"""

    prompt = f"""Recipe: {recipe_context}

Other ingredients in the recipe (for context):
{all_ingredients_ctx}
{steps_section}
The following ingredients have NO numeric quantity in the original recipe.
Your job: determine if a reasonable, precise quantity can be inferred.
Use the recipe steps above to understand how each ingredient is used
(frying vs drizzling, garnish vs main component, etc.).

{numbered}

For EACH ingredient, respond with a JSON object in the array.

CRITICAL RULES — read carefully:
- "confidence" is mandatory. Use ONLY these values:
  • "high"   → you are certain (e.g. "1 tbsp olive oil for drizzling" is clearly ~1 tbsp)
  • "medium" → plausible guess but context is ambiguous (e.g. "olive oil" with no prep info)
  • null     → impossible to determine (decorative, "to taste", composite sub-recipe, frying oil)
- When confidence is null, set quantity and unit to null too.
- When confidence is "medium", still provide your best estimate, but it will be flagged.
- NEVER invent a quantity when the recipe says "to taste", "as needed", "for frying",
  "for greasing", or similar open-ended instructions. Those are null.
- If the steps say "deep fry", "fill a pot with oil", or similar → the oil quantity is null.
- If the steps say "drizzle", "brush", "grease" → a small known amount can be estimated.
- If the name_en contains a full quantity string (e.g. "1 cup plus 2 tbsp flour"),
  extract and convert it — do NOT re-estimate.
- Use standard units: g, ml, tbsp, tsp, cup, piece, pinch.
- The rationale must explain WHY you chose this quantity in ≤15 words."""

    json_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "quantity_estimates",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "estimates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "quantity": {"type": ["number", "null"]},
                                "unit": {"type": ["string", "null"]},
                                "confidence": {
                                    "type": ["string", "null"],
                                    "enum": ["high", "medium", None],
                                },
                                "rationale": {"type": "string"},
                            },
                            "required": ["quantity", "unit", "confidence", "rationale"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["estimates"],
                "additionalProperties": False,
            },
        },
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional chef estimating missing ingredient "
                "quantities. You value accuracy over completeness: it is "
                "ALWAYS better to return null than to guess wrong. "
                "Return a JSON object with an 'estimates' array."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    model = "google/gemini-2.0-flash-001"
    extra = {"provider": {"sort": "throughput", "allow_fallbacks": True}}

    try:
        # ── Pass 1: deterministic estimate (temp=0) ──────────────────
        response = await client.chat.completions.create(
            model=model, messages=messages,
            max_tokens=1024, temperature=0.0,
            response_format=json_schema, extra_body=extra,
        )

        result_text = response.choices[0].message.content or "{}"
        parsed = json.loads(result_text)
        raw_estimates = parsed.get("estimates", [])

        estimates: List[Optional[Dict[str, Any]]] = []
        for est in raw_estimates:
            conf = est.get("confidence")
            qty = est.get("quantity")
            unit = est.get("unit")

            if conf is None or qty is None or unit is None:
                estimates.append(None)
            else:
                estimates.append({
                    "quantity": qty,
                    "unit": unit.strip().lower() if unit else None,
                    "confidence": conf,
                    "rationale": est.get("rationale", ""),
                })

        while len(estimates) < len(items):
            estimates.append(None)
        estimates = estimates[: len(items)]

        # ── Pass 2: self-consistency for "medium" estimates ──────────
        # Run 3 more calls at temp=0.3. If the quantities converge
        # (CV < 30%), promote to "high". Otherwise keep "medium".
        #
        # This is the same principle as the Perplexity x2 convergence
        # check in NutritionResolver, but applied to quantity estimation.
        _SC_RUNS = 3
        _SC_TEMP = 0.3
        _SC_MAX_CV = 0.30  # coefficient of variation threshold

        medium_indices = [
            i for i, est in enumerate(estimates)
            if est is not None and est.get("confidence") == "medium"
        ]

        if medium_indices:
            logger.info(
                f"Self-consistency check on {len(medium_indices)} medium estimates "
                f"({_SC_RUNS} runs at temp={_SC_TEMP})"
            )

            sc_responses = await asyncio.gather(*(
                client.chat.completions.create(
                    model=model, messages=messages,
                    max_tokens=1024, temperature=_SC_TEMP,
                    response_format=json_schema, extra_body=extra,
                )
                for _ in range(_SC_RUNS)
            ))

            sc_all_estimates: List[List[Optional[Dict]]] = []
            for sc_resp in sc_responses:
                sc_text = sc_resp.choices[0].message.content or "{}"
                sc_parsed = json.loads(sc_text).get("estimates", [])
                sc_row: List[Optional[Dict]] = []
                for est in sc_parsed:
                    qty = est.get("quantity") if est else None
                    if qty is not None and est.get("confidence") is not None:
                        sc_row.append({"quantity": qty, "unit": est.get("unit")})
                    else:
                        sc_row.append(None)
                while len(sc_row) < len(items):
                    sc_row.append(None)
                sc_all_estimates.append(sc_row[:len(items)])

            for idx in medium_indices:
                base_est = estimates[idx]
                base_qty = base_est["quantity"]
                samples = [base_qty]

                for sc_row in sc_all_estimates:
                    sc_est = sc_row[idx] if idx < len(sc_row) else None
                    if sc_est is not None and sc_est.get("quantity") is not None:
                        samples.append(sc_est["quantity"])

                if len(samples) < 3:
                    continue

                mean = sum(samples) / len(samples)
                if mean <= 0:
                    continue

                variance = sum((s - mean) ** 2 for s in samples) / len(samples)
                std = variance ** 0.5
                cv = std / mean

                if cv <= _SC_MAX_CV:
                    median = sorted(samples)[len(samples) // 2]
                    base_est["quantity"] = round(median, 2)
                    base_est["confidence"] = "high"
                    base_est["rationale"] = (
                        f"[SC {len(samples)} runs, CV={cv:.0%}] "
                        + base_est.get("rationale", "")
                    )
                    logger.info(
                        f"  SC promoted: '{items[idx]['name_en']}' → "
                        f"{median} {base_est['unit']} "
                        f"(samples={samples}, CV={cv:.0%})"
                    )
                else:
                    base_est["rationale"] = (
                        f"[SC {len(samples)} runs, CV={cv:.0%} > {_SC_MAX_CV:.0%}, kept medium] "
                        + base_est.get("rationale", "")
                    )
                    logger.info(
                        f"  SC kept medium: '{items[idx]['name_en']}' "
                        f"(samples={samples}, CV={cv:.0%})"
                    )

        return estimates

    except Exception as e:
        logger.error(f"LLM quantity estimation failed: {e}")
        return [None] * len(items)


async def estimate_missing_quantities_llm(
    ingredients: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Estimate missing ingredient quantities using an LLM with recipe context.

    Only applies estimates with confidence="high". Medium-confidence estimates
    are stored in the ingredient as quantityEstimate for transparency but do NOT
    overwrite quantity (it stays None, so the ingredient is excluded from
    nutrition calculations rather than counted with a guess).

    Returns the number of ingredients where quantity was set (high confidence only).
    """
    from ..services.nutrition_matcher import NutritionMatcher

    meta = metadata or {}
    title = meta.get("title", "Unknown recipe")
    servings = meta.get("servings", 4)
    recipe_type = meta.get("recipeType", "")
    recipe_context = f'"{title}", {servings} servings, type={recipe_type}'

    # Build a summary of ALL ingredients for context
    all_ing_lines = []
    for ing in ingredients:
        name = ing.get("name_en") or ing.get("name") or "?"
        qty = ing.get("quantity")
        unit = ing.get("unit") or ""
        if qty is not None:
            all_ing_lines.append(f"  {qty} {unit} {name}".strip())
        else:
            all_ing_lines.append(f"  ? {unit} {name}".strip())
    all_ingredients_summary = "\n".join(all_ing_lines)

    # Build a condensed version of recipe steps for context
    steps_text = ""
    if steps:
        step_lines = []
        for i, step in enumerate(steps, 1):
            action = step.get("action", "")
            if action:
                step_lines.append(f"  {i}. {action}")
        steps_text = "\n".join(step_lines)

    cache = _load_qty_estimate_cache()
    to_ask: List[Dict[str, Any]] = []
    to_ask_indices: List[int] = []

    for i, ing in enumerate(ingredients):
        name_en = ing.get("name_en", "")
        if not name_en:
            continue
        key = name_en.strip().lower()
        if key in _ALWAYS_NEGLIGIBLE:
            continue
        if key in _HERB_INGREDIENTS:
            unit = (ing.get("unit") or "").strip().lower()
            normalized_unit = NutritionMatcher._normalize_unit(unit) if unit else None
            if normalized_unit in _SMALL_HERB_UNITS or not unit:
                continue

        qty = ing.get("quantity")
        unit = ing.get("unit")
        if qty is not None:
            continue

        cache_key = f"{unit or 'none'}|{key}"
        if cache_key in cache:
            cached = cache[cache_key]
            cached_conf = cached.get("confidence", "high")
            if cached_conf == "high":
                ing["quantity"] = cached["quantity"]
                ing["unit"] = cached["unit"]
                ing["quantitySource"] = "estimated"
                ing["quantityRationale"] = cached.get("rationale", "")
            else:
                ing["quantityEstimate"] = {
                    "quantity": cached["quantity"],
                    "unit": cached["unit"],
                    "confidence": cached_conf,
                    "rationale": cached.get("rationale", ""),
                }
                ing["quantitySource"] = "estimated_low"
            continue

        to_ask.append({
            "name_en": name_en,
            "unit": unit or "none",
            "notes": ing.get("notes") or "",
            "preparation": ing.get("preparation") or "",
            "all_ingredients_summary": all_ingredients_summary,
        })
        to_ask_indices.append(i)

    if not to_ask:
        return 0

    logger.info(
        f"Estimating quantities via LLM for {len(to_ask)} ingredients "
        f"(recipe: '{title}')"
    )
    estimates = await _batch_estimate_quantities_llm(to_ask, recipe_context, steps_text)

    estimated_count = 0
    for idx, item, estimate in zip(to_ask_indices, to_ask, estimates):
        ing = ingredients[idx]
        cache_key = f"{item['unit']}|{item['name_en'].lower().strip()}"

        if estimate is None:
            cache[cache_key] = {
                "quantity": None, "unit": None,
                "confidence": None, "rationale": "LLM returned null",
            }
            continue

        est_qty = estimate["quantity"]
        est_unit = estimate["unit"]
        est_conf = estimate.get("confidence", "medium")
        est_rationale = estimate.get("rationale", "")

        if est_qty <= 0 or est_qty > 5000:
            logger.warning(
                f"LLM qty estimate {est_qty} {est_unit} for "
                f"'{item['name_en']}' — out of range, treating as null"
            )
            cache[cache_key] = {
                "quantity": est_qty, "unit": est_unit,
                "confidence": None, "rationale": f"out of range: {est_rationale}",
            }
            continue

        cache[cache_key] = {
            "quantity": est_qty,
            "unit": est_unit,
            "confidence": est_conf,
            "rationale": est_rationale,
        }

        if est_conf == "high":
            ing["quantity"] = est_qty
            ing["unit"] = est_unit
            ing["quantitySource"] = "estimated"
            ing["quantityRationale"] = est_rationale
            estimated_count += 1
            logger.info(
                f"Qty estimate (high): '{item['name_en']}' → "
                f"{est_qty} {est_unit} ({est_rationale})"
            )
        else:
            ing["quantityEstimate"] = {
                "quantity": est_qty,
                "unit": est_unit,
                "confidence": est_conf,
                "rationale": est_rationale,
            }
            ing["quantitySource"] = "estimated_low"
            logger.info(
                f"Qty estimate ({est_conf}, not applied): '{item['name_en']}' → "
                f"{est_qty} {est_unit} ({est_rationale})"
            )

    if to_ask:
        _save_qty_estimate_cache(cache)

    return estimated_count


# ---------------------------------------------------------------------------
# Default piece weight lookup
# ---------------------------------------------------------------------------

def default_piece_weight(name_en: str) -> Optional[float]:
    from ..services.nutrition_matcher import NutritionMatcher
    from ..services.nutrition_lookup import PIECE_WEIGHTS

    name_lower = name_en.strip().lower()
    portions = NutritionMatcher._get_portion_weights()
    entry = portions.get(name_lower)
    if entry and "piece" in entry:
        return entry["piece"]
    for word in reversed(name_lower.split()):
        entry = portions.get(word)
        if entry and "piece" in entry:
            return entry["piece"]
    if name_lower in PIECE_WEIGHTS:
        return PIECE_WEIGHTS[name_lower]
    for pw_key in sorted(PIECE_WEIGHTS, key=len, reverse=True):
        if _re.search(rf'\b{_re.escape(pw_key)}\b', name_lower):
            return PIECE_WEIGHTS[pw_key]
    return None


# ---------------------------------------------------------------------------
# Profile computation
# ---------------------------------------------------------------------------

def compute_nutrition_profile(
    ingredients: List[Dict[str, Any]],
    nutrition_data: Dict[str, Optional[Dict[str, Any]]],
    servings: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute per-serving nutritional profile from ingredient nutrition data.
    Applies liquid-retention heuristics for cooking liquids.
    """
    from ..services.nutrition_matcher import NutritionMatcher

    if not isinstance(servings, (int, float)) or servings <= 0:
        try:
            servings = max(1, round(float(servings)))
        except (ValueError, TypeError):
            servings = 4

    def _is_negligible(key: str, ing: dict) -> bool:
        if key in _ALWAYS_NEGLIGIBLE:
            return True
        if key in _HERB_INGREDIENTS:
            unit = (ing.get("unit") or "").strip().lower()
            normalized_unit = NutritionMatcher._normalize_unit(unit) if unit else None
            return normalized_unit in _SMALL_HERB_UNITS or not unit
        return False

    total = {
        "calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0,
        "sugar": 0.0, "saturatedFat": 0.0,
        "calcium": 0.0, "iron": 0.0, "magnesium": 0.0,
        "potassium": 0.0, "sodium": 0.0, "zinc": 0.0,
    }
    minerals_available = False
    resolved_count = 0
    matched_count = 0
    total_count = 0
    negligible_count = 0
    liquid_retention_applied = False
    issues: List[Dict[str, str]] = []
    ingredient_details: List[Dict[str, Any]] = []

    is_soup = _is_soup_recipe(metadata or {})

    for ing in ingredients:
        name_en = ing.get("name_en", "")
        name_orig = ing.get("name", "")

        if not name_en:
            total_count += 1
            ingredient_details.append({"name": name_orig or "?", "nameEn": "", "status": "no_translation"})
            issues.append({"ingredient": name_orig or "?", "issue": "no_translation", "detail": "Missing English name"})
            continue

        key = name_en.strip().lower()
        if _is_negligible(key, ing):
            negligible_count += 1
            continue

        total_count += 1
        nut = nutrition_data.get(key)
        if not nut or nut.get("not_found"):
            ingredient_details.append({"name": name_orig or key, "nameEn": key, "status": "no_match"})
            issues.append({"ingredient": key, "issue": "no_match", "detail": "Not found in nutrition index"})
            continue

        matched_count += 1

        # --- Fix broken fractions (e.g. qty=1, unit="/2 cup" → qty=0.5, unit="cup") ---
        _raw_unit = (ing.get("unit") or "")
        _raw_qty = ing.get("quantity")
        _frac_match = _re.match(r"^/(\d+)\s+(.*)", _raw_unit)
        if _frac_match:
            _divisor = int(_frac_match.group(1))
            ing = {**ing, "unit": _frac_match.group(2).strip(),
                   "quantity": max(_raw_qty or 1, 1) / _divisor}
            logger.debug("Fraction repair: %s %s → %s %s (%s)",
                         _raw_qty, _raw_unit, ing["quantity"], ing["unit"], name_en)
        elif (isinstance(_raw_qty, (int, float)) and _raw_qty > 50
              and (_raw_unit or "").strip().lower() in ("cup", "cups", "tbsp", "tsp")):
            issues.append({"ingredient": key, "issue": "implausible_quantity",
                           "detail": f"{_raw_qty} {_raw_unit} is implausible (likely broken fraction)"})
            ingredient_details.append({"name": name_orig or key, "nameEn": key,
                                       "status": "implausible_quantity"})
            continue

        quantity_estimated = False
        grams = ing.get("estimatedWeightGrams")
        if grams is None:
            grams = NutritionMatcher.estimate_grams(ing.get("quantity"), ing.get("unit"), name_en)
        if grams is None and ing.get("quantity") is None:
            dq = _lookup_default_quantity(name_en)
            if dq:
                dq_qty, dq_unit = dq
                grams = NutritionMatcher.estimate_grams(dq_qty, dq_unit, name_en)
                if grams and grams > 0:
                    quantity_estimated = True
        if grams is None and ing.get("quantity") is None:
            grams = default_piece_weight(name_en)
        if grams is None or grams <= 0:
            reason = "no quantity" if ing.get("quantity") is None else "weight estimation failed"
            ingredient_details.append({"name": name_orig or key, "nameEn": key, "status": "no_weight"})
            issues.append({"ingredient": key, "issue": "no_weight", "detail": f"Matched but {reason}"})
            continue

        retention = 1.0
        liquid_category = _classify_liquid(key, is_soup)
        if liquid_category is not None:
            unit_norm = (NutritionMatcher._normalize_unit(ing.get("unit") or "") or "").lower()
            _VOL_TO_ML = {"ml": 1.0, "l": 1000.0, "cl": 10.0, "dl": 100.0, "cup": 240.0, "tbsp": 15.0, "tsp": 5.0, "cs": 15.0, "cc": 5.0}
            qty = ing.get("quantity") or 0
            volume_ml = qty * _VOL_TO_ML.get(unit_norm, 1.0) if unit_norm in _VOL_TO_ML else grams
            threshold = _FRYING_OIL_THRESHOLD_ML if liquid_category in ("frying_oil", "confit_fat") else _LIQUID_VOLUME_THRESHOLD_ML
            if volume_ml > threshold:
                retention = _LIQUID_RETENTION_FACTORS.get(liquid_category, 1.0)
                liquid_retention_applied = True

        factor = (grams / 100.0) * retention
        ing_cal = round((nut.get("energy_kcal", 0) or 0) * factor, 1)
        ing_prot = round((nut.get("protein_g", 0) or 0) * factor, 1)
        ing_fat = round((nut.get("fat_g", 0) or 0) * factor, 1)
        ing_carbs = round((nut.get("carbs_g", 0) or 0) * factor, 1)
        ing_fiber = round((nut.get("fiber_g", 0) or 0) * factor, 1)
        ing_sugar = round((nut.get("sugar_g", 0) or 0) * factor, 1)
        ing_sat_fat = round((nut.get("saturated_fat_g", 0) or 0) * factor, 1)

        ing_calcium = round((nut.get("calcium_mg") or 0) * factor, 1)
        ing_iron = round((nut.get("iron_mg") or 0) * factor, 2)
        ing_magnesium = round((nut.get("magnesium_mg") or 0) * factor, 1)
        ing_potassium = round((nut.get("potassium_mg") or 0) * factor, 1)
        ing_sodium = round((nut.get("sodium_mg") or 0) * factor, 1)
        ing_zinc = round((nut.get("zinc_mg") or 0) * factor, 2)

        has_minerals = any(nut.get(k) is not None for k in ("calcium_mg", "iron_mg", "magnesium_mg", "potassium_mg", "sodium_mg", "zinc_mg"))
        if has_minerals:
            minerals_available = True

        total["calories"] += ing_cal
        total["protein"] += ing_prot
        total["fat"] += ing_fat
        total["carbs"] += ing_carbs
        total["fiber"] += ing_fiber
        total["sugar"] += ing_sugar
        total["saturatedFat"] += ing_sat_fat
        total["calcium"] += ing_calcium
        total["iron"] += ing_iron
        total["magnesium"] += ing_magnesium
        total["potassium"] += ing_potassium
        total["sodium"] += ing_sodium
        total["zinc"] += ing_zinc

        detail_entry: Dict[str, Any] = {
            "name": name_orig or key, "nameEn": key,
            "grams": round(grams * retention, 1),
            "calories": ing_cal, "protein": ing_prot, "fat": ing_fat,
            "carbs": ing_carbs, "fiber": ing_fiber,
            "sugar": ing_sugar, "saturatedFat": ing_sat_fat,
            "status": "resolved",
        }
        if has_minerals:
            detail_entry["minerals"] = {
                "calcium": ing_calcium, "iron": ing_iron, "magnesium": ing_magnesium,
                "potassium": ing_potassium, "sodium": ing_sodium, "zinc": ing_zinc,
            }
        qty = ing.get("quantity")
        unit = ing.get("unit")
        if qty is not None:
            detail_entry["quantity"] = qty
        if unit:
            detail_entry["unit"] = unit
        if quantity_estimated:
            detail_entry["quantityEstimated"] = True
        ingredient_details.append(detail_entry)
        resolved_count += 1

    if servings and servings > 0:
        for key in total:
            if key in ("iron", "zinc"):
                total[key] = round(total[key] / servings, 2)
            else:
                total[key] = round(total[key] / servings, 1)

    if total_count == 0:
        confidence = "none"
    elif resolved_count / total_count >= 0.9:
        confidence = "high"
    elif resolved_count / total_count >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    result = {
        "calories": total["calories"],
        "protein": total["protein"],
        "fat": total["fat"],
        "carbs": total["carbs"],
        "fiber": total["fiber"],
        "sugar": total["sugar"],
        "saturatedFat": total["saturatedFat"],
        "confidence": confidence,
        "resolvedIngredients": resolved_count,
        "matchedIngredients": matched_count,
        "totalIngredients": total_count,
        "negligibleIngredients": negligible_count,
        "source": "OpenNutrition",
    }
    if minerals_available and resolved_count > 0:
        mineral_details = [d for d in ingredient_details if d.get("status") == "resolved" and d.get("minerals")]
        mineral_coverage = len(mineral_details) / resolved_count
        if mineral_coverage >= 0.5:
            result["minerals"] = {
                "calcium": total["calcium"],
                "iron": total["iron"],
                "magnesium": total["magnesium"],
                "potassium": total["potassium"],
                "sodium": total["sodium"],
                "zinc": total["zinc"],
            }
            result["mineralCoverage"] = round(mineral_coverage, 2)
    if liquid_retention_applied:
        result["liquidRetentionApplied"] = True
    if issues:
        result["issues"] = issues
    if ingredient_details:
        result["ingredientDetails"] = ingredient_details
    return result


def derive_nutrition_tags(profile: Dict[str, Any]) -> List[str]:
    """Derive qualitative nutrition tags from the nutrition profile."""
    tags = []
    calories = profile.get("calories", 0)
    protein = profile.get("protein", 0)
    fat = profile.get("fat", 0)
    carbs = profile.get("carbs", 0)
    fiber = profile.get("fiber", 0)
    confidence = profile.get("confidence", "none")

    if confidence in ("none", "low"):
        return []

    if protein > 25:
        tags.append("high-protein")
    if 0 < calories < 400:
        tags.append("low-calorie")
    if fiber > 8:
        tags.append("high-fiber")
    if calories > 700 or fat > 40:
        tags.append("indulgent")
    if calories > 0:
        pct_protein = (protein * 4 / calories) * 100
        pct_carbs = (carbs * 4 / calories) * 100
        pct_fat = (fat * 9 / calories) * 100
        if 15 <= pct_protein <= 35 and 40 <= pct_carbs <= 65 and 20 <= pct_fat <= 35:
            tags.append("balanced")

    minerals = profile.get("minerals")
    if minerals:
        if (minerals.get("iron", 0) or 0) >= 5:
            tags.append("iron-rich")
        if (minerals.get("calcium", 0) or 0) >= 300:
            tags.append("calcium-rich")
    return tags
