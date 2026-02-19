"""
Ingredient name translator — translates ingredient names to English
using a local incremental dictionary with LLM fallback for unknowns.

The dictionary grows over time as new ingredients are encountered.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Path to the translation dictionary
_DATA_DIR = Path(__file__).parent.parent / "data"
_TRANSLATIONS_FILE = _DATA_DIR / "ingredient_translations.json"


class IngredientTranslator:
    """
    Translates ingredient names to English using a local dictionary
    with LLM fallback for unknown terms.

    The dictionary is loaded from disk, and new translations are
    persisted back for future use.
    """

    def __init__(
        self,
        translations_path: Optional[Path] = None,
        openrouter_api_key: Optional[str] = None,
        model: str = "deepseek/deepseek-v3.2",
    ):
        """
        Initialize the translator.

        Args:
            translations_path: Path to the translations JSON file.
            openrouter_api_key: API key for OpenRouter (LLM fallback).
            model: Model to use for LLM translation fallback.
        """
        self._path = translations_path or _TRANSLATIONS_FILE
        self._model = model
        self._translations: Dict[str, str] = {}
        self._dirty = False  # Track if we need to save

        # Load existing translations
        self._load()

        # LLM client for fallback (lazy init)
        self._api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self._llm_client: Optional[AsyncOpenAI] = None

    def _load(self) -> None:
        """Load translations from disk, filtering out invalid entries."""
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter out metadata keys and invalid entries
            raw_count = 0
            filtered_count = 0
            self._translations = {}
            for k, v in data.items():
                if k.startswith("_"):
                    continue
                raw_count += 1
                if self._is_valid_ingredient_entry(k, v):
                    self._translations[k] = v
                else:
                    filtered_count += 1
            if filtered_count > 0:
                logger.warning(
                    f"Filtered out {filtered_count} invalid translation entries "
                    f"(of {raw_count} total)"
                )
                self._dirty = True  # Re-save to clean the file
            logger.info(f"Loaded {len(self._translations)} ingredient translations")
        else:
            self._translations = {}
            logger.warning(f"No translations file found at {self._path}")

    def save(self) -> None:
        """Persist translations to disk if changed."""
        if not self._dirty:
            return

        data = {
            "_meta": {
                "description": "Incremental FR/ES/IT/DE -> EN translation dictionary for ingredient names.",
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(self._translations),
            }
        }
        data.update(dict(sorted(self._translations.items())))

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._dirty = False
        logger.info(f"Saved {len(self._translations)} translations to {self._path}")

    def _normalize(self, name: str) -> str:
        """Normalize an ingredient name for dictionary lookup."""
        return name.strip().lower()

    @staticmethod
    def _is_valid_ingredient_entry(key: str, value: str) -> bool:
        """
        Validate that a key-value pair looks like a real ingredient translation.

        Rejects entries that are:
        - LLM error messages or prompt fragments leaked into the dictionary
        - Keys/values that are clearly not ingredient names
        """
        # Keys must contain at least one letter
        if not any(c.isalpha() for c in key):
            return False

        # Reject keys that look like LLM meta-responses
        key_lower = key.lower()
        if key_lower.startswith("[") or key_lower.startswith("{"):
            return False

        # Reject values that are full sentences (> 8 words) — ingredient names are short
        if len(value.split()) > 8:
            return False

        # Reject values containing common LLM refusal patterns
        value_lower = value.lower()
        refusal_patterns = [
            "i cannot", "i can't", "cannot translate", "not a complete",
            "please provide", "no ingredient", "the provided",
            "unable to extract", "not listed", "i notice that",
        ]
        for pattern in refusal_patterns:
            if pattern in value_lower:
                return False

        return True

    def lookup(self, name: str) -> Optional[str]:
        """
        Look up a translation in the local dictionary.

        Returns English name or None if not found.
        """
        normalized = self._normalize(name)
        return self._translations.get(normalized)

    def _is_already_english(self, name: str) -> bool:
        """Heuristic: check if name is likely already in English."""
        # Common English ingredient words
        english_markers = {
            "chicken", "beef", "pork", "butter", "cream", "flour",
            "sugar", "salt", "pepper", "oil", "egg", "milk", "water",
            "rice", "bread", "cheese", "onion", "garlic", "tomato",
            "potato", "carrot", "lemon", "honey", "vinegar", "wine",
            "mushroom", "spinach", "ginger", "vanilla", "chocolate",
            "cinnamon", "oregano", "basil", "thyme", "parsley",
        }
        words = set(name.lower().split())
        return bool(words & english_markers)

    async def translate_ingredients(
        self,
        ingredients: List[Dict],
    ) -> List[Tuple[Dict, str]]:
        """
        Translate a list of ingredient dicts, adding name_en to each.

        For each ingredient:
        1. Check if name is already English
        2. Look up in local dictionary
        3. Batch unknown ingredients via LLM

        Args:
            ingredients: List of ingredient dicts with at least 'name' key.

        Returns:
            List of (ingredient_dict, english_name) tuples.
        """
        results: List[Tuple[Dict, str]] = []
        unknowns: List[Tuple[int, str]] = []  # (index, original_name)

        for i, ing in enumerate(ingredients):
            name = ing.get("name", "")
            if not name:
                results.append((ing, ""))
                continue

            # 1. Already English?
            if self._is_already_english(name):
                results.append((ing, name))
                continue

            # 2. Dictionary lookup
            translated = self.lookup(name)
            if translated:
                results.append((ing, translated))
                continue

            # 3. Mark as unknown for batch LLM
            results.append((ing, ""))  # placeholder
            unknowns.append((i, name))

        # Batch translate unknowns via LLM
        if unknowns:
            logger.info(f"Translating {len(unknowns)} unknown ingredients via LLM")
            translations = await self._batch_translate_llm(
                [name for _, name in unknowns]
            )

            for (idx, original_name), english_name in zip(unknowns, translations):
                # Update result
                results[idx] = (results[idx][0], english_name)
                # Save to dictionary only if it looks like a valid ingredient entry
                normalized = self._normalize(original_name)
                if self._is_valid_ingredient_entry(normalized, english_name):
                    self._translations[normalized] = english_name
                    self._dirty = True
                    logger.debug(f"New translation: '{original_name}' -> '{english_name}'")
                else:
                    logger.warning(
                        f"Rejected invalid translation: '{original_name}' -> '{english_name}'"
                    )

            # Persist new translations
            self.save()

        return results

    async def _batch_translate_llm(self, names: List[str]) -> List[str]:
        """
        Translate a batch of ingredient names to English using LLM.

        Args:
            names: List of ingredient names to translate.

        Returns:
            List of English translations (same order).
        """
        if not self._api_key:
            logger.warning("No OpenRouter API key — returning original names as-is")
            return names

        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(
                api_key=self._api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/recipe-display",
                    "X-Title": "Ingredient Translator",
                },
            )

        # Build prompt
        ingredient_list = "\n".join(f"- {name}" for name in names)
        prompt = f"""Translate the following ingredient names to English.
Return ONLY the English translations, one per line, in the same order.
Use the most common culinary English name for each ingredient.
Do NOT add quantities, explanations, or numbering.

Ingredients:
{ingredient_list}"""

        try:
            response = await self._llm_client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a culinary translator. Translate ingredient names to their standard English culinary equivalent. Reply with one translation per line, nothing else.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
                temperature=0.0,
                extra_body={
                    "provider": {
                        "sort": "throughput",
                        "allow_fallbacks": True,
                    }
                },
            )

            result = response.choices[0].message.content or ""
            lines = [
                line.strip().lstrip("- ").lstrip("0123456789.)")
                for line in result.strip().split("\n")
                if line.strip()
            ]

            # Pad or trim to match input length
            while len(lines) < len(names):
                lines.append(names[len(lines)])  # fallback to original
            lines = lines[:len(names)]

            return lines

        except Exception as e:
            logger.error(f"LLM translation failed: {e}")
            return names  # Return originals as fallback
