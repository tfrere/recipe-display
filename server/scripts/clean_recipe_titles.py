#!/usr/bin/env python3
"""
One-shot script to strip trailing parentheticals from recipe titles
in all .recipe.json files across data directories.

Usage:
    python server/scripts/clean_recipe_titles.py          # dry-run (default)
    python server/scripts/clean_recipe_titles.py --apply   # apply changes

Uses the same clean_title() function as the pipeline (shared.py).
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

_TRAILING_PARENS_RE = re.compile(r"\s*\([^)]*\)\s*$")


def clean_title(title: str) -> str:
    """Strip trailing parenthetical from a recipe title."""
    if not title:
        return title
    return _TRAILING_PARENS_RE.sub("", title).strip()

RECIPE_DIRS = [
    "recipes",
    "recipes_gemini_run",
    "recipes_old",
    "recipes_pre_v3",
    "recipes_backup_legacy_feb2026",
]


def main():
    apply = "--apply" in sys.argv
    changed = 0
    total = 0

    for dir_name in RECIPE_DIRS:
        recipe_dir = DATA_DIR / dir_name
        if not recipe_dir.exists():
            continue

        for path in sorted(recipe_dir.glob("*.recipe.json")):
            total += 1
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            title = data.get("metadata", {}).get("title", "")
            cleaned = clean_title(title)

            if cleaned != title:
                changed += 1
                print(f"  {dir_name}/{path.name}")
                print(f"    - {title}")
                print(f"    + {cleaned}")

                if apply:
                    data["metadata"]["title"] = cleaned
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        f.write("\n")

    print(f"\n{'Applied' if apply else 'Would change'}: {changed}/{total} recipes")
    if not apply and changed > 0:
        print("Run with --apply to write changes.")


if __name__ == "__main__":
    main()
