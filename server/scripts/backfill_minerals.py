"""
Backfill mineral data into OpenNutrition index from CIQUAL.

For each ON entry that lacks minerals, find the closest CIQUAL entry
by embedding similarity. If the match is strong enough (> 0.92), copy
the mineral values from CIQUAL.

Usage:
    python -m scripts.backfill_minerals [--dry-run] [--threshold 0.92]
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SERVER_ROOT / "packages" / "recipe_scraper" / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = SERVER_ROOT / "packages" / "recipe_scraper" / "src" / "recipe_scraper" / "data"
ON_INDEX = DATA_DIR / "opennutrition_index.json"
CIQUAL_INDEX = DATA_DIR / "ciqual_index.json"
MINERAL_FIELDS = ("calcium_mg", "iron_mg", "magnesium_mg", "potassium_mg", "sodium_mg", "zinc_mg")
DEFAULT_THRESHOLD = 0.92


def _build_text(entry: dict) -> str:
    text = entry["name"]
    alts = entry.get("alt", [])
    if alts:
        text += ", " + ", ".join(alts[:3])
    return text


def main():
    dry_run = "--dry-run" in sys.argv
    threshold = DEFAULT_THRESHOLD
    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        threshold = float(sys.argv[idx + 1])

    with open(ON_INDEX) as f:
        on_entries = json.load(f)
    with open(CIQUAL_INDEX) as f:
        ciqual_entries = json.load(f)

    ciqual_with_minerals = [
        e for e in ciqual_entries
        if any(e.get(k) is not None for k in MINERAL_FIELDS)
    ]
    logger.info(
        f"ON entries: {len(on_entries)}, "
        f"CIQUAL with minerals: {len(ciqual_with_minerals)}/{len(ciqual_entries)}"
    )

    on_without_minerals = [
        (i, e) for i, e in enumerate(on_entries)
        if not any(e.get(k) is not None for k in MINERAL_FIELDS)
    ]
    logger.info(f"ON entries lacking minerals: {len(on_without_minerals)}")

    if not on_without_minerals:
        logger.info("Nothing to backfill!")
        return

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    ciq_texts = [_build_text(e) for e in ciqual_with_minerals]
    on_texts = [_build_text(e) for _, e in on_without_minerals]

    logger.info(f"Encoding {len(ciq_texts)} CIQUAL texts...")
    ciq_embs = model.encode(ciq_texts, batch_size=128, normalize_embeddings=True, show_progress_bar=True)
    logger.info(f"Encoding {len(on_texts)} ON texts...")
    on_embs = model.encode(on_texts, batch_size=128, normalize_embeddings=True, show_progress_bar=True)

    similarities = on_embs @ ciq_embs.T

    enriched = 0
    borderline = []
    for j, (orig_idx, on_entry) in enumerate(on_without_minerals):
        best_ciq_idx = int(np.argmax(similarities[j]))
        score = float(similarities[j, best_ciq_idx])
        if score >= threshold:
            ciq = ciqual_with_minerals[best_ciq_idx]
            for field in MINERAL_FIELDS:
                on_entries[orig_idx][field] = ciq.get(field)
            on_entries[orig_idx]["mineral_source"] = ciq["name"]
            enriched += 1
            if enriched <= 15 or enriched % 200 == 0:
                logger.info(
                    f"  [{score:.3f}] '{on_entry['name']}' <- '{ciq['name']}'"
                )
            if score < threshold + 0.03:
                borderline.append((score, on_entry["name"], ciq["name"]))

    logger.info(f"\nEnriched {enriched}/{len(on_without_minerals)} ON entries (threshold={threshold})")

    if borderline:
        borderline.sort()
        logger.info(f"\nBorderline matches (worst 20):")
        for score, on_name, ciq_name in borderline[:20]:
            logger.info(f"  [{score:.3f}] '{on_name}' <- '{ciq_name}'")

    if not dry_run:
        with open(ON_INDEX, "w", encoding="utf-8") as f:
            json.dump(on_entries, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved enriched index to {ON_INDEX}")
    else:
        logger.info("[DRY-RUN] No files modified")


if __name__ == "__main__":
    main()
