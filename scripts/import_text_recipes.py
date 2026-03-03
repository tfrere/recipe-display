#!/usr/bin/env python3
"""Batch import text recipes from a folder and tag them with a common author."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RECIPE_OUTPUT = Path(__file__).parent.parent / "server" / "data" / "recipes"
IMAGE_OUTPUT = RECIPE_OUTPUT / "images"


def import_text_file(txt_path: Path, force: bool = False) -> str | None:
    """Run the recipe_scraper CLI for one text file. Returns the slug or None."""
    cmd = [
        sys.executable, "-m", "recipe_scraper.cli",
        "--mode", "text",
        "--input-file", str(txt_path),
        "--recipe-output-folder", str(RECIPE_OUTPUT),
        "--image-output-folder", str(IMAGE_OUTPUT),
    ]
    if force:
        cmd.append("--force")

    print(f"\n{'='*60}")
    print(f"  Importing: {txt_path.name}")
    print(f"{'='*60}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent / "server"),
    )

    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if "Saved recipe: slug=" in line:
                slug = line.split("slug=")[-1].strip()
                print(f"  -> OK: {slug}")
                return slug
        print(f"  -> OK (slug not parsed from output)")
        return "unknown"
    elif result.returncode == 100:
        print(f"  -> SKIP (already exists)")
        return None
    else:
        print(f"  -> FAIL (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"     {line}")
        return None


def patch_author(slug: str, author: str) -> bool:
    """Set the author field in a recipe JSON file."""
    recipe_path = RECIPE_OUTPUT / f"{slug}.recipe.json"
    if not recipe_path.exists():
        return False
    try:
        with open(recipe_path, "r") as f:
            data = json.load(f)
        data.setdefault("metadata", {})["author"] = author
        with open(recipe_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"  Error patching {slug}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Batch import text recipes")
    parser.add_argument("folder", help="Folder containing .txt recipe files")
    parser.add_argument("--author", default="Livre Collaboratif", help="Author to tag all imported recipes with")
    parser.add_argument("--force", action="store_true", help="Re-import even if recipe already exists")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: {folder} is not a directory")
        sys.exit(1)

    txt_files = sorted(folder.glob("*.txt"))
    print(f"Found {len(txt_files)} text files in {folder.name}")
    print(f"Author tag: {args.author}")
    print()

    imported_slugs = []
    skipped = 0
    failed = 0
    t0 = time.time()

    for txt_file in txt_files:
        slug = import_text_file(txt_file, force=args.force)
        if slug and slug != "unknown":
            imported_slugs.append(slug)
        elif slug is None:
            skipped += 1
        else:
            failed += 1

    # Also find recipes that were already imported (skipped) — match by filename
    existing_slugs = []
    for txt_file in txt_files:
        stem = txt_file.stem
        recipe_path = RECIPE_OUTPUT / f"{stem}.recipe.json"
        if recipe_path.exists() and stem not in imported_slugs:
            existing_slugs.append(stem)

    all_slugs = imported_slugs + existing_slugs

    print(f"\n{'='*60}")
    print(f"  Patching author to '{args.author}' on {len(all_slugs)} recipes")
    print(f"{'='*60}")
    patched = 0
    for slug in all_slugs:
        if patch_author(slug, args.author):
            patched += 1
            print(f"  Patched: {slug}")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  DONE in {elapsed:.0f}s")
    print(f"  Imported: {len(imported_slugs)}")
    print(f"  Skipped:  {skipped}")
    print(f"  Failed:   {failed}")
    print(f"  Patched:  {patched}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
