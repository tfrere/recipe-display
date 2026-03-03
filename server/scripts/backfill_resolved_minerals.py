"""
Backfill mineral data for resolved_ingredients.json using USDA FDC API.

Each resolved ingredient has an fdc_id. This script fetches the detailed
nutrient profile from USDA and copies mineral values into the entry.

Usage:
    USDA_API_KEY=xxx python -m scripts.backfill_resolved_minerals [--dry-run]
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = SERVER_ROOT / "packages" / "recipe_scraper" / "src" / "recipe_scraper" / "data"
RESOLVED_FILE = DATA_DIR / "resolved_ingredients.json"

USDA_BASE = "https://api.nal.usda.gov/fdc/v1"

MINERAL_NUTRIENT_IDS = {
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1092: "potassium_mg",
    1093: "sodium_mg",
    1095: "zinc_mg",
}


async def fetch_minerals(client: httpx.AsyncClient, fdc_id: int, api_key: str) -> dict | None:
    """Fetch mineral nutrient values for a single USDA FDC food item."""
    url = f"{USDA_BASE}/food/{fdc_id}"
    params = {"api_key": api_key}
    resp = await client.get(url, params=params, timeout=15.0)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()

    minerals = {}
    for nd in data.get("foodNutrients", []):
        nid = nd.get("nutrient", {}).get("id")
        if nid and nid in MINERAL_NUTRIENT_IDS:
            minerals[MINERAL_NUTRIENT_IDS[nid]] = round(nd.get("amount", 0), 2)

    return minerals if minerals else None


async def main():
    dry_run = "--dry-run" in sys.argv
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        logger.error("USDA_API_KEY not set")
        sys.exit(1)

    with open(RESOLVED_FILE) as f:
        data = json.load(f)

    entries = {k: v for k, v in data.items() if not k.startswith("_")}
    to_update = {
        k: v for k, v in entries.items()
        if v.get("fdc_id") and v.get("calcium_mg") is None
    }

    logger.info(f"Total resolved: {len(entries)}, needing minerals: {len(to_update)}")

    if not to_update:
        logger.info("Nothing to update!")
        return

    updated = 0
    errors = 0
    batch_size = 5

    keys = list(to_update.keys())

    async with httpx.AsyncClient() as client:
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            tasks = []
            for key in batch:
                entry = to_update[key]
                tasks.append(fetch_minerals(client, entry["fdc_id"], api_key))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for key, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.warning(f"  Error for '{key}': {result}")
                    errors += 1
                    continue

                if result:
                    data[key].update(result)
                    updated += 1
                    if updated <= 5 or updated % 100 == 0:
                        entry = data[key]
                        logger.info(
                            f"  [{updated}] '{key}' (fdc={entry['fdc_id']}): "
                            f"Ca={result.get('calcium_mg')} Fe={result.get('iron_mg')} "
                            f"Mg={result.get('magnesium_mg')}"
                        )

            if (i + batch_size) % 50 == 0:
                await asyncio.sleep(0.5)

    logger.info(f"\nDone: {updated} updated, {errors} errors")

    if not dry_run and updated > 0:
        data["_meta"] = data.get("_meta", {})
        data["_meta"]["minerals_backfilled_at"] = datetime.now().isoformat()
        with open(RESOLVED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {RESOLVED_FILE}")
    elif dry_run:
        logger.info("[DRY-RUN] No files modified")


if __name__ == "__main__":
    asyncio.run(main())
