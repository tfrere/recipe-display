#!/usr/bin/env python3
"""
Backfill pipelineVersion, structurerModel, and updatedAt on existing recipes.

Usage:
    python scripts/backfill_versioning.py                          # dry-run on today's recipes
    python scripts/backfill_versioning.py --apply                  # apply to today's recipes
    python scripts/backfill_versioning.py --all --apply            # apply to ALL recipes
    python scripts/backfill_versioning.py --since 2026-02-27       # recipes modified since date
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

RECIPES_DIR = Path(__file__).parent.parent / "data" / "recipes"

PIPELINE_VERSION = "3.0.0"
STRUCTURER_MODEL_DEEPSEEK = "deepseek/deepseek-v3.2"


def needs_backfill(meta: dict) -> bool:
    return (
        "pipelineVersion" not in meta
        or "updatedAt" not in meta
        or "structurerModel" not in meta
    )


def backfill_recipe(filepath: Path, dry_run: bool) -> bool:
    with open(filepath, "r", encoding="utf-8") as f:
        recipe = json.load(f)

    meta = recipe.get("metadata", {})
    if not needs_backfill(meta):
        return False

    created_at = meta.get("createdAt", datetime.now().isoformat())

    meta.setdefault("pipelineVersion", PIPELINE_VERSION)
    meta.setdefault("updatedAt", created_at)

    creation_mode = meta.get("creationMode", "unknown")
    if creation_mode == "manual":
        meta.setdefault("structurerModel", None)
    else:
        meta.setdefault("structurerModel", STRUCTURER_MODEL_DEEPSEEK)

    recipe["metadata"] = meta

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill recipe versioning metadata")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry-run)")
    parser.add_argument("--all", action="store_true", help="Process ALL recipes, not just today's")
    parser.add_argument("--since", type=str, help="Process recipes modified since YYYY-MM-DD")
    args = parser.parse_args()

    dry_run = not args.apply
    if dry_run:
        print("=== DRY RUN (use --apply to write changes) ===\n")

    recipe_files = sorted(RECIPES_DIR.glob("*.recipe.json"))
    print(f"Found {len(recipe_files)} recipe files in {RECIPES_DIR}")

    if not args.all:
        if args.since:
            cutoff = datetime.strptime(args.since, "%Y-%m-%d")
        else:
            cutoff = datetime.combine(date.today(), datetime.min.time())

        cutoff_ts = cutoff.timestamp()
        recipe_files = [
            f for f in recipe_files
            if f.stat().st_mtime >= cutoff_ts
        ]
        print(f"Filtered to {len(recipe_files)} recipes modified since {cutoff.date()}")

    updated = 0
    skipped = 0
    for filepath in recipe_files:
        try:
            if backfill_recipe(filepath, dry_run):
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR: {filepath.name}: {e}")

    action = "would update" if dry_run else "updated"
    print(f"\nDone: {action} {updated} recipes, skipped {skipped} (already had versioning)")


if __name__ == "__main__":
    main()
