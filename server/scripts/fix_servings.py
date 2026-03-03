"""
Fix suspect servings for recipes where servings=1 looks wrong.

Uses a single LLM call per recipe to determine the real number of portions
based on recipe title, type, ingredients list, and total calorie count.

The LLM returns a structured JSON with the corrected servings and a short
rationale. Results are cached to avoid re-processing.

Usage:
    python -m scripts.fix_servings [--dry-run] [--limit N] [--threshold 800]
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))

from dotenv import load_dotenv

load_dotenv(SERVER_ROOT / ".env")

from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RECIPES_DIR = SERVER_ROOT / "data" / "recipes"
RECIPES_OLD_DIR = SERVER_ROOT / "data" / "recipes_old"
CACHE_FILE = SERVER_ROOT / "data" / "constants" / "servings_fixes.json"

PROMPT = """\
You are a professional chef and food editor. Given a recipe, determine the \
realistic number of individual portions (servings) it produces.

Rules:
- A "portion" is what one person eats in one sitting for that meal type.
- For cakes, tarts, quiches, pies: count the slices (typically 6-8).
- For batch recipes (granola, jam, sauce, pâté): estimate portions by weight.
- For base components (pastry dough, stock): estimate how many recipes it serves.
- If servings=1 is actually correct (e.g. a single smoothie), keep 1.
- Answer ONLY with JSON, no commentary.

Recipe:
- Title: {title}
- Type: {recipe_type}
- Ingredients: {ingredients}
- Current servings: {servings}
- Total calories (whole recipe): {total_calories:.0f} kcal

Respond with this exact JSON format:
{{"servings": <int>, "rationale": "<1 sentence in English>"}}"""


def _get_llm_client() -> Optional[AsyncOpenAI]:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        logger.error("OPENROUTER_API_KEY not set")
        return None
    return AsyncOpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/recipe-display",
            "X-Title": "Servings Fixer",
        },
    )


def _load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def find_suspect_recipes(
    threshold: float = 800,
) -> List[tuple[Path, Dict[str, Any]]]:
    """Find recipes with servings=1 and calories above threshold."""
    suspects = []
    for recipes_dir in [RECIPES_DIR, RECIPES_OLD_DIR]:
        if not recipes_dir.exists():
            continue
        for path in sorted(recipes_dir.glob("*.recipe.json")):
            with open(path) as f:
                recipe = json.load(f)
            meta = recipe.get("metadata", {})
            servings = meta.get("servings", 0)
            if servings != 1:
                continue
            nut = meta.get("nutritionPerServing", {})
            cal = nut.get("calories", 0)
            if cal > threshold:
                suspects.append((path, recipe))
    return suspects


def _format_ingredients(recipe: Dict[str, Any]) -> str:
    parts = []
    for ing in recipe.get("ingredients", [])[:15]:
        q = ing.get("quantity")
        u = ing.get("unit") or ""
        name = ing.get("name", "")
        if q:
            parts.append(f"{q} {u} {name}".strip())
        else:
            parts.append(name)
    return ", ".join(parts)


async def fix_one(
    client: AsyncOpenAI,
    path: Path,
    recipe: Dict[str, Any],
    cache: Dict[str, Any],
    dry_run: bool,
) -> Optional[Dict[str, Any]]:
    slug = path.stem.replace(".recipe", "")
    meta = recipe.get("metadata", {})
    total_cal = meta.get("nutritionPerServing", {}).get("calories", 0)

    if slug in cache:
        entry = cache[slug]
        logger.info(f"  [cached] {slug} → {entry['servings']} servings")
    else:
        prompt = PROMPT.format(
            title=meta.get("title", "?"),
            recipe_type=meta.get("recipeType", "?"),
            ingredients=_format_ingredients(recipe),
            servings=meta.get("servings", 1),
            total_calories=total_cal,
        )

        try:
            resp = await client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            result = json.loads(raw)
        except Exception as e:
            logger.error(f"  [error] {slug}: {e}")
            return None

        new_servings = result.get("servings", 1)
        rationale = result.get("rationale", "")
        logger.info(f"  {slug}: 1 → {new_servings} servings ({rationale})")

        entry = {
            "servings": new_servings,
            "rationale": rationale,
            "original_calories_per_serving": total_cal,
            "corrected_calories_per_serving": round(total_cal / max(new_servings, 1), 1),
            "fixed_at": datetime.now().isoformat(),
        }
        cache[slug] = entry

    new_servings = entry["servings"]
    rationale = entry.get("rationale", "")

    if not dry_run and new_servings > 1:
        meta["servings"] = new_servings
        nut = meta.get("nutritionPerServing", {})
        if nut:
            for key in ("calories", "protein", "fat", "carbs", "fiber"):
                if key in nut:
                    nut[key] = round(nut[key] / new_servings, 1)
            meta["servingsCorrected"] = True
            meta["servingsCorrectionRationale"] = rationale
        with open(path, "w", encoding="utf-8") as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)
        logger.info(f"  [saved] {path.name}")

    return entry


async def main():
    parser = argparse.ArgumentParser(description="Fix suspect servings")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files")
    parser.add_argument("--limit", type=int, default=0, help="Max recipes to process")
    parser.add_argument(
        "--threshold",
        type=float,
        default=800,
        help="Min kcal/serving to consider suspect (default 800)",
    )
    args = parser.parse_args()

    client = _get_llm_client()
    if not client:
        sys.exit(1)

    cache = _load_cache()
    suspects = find_suspect_recipes(args.threshold)
    logger.info(f"Found {len(suspects)} suspect recipes (servings=1, >{args.threshold} kcal)")

    if args.limit:
        suspects = suspects[: args.limit]

    fixed = 0
    for path, recipe in suspects:
        result = await fix_one(client, path, recipe, cache, args.dry_run)
        if result and result["servings"] > 1:
            fixed += 1

    _save_cache(cache)
    mode = "DRY RUN" if args.dry_run else "APPLIED"
    logger.info(f"[{mode}] {fixed}/{len(suspects)} recipes corrected")


if __name__ == "__main__":
    asyncio.run(main())
