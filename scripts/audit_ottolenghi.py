"""Deep audit of Ottolenghi recipes specifically."""

import json
import glob
import re
from collections import Counter, defaultdict
from pathlib import Path

RECIPES_DIR = Path(__file__).parent.parent / "server" / "data" / "recipes"

VALID_CATEGORIES = {
    "meat", "poultry", "seafood", "produce", "dairy", "egg",
    "grain", "legume", "nuts_seeds", "oil", "herb",
    "pantry", "spice", "condiment", "beverage", "other",
}

def load_ottolenghi():
    recipes = []
    for fp in sorted(RECIPES_DIR.glob("*.recipe.json")):
        with open(fp) as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        source = (meta.get("source") or "").lower()
        author = (meta.get("author") or "").lower()
        source_url = (meta.get("sourceUrl") or "").lower()
        if "ottolenghi" in source or "ottolenghi" in author or "ottolenghi" in source_url:
            data["_filepath"] = str(fp)
            data["_slug"] = fp.stem.replace(".recipe", "")
            recipes.append(data)
    return recipes


def audit_all(recipes):
    issues = []

    def add(slug, severity, cat, msg):
        issues.append({"slug": slug, "severity": severity, "category": cat, "message": msg})

    # Per-recipe checks
    slug_titles = {}
    title_counter = Counter()

    for r in recipes:
        slug = r["_slug"]
        meta = r.get("metadata", {})
        ingredients = r.get("ingredients", [])
        steps = r.get("steps", [])
        title = meta.get("title", "")

        # --- Duplicates ---
        title_counter[title.lower().strip()] += 1
        slug_titles[slug] = title

        # --- Metadata ---
        servings = meta.get("servings")
        if servings is None or (isinstance(servings, str)):
            add(slug, "ERROR", "metadata", f"Servings invalide: {repr(servings)}")
        elif isinstance(servings, (int, float)) and servings == 0:
            add(slug, "ERROR", "metadata", f"Servings = 0")

        difficulty = meta.get("difficulty")
        if difficulty and difficulty not in ("easy", "medium", "hard"):
            add(slug, "ERROR", "metadata", f"Difficulty invalide: '{difficulty}'")

        recipe_type = meta.get("recipeType")
        if recipe_type and recipe_type not in ("appetizer", "starter", "main_course", "dessert", "drink", "base"):
            add(slug, "ERROR", "metadata", f"recipeType invalide: '{recipe_type}'")

        # Source manquante
        source_val = meta.get("source") or ""
        if not source_val.strip():
            add(slug, "WARNING", "metadata", "Source vide (devrait être 'Ottolenghi' ou le nom du livre)")

        author_val = meta.get("author") or ""
        if not author_val.strip():
            add(slug, "WARNING", "metadata", "Author vide")

        # Diets
        diets = meta.get("diets", [])
        if not diets:
            add(slug, "WARNING", "metadata", "Diets vide")
        if "omnivorous" not in diets and diets:
            add(slug, "WARNING", "metadata", f"'omnivorous' manquant dans diets: {diets}")

        # Seasons
        seasons = meta.get("seasons", [])
        if not seasons:
            add(slug, "WARNING", "metadata", "Seasons vide")

        # --- Temps ---
        total_time = meta.get("totalTime")
        total_time_min = meta.get("totalTimeMinutes")
        if total_time_min is not None and isinstance(total_time_min, (int, float)):
            if total_time_min <= 0:
                add(slug, "ERROR", "time", f"totalTimeMinutes = {total_time_min}")
            elif total_time_min < 3:
                add(slug, "WARNING", "time", f"totalTimeMinutes suspicieusement bas: {total_time_min} min")
            elif total_time_min > 1440:
                add(slug, "WARNING", "time", f"totalTimeMinutes > 24h: {total_time_min} min")

        active_min = meta.get("totalActiveTimeMinutes")
        passive_min = meta.get("totalPassiveTimeMinutes")
        if active_min is not None and total_time_min is not None:
            if isinstance(active_min, (int, float)) and isinstance(total_time_min, (int, float)):
                if active_min > total_time_min + 1:
                    add(slug, "ERROR", "time", f"activeTime ({active_min}) > totalTime ({total_time_min})")

        # Steps sans duration
        cook_steps_no_dur = []
        for step in steps:
            if step.get("stepType") == "cook" and not step.get("duration"):
                cook_steps_no_dur.append(step.get("id"))
        if cook_steps_no_dur:
            add(slug, "WARNING", "time", f"{len(cook_steps_no_dur)} step(s) 'cook' sans duration: {cook_steps_no_dur[:3]}")

        # --- Ingrédients ---
        if not ingredients:
            add(slug, "CRITICAL", "ingredients", "Aucun ingrédient")
        elif len(ingredients) == 1:
            name = ingredients[0].get("name", "")
            if "[" in name.lower() or "no ingredient" in name.lower() or "note" in ingredients[0].get("id", "").lower():
                add(slug, "CRITICAL", "ingredients", f"Ingrédient fantôme (scraping raté): '{name[:80]}'")
            else:
                add(slug, "WARNING", "ingredients", f"1 seul ingrédient: '{name}'")

        ing_ids = set()
        dup_ids = []
        for ing in ingredients:
            iid = ing.get("id", "")
            if iid in ing_ids:
                dup_ids.append(iid)
            ing_ids.add(iid)

            # Quantity checks
            qty = ing.get("quantity")
            if qty is not None and isinstance(qty, (int, float)):
                if qty < 0:
                    add(slug, "ERROR", "ingredients", f"Quantité négative pour '{ing.get('name')}': {qty}")
                elif qty == 0 and not ing.get("optional", False):
                    add(slug, "WARNING", "ingredients", f"Quantité = 0 pour '{ing.get('name')}'")
                elif qty > 5000:
                    add(slug, "WARNING", "ingredients", f"Quantité très élevée pour '{ing.get('name')}': {qty} {ing.get('unit')}")

            # Category
            cat = ing.get("category")
            if cat and cat not in VALID_CATEGORIES:
                add(slug, "ERROR", "ingredients", f"Catégorie invalide '{cat}' pour '{ing.get('name')}'")

            # name_en missing
            name_en = ing.get("name_en")
            if not name_en or not name_en.strip():
                add(slug, "WARNING", "ingredients", f"name_en manquant pour '{ing.get('name')}'")

        if dup_ids:
            add(slug, "ERROR", "ingredients", f"IDs dupliqués: {dup_ids}")

        # --- Températures ---
        for step in steps:
            temp = step.get("temperature")
            if temp is not None:
                if not isinstance(temp, (int, float)):
                    add(slug, "ERROR", "temperature", f"Temp non-numérique dans '{step.get('id')}': {temp}")
                elif temp > 300:
                    add(slug, "ERROR", "temperature", f"Temp en °F probable dans '{step.get('id')}': {temp}°C")
                elif temp < -30:
                    add(slug, "ERROR", "temperature", f"Temp aberrante dans '{step.get('id')}': {temp}°C")

        # --- Graphe DAG ---
        produced = set()
        for step in steps:
            sid = step.get("id", "")
            uses = step.get("uses", [])
            if isinstance(uses, str):
                add(slug, "ERROR", "graph", f"Step '{sid}' uses est une string au lieu d'une liste")
                uses = [uses]
            requires = step.get("requires", [])
            if isinstance(requires, str):
                add(slug, "ERROR", "graph", f"Step '{sid}' requires est une string au lieu d'une liste")
                requires = [requires]

            for ref in uses:
                if ref not in ing_ids and ref not in produced:
                    add(slug, "ERROR", "graph", f"Step '{sid}' réf. inconnue: '{ref}'")

            for ref in requires:
                if ref not in produced:
                    add(slug, "ERROR", "graph", f"Step '{sid}' requires état inexistant: '{ref}'")

            p = step.get("produces", "")
            if p in produced:
                add(slug, "ERROR", "graph", f"État dupliqué: '{p}'")
            if p:
                produced.add(p)

        final = r.get("finalState", "")
        if final and final not in produced:
            add(slug, "ERROR", "graph", f"finalState '{final}' non produit")

        # Unused required ingredients
        used_refs = set()
        for step in steps:
            u = step.get("uses", [])
            if isinstance(u, str): u = [u]
            for ref in u:
                used_refs.add(ref)

        optional_ids = {i.get("id") for i in ingredients if i.get("optional", False)}
        required_ids = ing_ids - optional_ids
        unused = required_ids - used_refs
        if unused and len(unused) > 0:
            pct = len(unused) / max(len(required_ids), 1) * 100
            if pct > 50:
                add(slug, "ERROR", "graph", f"{len(unused)}/{len(required_ids)} ingrédients requis non utilisés ({pct:.0f}%): {sorted(unused)[:5]}")
            elif pct > 20:
                add(slug, "WARNING", "graph", f"{len(unused)}/{len(required_ids)} ingrédients non utilisés ({pct:.0f}%)")

        # --- Nutrition ---
        nut = meta.get("nutritionPerServing", {})
        if nut:
            cal = nut.get("calories")
            if cal is not None and cal == 0.0 and len(ingredients) > 2:
                add(slug, "ERROR", "nutrition", f"0 calories avec {len(ingredients)} ingrédients")
            elif cal is not None and cal > 2000:
                add(slug, "WARNING", "nutrition", f"Calories très élevées: {cal}/portion")
            elif cal is not None and cal < 20 and cal > 0 and len(ingredients) > 3:
                add(slug, "WARNING", "nutrition", f"Calories suspicieusement basses: {cal}/portion")

            conf = nut.get("confidence")
            if conf == "low":
                resolved = nut.get("resolvedIngredients", 0)
                total = nut.get("totalIngredients", 0)
                if total > 0 and resolved / total < 0.5:
                    add(slug, "WARNING", "nutrition", f"Confiance basse: {resolved}/{total} ingrédients résolus")
        elif len(ingredients) > 2:
            add(slug, "WARNING", "nutrition", "Pas de données nutritionnelles")

    # --- Duplicate titles ---
    duplicates = {t: c for t, c in title_counter.items() if c > 1}

    return issues, duplicates


def main():
    recipes = load_ottolenghi()
    print(f"Recettes Ottolenghi trouvées: {len(recipes)}")

    # Split by creation date
    today_count = sum(1 for r in recipes if (r.get("metadata", {}).get("createdAt") or "")[:10] == "2026-02-19")
    print(f"  dont importées aujourd'hui: {today_count}")
    print()

    issues, duplicates = audit_all(recipes)

    severity_counts = Counter(i["severity"] for i in issues)
    category_counts = Counter(i["category"] for i in issues)

    print("=" * 70)
    print("RÉSUMÉ DE L'AUDIT OTTOLENGHI")
    print("=" * 70)
    print(f"Total issues:     {len(issues)}")
    print(f"  CRITICAL:       {severity_counts.get('CRITICAL', 0)}")
    print(f"  ERROR:          {severity_counts.get('ERROR', 0)}")
    print(f"  WARNING:        {severity_counts.get('WARNING', 0)}")
    print()

    print("Par catégorie:")
    for cat, count in category_counts.most_common():
        print(f"  {cat:18s}: {count}")
    print()

    # Duplicates
    if duplicates:
        print("=" * 70)
        print(f"DOUBLONS DE TITRES ({len(duplicates)})")
        print("=" * 70)
        for title, count in sorted(duplicates.items(), key=lambda x: -x[1]):
            print(f"  [{count}x] {title}")
        print()

    # CRITICAL
    criticals = [i for i in issues if i["severity"] == "CRITICAL"]
    if criticals:
        print("=" * 70)
        print(f"CRITIQUES ({len(criticals)})")
        print("=" * 70)
        for i in criticals:
            print(f"  {i['slug']}: {i['message']}")
        print()

    # ERRORS by category
    errors = [i for i in issues if i["severity"] == "ERROR"]
    if errors:
        print("=" * 70)
        print(f"ERREURS ({len(errors)})")
        print("=" * 70)
        by_cat = defaultdict(list)
        for i in errors:
            by_cat[i["category"]].append(i)
        for cat in ["temperature", "graph", "ingredients", "metadata", "nutrition", "time"]:
            cat_issues = by_cat.get(cat, [])
            if cat_issues:
                print(f"\n  --- {cat.upper()} ({len(cat_issues)}) ---")
                for i in cat_issues[:30]:
                    print(f"    {i['slug']}: {i['message']}")
                if len(cat_issues) > 30:
                    print(f"    ... et {len(cat_issues) - 30} de plus")
        print()

    # WARNINGS summary (grouped)
    warnings = [i for i in issues if i["severity"] == "WARNING"]
    if warnings:
        print("=" * 70)
        print(f"WARNINGS ({len(warnings)}) - résumé par catégorie")
        print("=" * 70)
        by_cat = defaultdict(list)
        for i in warnings:
            by_cat[i["category"]].append(i)
        for cat, items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
            print(f"\n  --- {cat.upper()} ({len(items)}) ---")
            # Group similar messages
            msg_patterns = Counter()
            for i in items:
                # Simplify message for grouping
                msg = i["message"]
                if "name_en manquant" in msg:
                    msg_patterns["name_en manquant"] += 1
                elif "cook' sans duration" in msg:
                    msg_patterns["Steps cook sans duration"] += 1
                elif "Source vide" in msg:
                    msg_patterns["Source vide"] += 1
                elif "Author vide" in msg:
                    msg_patterns["Author vide"] += 1
                elif "Confiance basse" in msg:
                    msg_patterns["Nutrition confiance basse"] += 1
                elif "Pas de données nutritionnelles" in msg:
                    msg_patterns["Pas de nutrition"] += 1
                elif "ingrédients non utilisés" in msg:
                    msg_patterns["Ingrédients non utilisés (>20%)"] += 1
                elif "Calories très élevées" in msg:
                    msg_patterns["Calories très élevées"] += 1
                else:
                    msg_patterns[msg] += 1
            for msg, count in msg_patterns.most_common(15):
                print(f"    [{count:4d}x] {msg}")

    # Top offenders
    issues_per_recipe = Counter(i["slug"] for i in issues if i["severity"] in ("ERROR", "CRITICAL"))
    top = issues_per_recipe.most_common(20)
    if top:
        print()
        print("=" * 70)
        print("TOP 20 RECETTES LES PLUS PROBLÉMATIQUES")
        print("=" * 70)
        for slug, count in top:
            recipe_issues = [i for i in issues if i["slug"] == slug and i["severity"] in ("ERROR", "CRITICAL")]
            cats = Counter(i["category"] for i in recipe_issues)
            cat_str = ", ".join(f"{c}:{n}" for c, n in cats.most_common())
            print(f"  {slug}: {count} erreurs ({cat_str})")

    # Stats globales
    print()
    print("=" * 70)
    print("STATISTIQUES GLOBALES")
    print("=" * 70)
    total = len(recipes)
    with_errors = len(set(i["slug"] for i in issues if i["severity"] in ("ERROR", "CRITICAL")))
    clean = total - len(set(i["slug"] for i in issues))
    print(f"  Recettes propres (0 issue):     {clean}/{total} ({clean/total*100:.1f}%)")
    print(f"  Recettes avec erreurs:          {with_errors}/{total} ({with_errors/total*100:.1f}%)")
    print(f"  Recettes avec warnings seuls:   {total - clean - with_errors}/{total}")


if __name__ == "__main__":
    main()
