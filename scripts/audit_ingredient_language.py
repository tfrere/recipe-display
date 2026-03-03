#!/usr/bin/env python3
"""
Audit script: quantify recipes with mixed French/English ingredient names.

Detects language mixing by comparing ingredient.name vs name_en.
- If name is French and name_en is English → mixed (or intentional for FR recipes)
- If recipe is from an English source but name is French → bug
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Common French ingredient patterns (words that strongly indicate French)
FRENCH_PATTERNS = [
    r"\bhuile\b", r"\bpois\b", r"\bchiches\b", r"\bpois chiches\b",
    r"\bcrème\b", r"\bbeurre\b", r"\bail\b", r"\boignon\b", r"\bpoivre\b",
    r"\bsel\b", r"\bpoivron\b", r"\bpoivrons\b", r"\bpois chiches\b",
    r"\bharicots\b", r"\blentilles\b", r"\bépices\b", r"\bépice\b",
    r"\bépices\b", r"\bcumin moulu\b", r"\bpois chiches\b",
    r"\bhuile d'olive\b", r"\bhuile d'olive\b", r"\bconcentré\b",
    r"\bpâte\b", r"\bpurée\b", r"\bémincé\b", r"\bémincés\b",
    r"\bégoutté\b", r"\bégouttés\b", r"\bciselé\b", r"\bhaché\b",
    r"\bmoulu\b", r"\bmoulue\b", r"\bfrais\b", r"\bfraîche\b",
    r"\bchampignons\b", r"\bchampignon\b", r"\bthym\b", r"\bromarin\b",
    r"\bpersil\b", r"\bmenthe\b", r"\bcoriandre\b", r"\bbasilic\b",
    r"\bamandes\b", r"\bnoix\b", r"\bnoisettes\b", r"\bnoix de cajou\b",
    r"\bcrème fraîche\b", r"\bvin blanc\b", r"\bvin rouge\b",
    r"\bbouillon\b", r"\bvolaille\b", r"\bviande\b", r"\bpoisson\b",
    r"\bconcombre\b", r"\bconcombres\b", r"\bcourgette\b", r"\bcourgettes\b",
    r"\baubergine\b", r"\baubergines\b", r"\btomate\b", r"\btomates\b",
    r"\bcarotte\b", r"\bcarottes\b", r"\bharicots verts\b",
    r"\bpois chiches\b", r"\bpois chiches\b", r"\bpois chiches\b",
    r"d'olive", r"d'ail", r"de tomate", r"de tomates",
    r"l'ail", r"l'oignon", r"l'huile",
]

# Common English ingredient words (strongly indicate English)
ENGLISH_PATTERNS = [
    r"\bolive oil\b", r"\bchickpeas\b", r"\bground cumin\b", r"\bcumin\b",
    r"\bchicken\b", r"\bgarlic\b", r"\bonion\b", r"\bpepper\b", r"\bsalt\b",
    r"\bbutter\b", r"\bcream\b", r"\bflour\b", r"\bsugar\b", r"\bvinegar\b",
    r"\bchicken legs\b", r"\bchicken thighs\b", r"\bchicken breast\b",
    r"\bvegetable oil\b", r"\bcanola oil\b", r"\bsoy sauce\b",
    r"\bblack pepper\b", r"\bwhite pepper\b", r"\bsea salt\b",
    r"\bkosher salt\b", r"\btable salt\b",
]


def is_likely_french(name: str) -> bool:
    """Heuristic: name contains French ingredient words."""
    if not name or len(name.strip()) < 2:
        return False
    name_lower = name.lower().strip()
    for pat in FRENCH_PATTERNS:
        if re.search(pat, name_lower, re.IGNORECASE):
            return True
    # French-specific diacritics / constructions
    if re.search(r"[àâäéèêëïîôùûüç]", name_lower):
        return True
    if "'" in name and re.search(r"\w+\s+d'\w+", name_lower):
        return True  # "huile d'olive" pattern
    return False


def is_likely_english(name: str) -> bool:
    """Heuristic: name contains common English ingredient words."""
    if not name or len(name.strip()) < 2:
        return False
    name_lower = name.lower().strip()
    for pat in ENGLISH_PATTERNS:
        if re.search(pat, name_lower, re.IGNORECASE):
            return True
    # No French diacritics and common English structure
    if not re.search(r"[àâäéèêëïîôùûüç]", name_lower):
        # Simple check: "chicken legs" pattern
        if re.search(r"\b(chicken|olive|butter|cream|flour|garlic|onion)\b", name_lower):
            return True
    return False


def is_english_source(metadata: dict) -> bool:
    """Check if recipe source is likely English based on metadata.language."""
    lang = (metadata.get("language") or "").lower()
    return lang == "en"


def audit_recipe(recipe_path: Path) -> dict:
    """Analyze a single recipe for language mixing."""
    try:
        with open(recipe_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e), "path": str(recipe_path)}

    metadata = data.get("metadata", {})
    ingredients = data.get("ingredients", [])

    names_fr = []
    names_en = []
    mixed = []

    for ing in ingredients:
        name = ing.get("name", "")
        name_en = ing.get("name_en", "")
        if not name:
            continue

        name_fr = is_likely_french(name)
        name_en_check = is_likely_english(name)

        if name_fr:
            names_fr.append(name)
        if name_en_check:
            names_en.append(name)

        # Mixed: same ingredient has French name but English name_en
        if name_fr and name_en and name_en != name:
            mixed.append({"name": name, "name_en": name_en})

    is_english_src = is_english_source(metadata)
    has_mixed = len(names_fr) > 0 and len(names_en) > 0
    has_fr_in_en_source = is_english_src and len(names_fr) > 0

    return {
        "path": str(recipe_path),
        "title": metadata.get("title", "?"),
        "source_url": metadata.get("sourceUrl", ""),
        "language": metadata.get("language", ""),
        "is_english_source": is_english_src,
        "ingredient_count": len(ingredients),
        "names_fr_count": len(names_fr),
        "names_en_count": len(names_en),
        "names_fr": names_fr[:5],
        "names_en": names_en[:5],
        "mixed_count": len(mixed),
        "mixed_samples": mixed[:3],
        "has_mixed": has_mixed,
        "has_fr_in_en_source": has_fr_in_en_source,
    }


def main():
    recipes_dir = Path(__file__).parent.parent / "server" / "data" / "recipes"
    if not recipes_dir.exists():
        recipes_dir = Path(__file__).parent.parent / "server" / "packages" / "recipe_scraper" / "data" / "recipes"
    if not recipes_dir.exists():
        print("No recipes directory found")
        return

    recipe_files = list(recipes_dir.glob("*.recipe.json"))
    print(f"Scanning {len(recipe_files)} recipes in {recipes_dir}")

    results = []
    for rf in recipe_files:
        r = audit_recipe(rf)
        if "error" not in r:
            results.append(r)

    # Summary
    total = len(results)
    mixed_recipes = [r for r in results if r["has_mixed"]]
    fr_in_en_source = [r for r in results if r["has_fr_in_en_source"]]

    print("\n" + "=" * 60)
    print("INGREDIENT LANGUAGE AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total recipes: {total}")
    print(f"Recipes with mixed FR+EN names: {len(mixed_recipes)} ({100*len(mixed_recipes)/total:.1f}%)")
    print(f"English-source recipes with French names (BUG): {len(fr_in_en_source)} ({100*len(fr_in_en_source)/total:.1f}%)")

    if fr_in_en_source:
        print("\n--- Sample: English-source recipes with French ingredient names ---")
        for r in fr_in_en_source[:10]:
            print(f"  - {r['title'][:50]}...")
            print(f"    Source: {r['source_url'][:60]}...")
            print(f"    French names: {r['names_fr'][:5]}")
            print(f"    English names: {r['names_en'][:5]}")

    if mixed_recipes:
        print("\n--- Sample: Mixed recipes (some FR, some EN names) ---")
        for r in mixed_recipes[:5]:
            print(f"  - {r['title'][:50]}...")
            print(f"    FR: {r['names_fr'][:3]} | EN: {r['names_en'][:3]}")


if __name__ == "__main__":
    main()
