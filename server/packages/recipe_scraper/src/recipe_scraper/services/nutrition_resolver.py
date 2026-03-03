"""
Auto-resolution of unknown ingredients via tiered external sources.

Tier 1: USDA FoodData Central (authoritative, government data)
Tier 2: Perplexity sonar x2 via OpenRouter (web search, double-validated)

The LLM never generates nutrition values — it only selects USDA candidates
or extracts data from web search results. All entries are persisted in
resolved_ingredients.json with full provenance tracking.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_RESOLVED_FILE = _DATA_DIR / "resolved_ingredients.json"

_GARBAGE_PATTERNS = re.compile(
    r"^\[|"
    r"^additional\s|"
    r"^optional\s|"
    r"^anything\s|"
    r"^your (choice|favorite)|"
    r"^(add-ins|toppings|garnish|seasoning to taste|to taste|"
    r"for garnish|for serving|for frying|for greasing|as needed|"
    r"of your choice|desired|accompaniments|sides)$",
    re.IGNORECASE,
)

_MAX_CONCURRENT_USDA = 5
_USDA_DELAY = 0.15


def _is_garbage(name: str) -> bool:
    """Return True if the name is a parser artifact or generic placeholder."""
    if len(name) < 3:
        return True
    if _GARBAGE_PATTERNS.search(name):
        return True
    return False


def _atwater_check(kcal: float, protein: float, fat: float, carbs: float) -> bool:
    """
    Validate nutrition data with the Atwater formula.
    Accepts up to 20% deviation to account for alcohol, fiber calories, rounding.
    """
    if kcal <= 0:
        return protein == 0 and fat == 0 and carbs == 0
    estimated = protein * 4 + fat * 9 + carbs * 4
    deviation = abs(estimated - kcal) / max(kcal, 1)
    return deviation < 0.20


def _range_check(data: Dict[str, float]) -> bool:
    """Sanity-check that nutrition values are within plausible ranges."""
    kcal = data.get("kcal", 0)
    if not (0 <= kcal <= 902):
        return False
    for key in ("protein", "fat", "carbs", "fiber", "sugar", "sat_fat"):
        if data.get(key, 0) < 0:
            return False
    return True


class NutritionResolver:
    """
    Resolves unknown ingredients by querying external sources (USDA, Perplexity).

    Results are stored in resolved_ingredients.json and loaded by
    NutritionMatcher into its exact-match index on next startup.
    """

    def __init__(self):
        self._openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self._llm_client: Optional[AsyncOpenAI] = None

        self._resolved: Dict[str, Dict[str, Any]] = {}
        self._dirty = False
        self._load_resolved()

        from .nutrition_lookup import NutritionLookup
        self._usda = NutritionLookup()

    def _get_llm_client(self) -> Optional[AsyncOpenAI]:
        if not self._openrouter_key:
            return None
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(
                api_key=self._openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/recipe-display",
                    "X-Title": "Nutrition Resolver",
                },
            )
        return self._llm_client

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_resolved(self) -> None:
        if _RESOLVED_FILE.exists():
            with open(_RESOLVED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._resolved = {
                k: v for k, v in data.items() if not k.startswith("_")
            }
            logger.info(f"Loaded {len(self._resolved)} resolved ingredients")
        else:
            self._resolved = {}

    def _save_resolved(self) -> None:
        if not self._dirty:
            return

        usda_count = sum(1 for v in self._resolved.values() if v.get("source") == "usda")
        ppx_count = sum(1 for v in self._resolved.values() if v.get("source") == "perplexity")

        data: Dict[str, Any] = {
            "_meta": {
                "description": "Auto-resolved nutrition entries. source field indicates data provenance.",
                "total_entries": len(self._resolved),
                "usda_entries": usda_count,
                "perplexity_entries": ppx_count,
                "last_updated": datetime.now().isoformat(),
            }
        }
        data.update(dict(sorted(self._resolved.items())))

        _RESOLVED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_RESOLVED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._dirty = False
        logger.info(
            f"Saved {len(self._resolved)} resolved ingredients "
            f"(usda={usda_count}, perplexity={ppx_count})"
        )

    # ------------------------------------------------------------------
    # Deduplication helpers
    # ------------------------------------------------------------------

    def _find_by_name_or_alias(self, name_en: str) -> Optional[Dict[str, Any]]:
        """Check if name_en (or a known alias) already exists in resolved DB."""
        key = name_en.strip().lower()
        if key in self._resolved:
            return self._resolved[key]
        for entry in self._resolved.values():
            if key in [a.lower() for a in entry.get("alt", [])]:
                return entry
        return None

    def _find_by_fdc_id(self, fdc_id: int) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Check if a given fdc_id already exists in resolved DB."""
        for entry_key, entry in self._resolved.items():
            if entry.get("fdc_id") == fdc_id:
                return (entry_key, entry)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve_batch(
        self, unknown_names: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Resolve a batch of unknown ingredient names.

        Returns a dict mapping name_en (lowered) to resolved nutrition data,
        or None if resolution failed.
        """
        results: Dict[str, Optional[Dict[str, Any]]] = {}
        to_resolve: List[str] = []

        for name in unknown_names:
            key = name.strip().lower()
            if not key:
                continue

            if _is_garbage(key):
                logger.debug(f"Skipping garbage entry: '{key}'")
                results[key] = None
                continue

            existing = self._find_by_name_or_alias(key)
            if existing:
                logger.debug(f"Already resolved (name/alias): '{key}'")
                results[key] = existing
                continue

            to_resolve.append(key)

        if not to_resolve:
            return results

        logger.info(f"Resolving {len(to_resolve)} unknown ingredients...")

        _BATCH_SIZE = 20
        _TIMEOUT_PER_INGREDIENT = 30

        for batch_start in range(0, len(to_resolve), _BATCH_SIZE):
            batch = to_resolve[batch_start:batch_start + _BATCH_SIZE]
            batch_num = batch_start // _BATCH_SIZE + 1
            total_batches = (len(to_resolve) + _BATCH_SIZE - 1) // _BATCH_SIZE
            logger.info(
                f"Batch {batch_num}/{total_batches}: "
                f"resolving {len(batch)} ingredients..."
            )

            for name in batch:
                try:
                    data = await asyncio.wait_for(
                        self._resolve_single(name),
                        timeout=_TIMEOUT_PER_INGREDIENT,
                    )
                    results[name] = data
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout resolving '{name}' — skipping")
                    results[name] = None
                except Exception as e:
                    logger.error(f"Error resolving '{name}': {e}")
                    results[name] = None

                await asyncio.sleep(_USDA_DELAY)

            self._save_resolved()
            self._usda.save_cache()

        resolved_count = sum(1 for v in results.values() if v is not None)
        logger.info(
            f"Resolution complete: {resolved_count}/{len(unknown_names)} resolved"
        )
        return results

    # ------------------------------------------------------------------
    # Single ingredient resolution
    # ------------------------------------------------------------------

    async def _resolve_single(self, name_en: str) -> Optional[Dict[str, Any]]:
        """
        Try to resolve a single ingredient:
        1. USDA FDC (Tier 1)
        2. Perplexity x2 (Tier 2)
        """
        # Tier 1: USDA
        usda_result = await self._try_usda(name_en)
        if usda_result:
            return usda_result

        # Tier 2: Perplexity x2
        ppx_result = await self._try_perplexity(name_en)
        if ppx_result:
            return ppx_result

        logger.info(f"Unresolvable: '{name_en}'")
        return None

    # ------------------------------------------------------------------
    # Tier 1: USDA
    # ------------------------------------------------------------------

    async def _try_usda(self, name_en: str) -> Optional[Dict[str, Any]]:
        """Query USDA and validate the result."""
        result = await self._usda._search_usda(name_en)
        if not result:
            return None

        kcal = result.get("energy_kcal", 0)
        protein = result.get("protein_g", 0)
        fat = result.get("fat_g", 0)
        carbs = result.get("carbs_g", 0)

        if not _atwater_check(kcal, protein, fat, carbs):
            logger.warning(
                f"USDA result for '{name_en}' failed Atwater check "
                f"(kcal={kcal}, p={protein}, f={fat}, c={carbs})"
            )
            return None

        fdc_id = result.get("fdc_id")
        if fdc_id:
            existing = self._find_by_fdc_id(fdc_id)
            if existing:
                entry_key, entry = existing
                if name_en not in [a.lower() for a in entry.get("alt", [])]:
                    entry["alt"].append(name_en)
                    self._dirty = True
                    logger.info(
                        f"Added '{name_en}' as alias to existing entry '{entry_key}' "
                        f"(same fdc_id={fdc_id})"
                    )
                self._resolved[name_en] = entry
                return entry

        entry = {
            "name": name_en.title(),
            "alt": [],
            "kcal": round(kcal, 1),
            "protein": round(protein, 1),
            "fat": round(fat, 1),
            "carbs": round(carbs, 1),
            "fiber": round(result.get("fiber_g", 0), 1),
            "sugar": round(result.get("sugar_g", 0), 1),
            "sat_fat": round(result.get("saturated_fat_g", 0), 1),
            "source": "usda",
            "fdc_id": fdc_id,
            "fdc_description": result.get("fdc_description", ""),
            "original_query": name_en,
            "matching": result.get("matching", "unknown"),
            "resolved_at": datetime.now().isoformat(),
        }

        aliases = await self._generate_aliases(name_en)
        if aliases:
            entry["alt"] = aliases

        self._resolved[name_en] = entry
        self._dirty = True
        logger.info(f"Resolved '{name_en}' via USDA (fdc_id={fdc_id})")
        return entry

    # ------------------------------------------------------------------
    # Tier 2: Perplexity x2
    # ------------------------------------------------------------------

    async def _try_perplexity(self, name_en: str) -> Optional[Dict[str, Any]]:
        """Double-query Perplexity for nutrition data, then cross-validate."""
        client = self._get_llm_client()
        if not client:
            logger.debug("No OpenRouter key — skipping Perplexity tier")
            return None

        query1 = (
            f"What are the nutrition facts for {name_en} per 100g? "
            f"Give me: calories (kcal), protein (g), fat (g), carbs (g), "
            f"fiber (g), sugar (g), saturated fat (g). "
            f"Use authoritative sources like USDA, CIQUAL, or nutrition databases. "
            f"Reply ONLY with the numbers in this exact format: "
            f"kcal=X protein=X fat=X carbs=X fiber=X sugar=X sat_fat=X"
        )
        query2 = (
            f"Macronutrients of {name_en} per 100 grams: "
            f"calories, protein, total fat, carbohydrates, dietary fiber, "
            f"sugars, saturated fat. "
            f"Use reliable nutrition data (USDA FoodData Central, nutritionvalue.org). "
            f"Reply ONLY with numbers: "
            f"kcal=X protein=X fat=X carbs=X fiber=X sugar=X sat_fat=X"
        )

        data1 = await self._perplexity_query(client, query1)
        data2 = await self._perplexity_query(client, query2)

        if not data1 or not data2:
            logger.info(f"Perplexity returned no data for '{name_en}'")
            return None

        kcal1 = data1.get("kcal", 0)
        kcal2 = data2.get("kcal", 0)
        avg_kcal = (kcal1 + kcal2) / 2

        if avg_kcal > 0:
            delta_pct = abs(kcal1 - kcal2) / avg_kcal * 100
        elif kcal1 == 0 and kcal2 == 0:
            delta_pct = 0
        else:
            delta_pct = 100

        if delta_pct > 15:
            logger.warning(
                f"Perplexity convergence failed for '{name_en}': "
                f"kcal1={kcal1}, kcal2={kcal2}, delta={delta_pct:.1f}%"
            )
            return None

        merged = {}
        for key in ("kcal", "protein", "fat", "carbs", "fiber", "sugar", "sat_fat"):
            v1 = data1.get(key, 0)
            v2 = data2.get(key, 0)
            merged[key] = round((v1 + v2) / 2, 1)

        if not _atwater_check(merged["kcal"], merged["protein"], merged["fat"], merged["carbs"]):
            logger.warning(
                f"Perplexity result for '{name_en}' failed Atwater check: {merged}"
            )
            return None

        if not _range_check(merged):
            logger.warning(f"Perplexity result for '{name_en}' failed range check: {merged}")
            return None

        entry = {
            "name": name_en.title(),
            "alt": [],
            **merged,
            "source": "perplexity",
            "convergence_delta_pct": round(delta_pct, 1),
            "original_query": name_en,
            "resolved_at": datetime.now().isoformat(),
        }

        aliases = await self._generate_aliases(name_en)
        if aliases:
            entry["alt"] = aliases

        self._resolved[name_en] = entry
        self._dirty = True
        logger.info(f"Resolved '{name_en}' via Perplexity (delta={delta_pct:.1f}%)")
        return entry

    async def _perplexity_query(
        self, client: AsyncOpenAI, prompt: str
    ) -> Optional[Dict[str, float]]:
        """Send a single Perplexity query and parse the structured response."""
        try:
            response = await client.chat.completions.create(
                model="perplexity/sonar",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a nutrition data assistant. "
                            "Reply ONLY with the requested format. No explanation."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.0,
            )
            text = (response.choices[0].message.content or "").strip()
            return self._parse_nutrition_response(text)
        except Exception as e:
            logger.error(f"Perplexity query failed: {e}")
            return None

    @staticmethod
    def _parse_nutrition_response(text: str) -> Optional[Dict[str, float]]:
        """Parse 'kcal=X protein=X fat=X ...' format from LLM response."""
        fields = {}
        for key in ("kcal", "protein", "fat", "carbs", "fiber", "sugar", "sat_fat"):
            pattern = rf"{key}\s*[=:]\s*([\d.]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    fields[key] = float(match.group(1))
                except ValueError:
                    pass

        if "kcal" not in fields:
            return None
        return fields

    # ------------------------------------------------------------------
    # Alias generation
    # ------------------------------------------------------------------

    async def _generate_aliases(self, name_en: str) -> List[str]:
        """Ask LLM to generate 3-5 common alternative names for deduplication."""
        client = self._get_llm_client()
        if not client:
            return []

        try:
            response = await client.chat.completions.create(
                model="deepseek/deepseek-v3.2",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate alternative English names for cooking "
                            "ingredients. Reply ONLY with a comma-separated list. "
                            "No explanation."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"List 3-5 alternative names a recipe might use for: "
                            f"{name_en}\n\n"
                            f"Include common synonyms, spelling variants, and "
                            f"abbreviated forms. No duplicates."
                        ),
                    },
                ],
                max_tokens=80,
                temperature=0.0,
            )
            text = (response.choices[0].message.content or "").strip()
            aliases = [a.strip().lower() for a in text.split(",") if a.strip()]
            aliases = [a for a in aliases if a != name_en.lower() and len(a) >= 2]
            return aliases[:5]
        except Exception as e:
            logger.warning(f"Alias generation failed for '{name_en}': {e}")
            return []
