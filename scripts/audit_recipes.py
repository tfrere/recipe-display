"""Audit all recipe JSON files for data quality issues."""

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

RECIPES_DIR = Path(__file__).parent.parent / "server" / "data" / "recipes"

VALID_UNITS = {
    "g", "kg", "ml", "l", "cl", "dl",
    "tbsp", "tsp", "cup", "piece", "bunch", "slice", "pinch",
    "can", "handful", "sprig", "clove", "head", "stalk", "sheet",
    "stick", "dash", "drop", "packet", "bag", "bottle", "jar",
    "box", "bar", "block", "link", "fillet", "leaf", "branch",
    "scoop", "serving", "splash", "knob", "zest",
    None,
}

VALID_CATEGORIES = {
    "meat", "poultry", "seafood", "produce", "dairy", "egg",
    "grain", "legume", "nuts_seeds", "oil", "herb",
    "pantry", "spice", "condiment", "beverage", "other",
}

VALID_RECIPE_TYPES = {"appetizer", "starter", "main_course", "dessert", "drink", "base"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_STEP_TYPES = {"prep", "combine", "cook", "rest", "serve"}


def audit_recipe(filepath: Path) -> list[dict]:
    """Return a list of issues found in a single recipe file."""
    issues = []
    slug = filepath.stem.replace(".recipe", "")

    def add(severity: str, category: str, msg: str):
        issues.append({"severity": severity, "category": category, "message": msg, "slug": slug})

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        add("CRITICAL", "json", f"Invalid JSON: {e}")
        return issues
    except Exception as e:
        add("CRITICAL", "io", f"Cannot read file: {e}")
        return issues

    meta = data.get("metadata", {})
    ingredients = data.get("ingredients", [])
    steps = data.get("steps", [])

    # --- METADATA ---
    if not meta:
        add("CRITICAL", "metadata", "Missing metadata entirely")
        return issues

    title = meta.get("title", "")
    if not title or not title.strip():
        add("CRITICAL", "metadata", "Empty title")

    servings = meta.get("servings")
    if servings is None:
        add("ERROR", "metadata", "Missing servings")
    elif not isinstance(servings, (int, float)) or servings <= 0:
        add("ERROR", "metadata", f"Invalid servings: {servings}")
    elif servings > 50:
        add("WARNING", "metadata", f"Unusually high servings: {servings}")

    difficulty = meta.get("difficulty")
    if difficulty and difficulty not in VALID_DIFFICULTIES:
        add("ERROR", "metadata", f"Invalid difficulty: '{difficulty}'")

    recipe_type = meta.get("recipeType")
    if recipe_type and recipe_type not in VALID_RECIPE_TYPES:
        add("ERROR", "metadata", f"Invalid recipeType: '{recipe_type}'")

    total_time = meta.get("totalTime")
    if total_time is not None:
        if isinstance(total_time, (int, float)):
            if total_time <= 0:
                add("ERROR", "metadata", f"totalTime <= 0: {total_time}")
            elif total_time > 1440:
                add("WARNING", "metadata", f"totalTime > 24h: {total_time} min")

    nutrition = meta.get("nutritionPerServing", {})
    if nutrition:
        cal = nutrition.get("calories")
        if cal is not None:
            if cal <= 0:
                add("ERROR", "nutrition", f"Calories <= 0: {cal}")
            elif cal > 3000:
                add("WARNING", "nutrition", f"Unusually high calories/serving: {cal}")
            elif cal < 10:
                add("WARNING", "nutrition", f"Suspiciously low calories/serving: {cal}")

        protein = nutrition.get("protein")
        if protein is not None and protein < 0:
            add("ERROR", "nutrition", f"Negative protein: {protein}")

        fat = nutrition.get("fat")
        if fat is not None and fat < 0:
            add("ERROR", "nutrition", f"Negative fat: {fat}")

        carbs = nutrition.get("carbs")
        if carbs is not None and carbs < 0:
            add("ERROR", "nutrition", f"Negative carbs: {carbs}")

    # --- INGREDIENTS ---
    if not ingredients:
        add("CRITICAL", "ingredients", "No ingredients")
    elif len(ingredients) < 2:
        add("WARNING", "ingredients", f"Only {len(ingredients)} ingredient(s)")

    ingredient_ids = set()
    duplicate_ids = []
    for ing in ingredients:
        ing_id = ing.get("id", "")
        name = ing.get("name", "")

        if not ing_id:
            add("ERROR", "ingredients", f"Ingredient missing id: '{name}'")
        elif ing_id in ingredient_ids:
            duplicate_ids.append(ing_id)
        ingredient_ids.add(ing_id)

        if not name or not name.strip():
            add("ERROR", "ingredients", f"Empty ingredient name (id: {ing_id})")

        qty = ing.get("quantity")
        unit = ing.get("unit")
        optional = ing.get("optional", False)

        if qty is not None:
            if not isinstance(qty, (int, float)):
                add("ERROR", "ingredients", f"Non-numeric quantity for '{name}': {qty}")
            elif qty < 0:
                add("ERROR", "ingredients", f"Negative quantity for '{name}': {qty}")
            elif qty == 0 and not optional:
                add("WARNING", "ingredients", f"Zero quantity for required ingredient '{name}'")

        if unit is not None and unit not in VALID_UNITS:
            pass  # too many custom units, skip

        category = ing.get("category")
        if category and category not in VALID_CATEGORIES:
            add("ERROR", "ingredients", f"Invalid category '{category}' for '{name}'")

    if duplicate_ids:
        add("ERROR", "ingredients", f"Duplicate ingredient IDs: {duplicate_ids}")

    # --- STEPS ---
    if not steps:
        add("CRITICAL", "steps", "No steps")
    elif len(steps) < 2:
        add("WARNING", "steps", f"Only {len(steps)} step(s)")

    produced_states = set()
    step_ids = set()
    for step in steps:
        sid = step.get("id", "")
        if not sid:
            add("ERROR", "steps", "Step missing id")
        elif sid in step_ids:
            add("ERROR", "steps", f"Duplicate step id: '{sid}'")
        step_ids.add(sid)

        action = step.get("action", "")
        if not action or not action.strip():
            add("ERROR", "steps", f"Empty action in step '{sid}'")

        step_type = step.get("stepType")
        if step_type and step_type not in VALID_STEP_TYPES:
            add("ERROR", "steps", f"Invalid stepType '{step_type}' in step '{sid}'")

        temp = step.get("temperature")
        if temp is not None:
            if not isinstance(temp, (int, float)):
                add("ERROR", "steps", f"Non-numeric temperature in step '{sid}': {temp}")
            elif temp > 350:
                add("WARNING", "steps", f"Very high temperature in step '{sid}': {temp}°C")
            elif temp < 0:
                add("ERROR", "steps", f"Negative temperature in step '{sid}': {temp}°C")

        uses = step.get("uses", [])
        if isinstance(uses, str):
            add("ERROR", "steps", f"Step '{sid}' has 'uses' as string instead of list")
            uses = [uses]
        produces = step.get("produces", "")
        requires = step.get("requires", [])
        if isinstance(requires, str):
            add("ERROR", "steps", f"Step '{sid}' has 'requires' as string instead of list")
            requires = [requires]

        for ref in uses:
            if ref not in ingredient_ids and ref not in produced_states:
                add("ERROR", "graph", f"Step '{sid}' uses unknown ref '{ref}'")

        for ref in requires:
            if ref not in produced_states:
                add("ERROR", "graph", f"Step '{sid}' requires unknown state '{ref}'")

        if produces:
            if produces in produced_states:
                add("ERROR", "graph", f"Duplicate produced state: '{produces}'")
            produced_states.add(produces)

    # finalState
    final = data.get("finalState", "")
    if final and final not in produced_states:
        add("ERROR", "graph", f"finalState '{final}' not produced by any step")

    # Unused required ingredients
    used_refs = set()
    for step in steps:
        for ref in step.get("uses", []):
            used_refs.add(ref)

    optional_ids = {ing.get("id") for ing in ingredients if ing.get("optional", False)}
    required_ids = ingredient_ids - optional_ids
    unused = required_ids - used_refs
    if unused and len(unused) > len(required_ids) * 0.5:
        add("ERROR", "graph", f"More than half of required ingredients unused: {sorted(unused)}")

    # Orphan states
    consumed = set()
    for step in steps:
        _uses = step.get("uses", [])
        _requires = step.get("requires", [])
        if isinstance(_uses, str):
            _uses = [_uses]
        if isinstance(_requires, str):
            _requires = [_requires]
        for ref in _uses + _requires:
            if ref in produced_states:
                consumed.add(ref)
    orphans = produced_states - consumed - {final}
    if orphans:
        add("WARNING", "graph", f"Orphan states (never consumed): {sorted(orphans)}")

    # --- LANGUAGE MIXING ---
    if title and meta.get("source"):
        source = meta.get("source", "")
        fr_sources = {"Free The Pickle", "Papilles et Pupilles", "Marmiton"}
        en_sources = {"Minimalist Baker", "Cookie and Kate", "Love and Lemons", "101 Cookbooks", "Smitten Kitchen"}
        is_french_source = any(s.lower() in source.lower() for s in fr_sources)
        is_english_source = any(s.lower() in source.lower() for s in en_sources)

        if is_french_source:
            for ing in ingredients:
                name = ing.get("name", "")
                en_words = {"flour", "sugar", "butter", "salt", "pepper", "milk", "water", "egg", "oil", "chicken", "onion"}
                if name.lower() in en_words:
                    add("WARNING", "language", f"French source but English ingredient name: '{name}'")
                    break

    return issues


def main():
    recipe_files = sorted(RECIPES_DIR.glob("*.recipe.json"))
    if not recipe_files:
        print(f"No recipe files found in {RECIPES_DIR}")
        sys.exit(1)

    print(f"Auditing {len(recipe_files)} recipes...\n")

    all_issues = []
    recipes_with_issues = 0

    for fp in recipe_files:
        issues = audit_recipe(fp)
        if issues:
            recipes_with_issues += 1
        all_issues.extend(issues)

    # --- Summary ---
    severity_counts = Counter(i["severity"] for i in all_issues)
    category_counts = Counter(i["category"] for i in all_issues)

    print("=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"Total recipes:          {len(recipe_files)}")
    print(f"Recipes with issues:    {recipes_with_issues}")
    print(f"Total issues:           {len(all_issues)}")
    print()

    print("By severity:")
    for sev in ["CRITICAL", "ERROR", "WARNING"]:
        count = severity_counts.get(sev, 0)
        print(f"  {sev:10s}: {count}")
    print()

    print("By category:")
    for cat, count in category_counts.most_common():
        print(f"  {cat:15s}: {count}")
    print()

    # Show CRITICAL issues
    criticals = [i for i in all_issues if i["severity"] == "CRITICAL"]
    if criticals:
        print("=" * 70)
        print(f"CRITICAL ISSUES ({len(criticals)})")
        print("=" * 70)
        for i in criticals:
            print(f"  [{i['category']}] {i['slug']}: {i['message']}")
        print()

    # Show ERROR issues (first 50)
    errors = [i for i in all_issues if i["severity"] == "ERROR"]
    if errors:
        print("=" * 70)
        print(f"ERROR ISSUES ({len(errors)} total, showing first 80)")
        print("=" * 70)
        for i in errors[:80]:
            print(f"  [{i['category']}] {i['slug']}: {i['message']}")
        if len(errors) > 80:
            print(f"  ... and {len(errors) - 80} more errors")
        print()

    # Show WARNING issues (first 30)
    warnings = [i for i in all_issues if i["severity"] == "WARNING"]
    if warnings:
        print("=" * 70)
        print(f"WARNING ISSUES ({len(warnings)} total, showing first 50)")
        print("=" * 70)
        for i in warnings[:50]:
            print(f"  [{i['category']}] {i['slug']}: {i['message']}")
        if len(warnings) > 50:
            print(f"  ... and {len(warnings) - 50} more warnings")
        print()

    # Top offenders
    issues_per_recipe = Counter(i["slug"] for i in all_issues)
    top_offenders = issues_per_recipe.most_common(15)
    if top_offenders:
        print("=" * 70)
        print("TOP 15 RECIPES WITH MOST ISSUES")
        print("=" * 70)
        for slug, count in top_offenders:
            recipe_issues = [i for i in all_issues if i["slug"] == slug]
            severities = Counter(i["severity"] for i in recipe_issues)
            sev_str = ", ".join(f"{s}:{c}" for s, c in severities.most_common())
            print(f"  {slug}: {count} issues ({sev_str})")


if __name__ == "__main__":
    main()
