"""
Re-categorize ingredients in existing recipe JSONs.

The parser previously rejected categories: grain, legume, nuts_seeds, oil, herb
and silently downgraded them to 'other' or the LLM used 'pantry' as fallback.

This script applies deterministic keyword rules on name_en to fix categories.
Only reassigns from 'other' or 'pantry' → more specific category.
Never touches existing specific categories (meat, dairy, produce, etc.).

Usage:
    cd server && poetry run python scripts/recategorize_ingredients.py
    cd server && poetry run python scripts/recategorize_ingredients.py --dry-run
"""

import json
import sys
from collections import Counter
from pathlib import Path

RECIPES_DIR = Path(__file__).parent.parent / "data" / "recipes"

# ── Keyword rules ────────────────────────────────────────────────
# Each rule: (target_category, keywords_that_match)
# Order matters: first match wins. More specific patterns first.

OIL_KEYWORDS = {
    "olive oil", "vegetable oil", "canola oil", "sunflower oil",
    "sesame oil", "coconut oil", "avocado oil", "grapeseed oil",
    "peanut oil", "corn oil", "rapeseed oil", "truffle oil",
    "walnut oil", "hazelnut oil", "flaxseed oil", "safflower oil",
    "chili oil", "neutral oil", "cooking oil", "frying oil",
}

OIL_SUFFIXES = (" oil",)

GRAIN_KEYWORDS = {
    "rice", "basmati rice", "jasmine rice", "brown rice", "wild rice",
    "arborio rice", "sushi rice", "sticky rice", "risotto rice",
    "pasta", "spaghetti", "penne", "fusilli", "linguine", "fettuccine",
    "tagliatelle", "rigatoni", "orzo", "macaroni", "farfalle",
    "lasagna", "lasagne", "noodles", "rice noodles", "udon",
    "soba", "ramen", "vermicelli", "glass noodles", "egg noodles",
    "flour", "all-purpose flour", "bread flour", "whole wheat flour",
    "oat flour", "almond flour", "rice flour", "cornstarch",
    "buckwheat flour", "semolina", "cornmeal", "polenta",
    "quinoa", "bulgur", "couscous", "farro", "barley",
    "millet", "amaranth", "spelt",
    "oats", "rolled oats", "steel-cut oats", "oat flakes",
    "breadcrumbs", "panko", "panko breadcrumbs",
    "tortillas", "flour tortillas", "corn tortillas", "wheat tortillas",
    "pita", "pita bread", "naan", "flatbread",
    "bread", "sourdough", "baguette", "ciabatta",
    "croutons", "toast", "brioche",
}

GRAIN_SUFFIXES = (" flour", " rice", " pasta", " noodles", " bread", " tortillas")

LEGUME_KEYWORDS = {
    "chickpeas", "lentils", "red lentils", "green lentils", "black lentils",
    "brown lentils", "puy lentils", "beluga lentils",
    "black beans", "kidney beans", "white beans", "cannellini beans",
    "navy beans", "pinto beans", "lima beans", "butter beans",
    "great northern beans", "borlotti beans", "fava beans", "broad beans",
    "mung beans", "adzuki beans", "edamame",
    "split peas", "green peas", "yellow split peas",
    "dal", "dhal", "daal",
    "tofu", "tempeh",
}

LEGUME_SUFFIXES = (" beans", " lentils", " peas", " dal")

NUTS_SEEDS_KEYWORDS = {
    "almonds", "walnuts", "cashews", "pecans", "pistachios",
    "hazelnuts", "macadamia", "pine nuts", "peanuts", "brazil nuts",
    "chestnuts", "coconut flakes", "shredded coconut", "desiccated coconut",
    "sliced almonds", "slivered almonds", "chopped walnuts", "chopped pecans",
    "sesame seeds", "sunflower seeds", "pumpkin seeds", "poppy seeds",
    "chia seeds", "flax seeds", "flaxseed", "ground flaxseed",
    "hemp seeds", "hemp hearts", "nigella seeds", "caraway seeds",
    "tahini", "almond butter", "peanut butter", "cashew butter",
    "nut butter", "seed butter", "sunflower seed butter",
    "almond meal", "ground almonds", "almond extract",
}

NUTS_SEEDS_SUFFIXES = (" nuts", " seeds", " nut")

_NUT_BUTTER_PATTERNS = (
    "nut butter", "nut) butter", "almond butter", "peanut butter",
    "cashew butter", "sunflower butter", "seed butter", "tahini",
)

HERB_KEYWORDS = {
    "basil", "fresh basil", "cilantro", "fresh cilantro", "coriander leaves",
    "parsley", "fresh parsley", "flat-leaf parsley", "curly parsley",
    "mint", "fresh mint", "spearmint", "peppermint",
    "chives", "fresh chives",
    "dill", "fresh dill",
    "tarragon", "fresh tarragon",
    "rosemary", "fresh rosemary",
    "thyme", "fresh thyme",
    "sage", "fresh sage",
    "oregano", "fresh oregano",
    "marjoram", "fresh marjoram",
    "lemongrass", "fresh lemongrass",
    "bay leaves", "fresh bay leaves",
    "thai basil", "holy basil",
    "chervil", "lovage", "sorrel",
    "green onions", "scallions", "spring onions",
}

# Words that indicate the herb is DRIED → should be spice, not herb
DRIED_INDICATORS = {"dried", "ground", "powder", "crushed"}

REASSIGNABLE_FROM = {"other", "pantry"}

_COMPOSITE_SIGNALS = (" or ", " and/or ", " / ", " without ")


def classify_ingredient(name_en: str, current_category: str) -> str | None:
    """Return the new category if reassignment is warranted, else None."""
    if current_category not in REASSIGNABLE_FROM:
        return None

    lower = name_en.strip().lower()
    if not lower:
        return None

    # Skip composite ingredient names — too ambiguous to classify
    if any(sig in lower for sig in _COMPOSITE_SIGNALS):
        return None

    # Oil (check before nuts_seeds because "sesame oil" != "sesame seeds")
    if lower in OIL_KEYWORDS or any(lower.endswith(s) for s in OIL_SUFFIXES):
        return "oil"

    # Grain
    if lower in GRAIN_KEYWORDS or any(lower.endswith(s) for s in GRAIN_SUFFIXES):
        if "almond flour" in lower:
            return "nuts_seeds"
        return "grain"

    # Legume
    if lower in LEGUME_KEYWORDS or any(lower.endswith(s) for s in LEGUME_SUFFIXES):
        return "legume"

    # Nuts & Seeds
    if lower in NUTS_SEEDS_KEYWORDS or any(lower.endswith(s) for s in NUTS_SEEDS_SUFFIXES):
        return "nuts_seeds"
    if any(p in lower for p in _NUT_BUTTER_PATTERNS):
        return "nuts_seeds"

    # Herb (only if fresh — dried herbs stay as spice or pantry)
    tokens = set(lower.split())
    if tokens & DRIED_INDICATORS:
        return None

    if lower in HERB_KEYWORDS:
        return "herb"

    return None


def process_recipes(dry_run: bool = False):
    recipe_files = sorted(RECIPES_DIR.glob("*.recipe.json"))
    print(f"Scanning {len(recipe_files)} recipe files...\n")

    total_changes = 0
    changed_files = 0
    change_log: Counter = Counter()
    examples: dict[str, list[str]] = {}

    for recipe_file in recipe_files:
        try:
            data = json.loads(recipe_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ERROR reading {recipe_file.name}: {e}")
            continue

        ingredients = data.get("ingredients", [])
        file_changed = False

        for ing in ingredients:
            name_en = ing.get("name_en", "")
            current = ing.get("category", "other")
            new_cat = classify_ingredient(name_en, current)

            if new_cat and new_cat != current:
                transition = f"{current} → {new_cat}"
                change_log[transition] += 1

                if transition not in examples:
                    examples[transition] = []
                if len(examples[transition]) < 5:
                    examples[transition].append(name_en)

                ing["category"] = new_cat
                file_changed = True
                total_changes += 1

        if file_changed:
            changed_files += 1
            if not dry_run:
                recipe_file.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

    # ── Report ──
    print("=" * 60)
    print(f"{'DRY RUN — no files written' if dry_run else 'DONE'}")
    print(f"Files scanned:  {len(recipe_files)}")
    print(f"Files changed:  {changed_files}")
    print(f"Total reassignments: {total_changes}")
    print("=" * 60)

    if change_log:
        print("\nTransitions:")
        for transition, count in change_log.most_common():
            exs = ", ".join(examples.get(transition, []))
            print(f"  {transition}: {count}x  (e.g. {exs})")
    else:
        print("\nNo reassignments needed.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    process_recipes(dry_run=dry)
