"""
Fast mineral backfill: enrich OpenNutrition entries with CIQUAL minerals
using deterministic name normalization (no embeddings, no API calls).

CIQUAL names are "food, descriptor" format (e.g. "flour, wheat").
ON names are natural order (e.g. "Wheat Flour").
This script normalizes both to a canonical form and matches them.

Usage:
    python -m scripts.backfill_minerals_fast [--dry-run]
"""

import json
import logging
import re
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).parent.parent
DATA_DIR = SERVER_ROOT / "packages" / "recipe_scraper" / "src" / "recipe_scraper" / "data"
ON_INDEX = DATA_DIR / "opennutrition_index.json"
CIQUAL_INDEX = DATA_DIR / "ciqual_index.json"
MINERAL_FIELDS = ("calcium_mg", "iron_mg", "magnesium_mg", "potassium_mg", "sodium_mg", "zinc_mg")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STRIP_WORDS = {
    "raw", "cooked", "boiled", "fresh", "dried", "frozen", "canned",
    "peeled", "unpeeled", "unprepared", "prepared", "drained",
    "salted", "unsalted", "whole", "ground", "powdered", "pure",
    "from cow's milk", "from sheep's milk", "from goat's milk",
}
STRIP_RE = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in STRIP_WORDS) + r')\b',
    re.IGNORECASE,
)


def _normalize(name: str) -> set[str]:
    """Generate multiple canonical forms from a food name."""
    forms = set()
    name = name.lower().strip()
    name = re.sub(r"[''']s\b", "", name)

    base = re.sub(r'\s+', ' ', STRIP_RE.sub('', name)).strip(' ,')
    base = re.sub(r'\s*,\s*', ', ', base).strip(', ')

    forms.add(base)
    forms.add(name)

    parts = [p.strip() for p in name.split(',') if p.strip()]
    if len(parts) >= 2:
        reversed_name = ' '.join(parts[1:]) + ' ' + parts[0]
        reversed_name = re.sub(r'\s+', ' ', reversed_name).strip()
        forms.add(reversed_name)

        base_parts = [p.strip() for p in base.split(',') if p.strip()]
        if len(base_parts) >= 2:
            rev_base = ' '.join(base_parts[1:]) + ' ' + base_parts[0]
            rev_base = re.sub(r'\s+', ' ', rev_base).strip()
            forms.add(rev_base)

    for f in list(forms):
        cleaned = STRIP_RE.sub('', f)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,')
        if cleaned:
            forms.add(cleaned)

    return {f for f in forms if len(f) > 2}


def main():
    dry_run = "--dry-run" in sys.argv

    with open(ON_INDEX) as f:
        on_entries = json.load(f)
    with open(CIQUAL_INDEX) as f:
        ciqual_entries = json.load(f)

    ciqual_with_minerals = [
        e for e in ciqual_entries
        if any(e.get(k) is not None for k in MINERAL_FIELDS)
    ]

    ciqual_lookup: dict[str, dict] = {}
    for entry in ciqual_with_minerals:
        forms = _normalize(entry["name"])
        for alt in entry.get("alt", []):
            forms.update(_normalize(alt))
        for form in forms:
            if form not in ciqual_lookup:
                ciqual_lookup[form] = entry

    logger.info(
        f"CIQUAL lookup: {len(ciqual_lookup)} normalized forms "
        f"from {len(ciqual_with_minerals)} entries"
    )

    on_needing = [
        (i, e) for i, e in enumerate(on_entries)
        if not any(e.get(k) is not None for k in MINERAL_FIELDS)
    ]
    logger.info(f"ON entries needing minerals: {len(on_needing)}/{len(on_entries)}")

    enriched = 0
    for orig_idx, on_entry in on_needing:
        on_forms = _normalize(on_entry["name"])
        for alt in on_entry.get("alt", []):
            on_forms.update(_normalize(alt))

        matched_ciq = None
        matched_form = None
        for form in on_forms:
            if form in ciqual_lookup:
                matched_ciq = ciqual_lookup[form]
                matched_form = form
                break

        if matched_ciq:
            for field in MINERAL_FIELDS:
                on_entries[orig_idx][field] = matched_ciq.get(field)
            on_entries[orig_idx]["mineral_source"] = f"ciqual:{matched_ciq['name']}"
            enriched += 1
            if enriched <= 20 or enriched % 200 == 0:
                logger.info(
                    f"  '{on_entry['name']}' <- '{matched_ciq['name']}' "
                    f"(via '{matched_form}')"
                )

    logger.info(f"\nEnriched {enriched}/{len(on_needing)} ON entries")

    if not dry_run and enriched > 0:
        with open(ON_INDEX, "w", encoding="utf-8") as f:
            json.dump(on_entries, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {ON_INDEX}")
    elif dry_run:
        logger.info("[DRY-RUN] No files modified")


if __name__ == "__main__":
    main()
