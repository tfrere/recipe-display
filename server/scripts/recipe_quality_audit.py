#!/usr/bin/env python3
"""
Deterministic recipe quality audit — zero LLM, zero API cost.

Runs all structural, nutritional, and metadata checks on recipe files.
Produces a terminal report + optional JSON output.

Usage:
    cd server
    poetry run python scripts/recipe_quality_audit.py
    poetry run python scripts/recipe_quality_audit.py --json           # JSON output
    poetry run python scripts/recipe_quality_audit.py --dir data/recipes_pre_v3  # audit old recipes
    poetry run python scripts/recipe_quality_audit.py --compare        # side-by-side old vs new
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
SERVER_ROOT = SCRIPT_DIR.parent
DEFAULT_DIR = SERVER_ROOT / "data" / "recipes"
OLD_DIR = SERVER_ROOT / "data" / "recipes_pre_v3"

VALID_RECIPE_TYPES = {
    "appetizer", "starter", "main_course", "dessert", "drink",
    "base", "breakfast", "side_dish", "snack", "soup", "salad",
}
VALID_STEP_TYPES = {"prep", "combine", "cook", "rest", "serve"}


# ─── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class NutritionStats:
    high: int = 0
    medium: int = 0
    low: int = 0
    missing: int = 0
    atwater_outliers: list = field(default_factory=list)
    zero_macros: dict = field(default_factory=lambda: Counter())
    low_match_rate: list = field(default_factory=list)
    calorie_values: list = field(default_factory=list)


@dataclass
class ReviewStats:
    reviewed: int = 0
    unreviewed: int = 0
    scores: list = field(default_factory=list)
    corrections_applied: list = field(default_factory=list)
    corrections_skipped: list = field(default_factory=list)
    low_score_recipes: list = field(default_factory=list)


@dataclass
class GraphStats:
    valid_refs: int = 0
    invalid_refs: int = 0
    recipes_with_broken_refs: int = 0
    orphan_ingredients: int = 0
    broken_samples: list = field(default_factory=list)


@dataclass
class MetadataStats:
    missing_times: int = 0
    missing_diets: int = 0
    missing_seasons: int = 0
    non_standard_recipe_types: list = field(default_factory=list)
    string_servings: list = field(default_factory=list)
    numeric_servings: int = 0


@dataclass
class IngredientStats:
    total: int = 0
    missing_name_en: int = 0
    missing_quantity_required: int = 0
    missing_category: int = 0
    no_unit_with_qty: int = 0


@dataclass
class StepStats:
    total: int = 0
    missing_duration: int = 0
    empty_uses: int = 0
    non_standard_types: list = field(default_factory=list)


@dataclass
class AuditResult:
    directory: str = ""
    total_recipes: int = 0
    nutrition: NutritionStats = field(default_factory=NutritionStats)
    review: ReviewStats = field(default_factory=ReviewStats)
    graph: GraphStats = field(default_factory=GraphStats)
    metadata: MetadataStats = field(default_factory=MetadataStats)
    ingredients: IngredientStats = field(default_factory=IngredientStats)
    steps: StepStats = field(default_factory=StepStats)
    has_original_text: int = 0
    issues_summary: list = field(default_factory=list)


# ─── Audit logic ──────────────────────────────────────────────────────────────


def audit_recipes(recipes_dir: Path) -> AuditResult:
    recipe_files = sorted(recipes_dir.glob("*.recipe.json"))
    result = AuditResult(
        directory=str(recipes_dir),
        total_recipes=len(recipe_files),
    )

    if not recipe_files:
        return result

    for filepath in recipe_files:
        with open(filepath, "r", encoding="utf-8") as f:
            recipe = json.load(f)

        meta = recipe.get("metadata", {})
        ings = recipe.get("ingredients", [])
        steps = recipe.get("steps", [])
        title = meta.get("title", filepath.stem)[:60]

        _audit_nutrition(result.nutrition, meta, title)
        _audit_review(result.review, meta, title)
        _audit_graph(result.graph, ings, steps, title)
        _audit_metadata(result.metadata, meta, title)
        _audit_ingredients(result.ingredients, ings)
        _audit_steps(result.steps, steps)

        if recipe.get("originalText"):
            result.has_original_text += 1

    _build_summary(result)
    return result


def _audit_nutrition(ns: NutritionStats, meta: dict, title: str):
    nutr = meta.get("nutritionPerServing")
    if not nutr:
        ns.missing += 1
        return

    conf = nutr.get("confidence", "?")
    if conf == "high":
        ns.high += 1
    elif conf == "medium":
        ns.medium += 1
    elif conf == "low":
        ns.low += 1

    cal = nutr.get("calories", 0)
    if cal > 0:
        ns.calorie_values.append(cal)

    protein = nutr.get("protein", 0)
    carbs = nutr.get("carbs", 0)
    fat = nutr.get("fat", 0)
    fiber = nutr.get("fiber", 0)

    if cal > 50:
        atwater = protein * 4 + carbs * 4 + fat * 9
        ratio = atwater / cal if cal > 0 else 0
        if ratio < 0.5 or ratio > 2.0:
            ns.atwater_outliers.append((ratio, cal, atwater, title))

        for macro_name, macro_val in [("protein", protein), ("carbs", carbs), ("fat", fat), ("fiber", fiber)]:
            if macro_val == 0:
                ns.zero_macros[macro_name] += 1

    if cal > 2000:
        ns.atwater_outliers.append((0, cal, 0, f"HIGH CAL: {title}"))
    elif cal < 20 and meta.get("recipeType") not in ("beverage", "sauce", "base", "drink"):
        ns.atwater_outliers.append((0, cal, 0, f"LOW CAL: {title}"))

    matched = nutr.get("matchedIngredients", 0)
    total = nutr.get("totalIngredients", 0)
    if total > 0 and matched / total < 0.7:
        ns.low_match_rate.append((matched, total, title))


def _audit_review(rs: ReviewStats, meta: dict, title: str):
    score = meta.get("reviewScore")
    if score is None:
        rs.unreviewed += 1
    else:
        rs.reviewed += 1
        rs.scores.append(score)
        if score < 5:
            rs.low_score_recipes.append((score, title))

    rs.corrections_applied.append(meta.get("reviewCorrectionsApplied", 0))
    rs.corrections_skipped.append(meta.get("reviewCorrectionsSkipped", 0))


def _audit_graph(gs: GraphStats, ings: list, steps: list, title: str):
    ing_ids = set()
    for i in ings:
        if isinstance(i, dict) and i.get("id"):
            ing_ids.add(i["id"])

    produced = set()
    all_used = set()
    recipe_invalid = 0

    for step in steps:
        if not isinstance(step, dict):
            continue

        for u in step.get("uses", []):
            ref = u if isinstance(u, str) else (u.get("ref") if isinstance(u, dict) else None)
            if ref:
                all_used.add(ref)
                if ref in ing_ids or ref in produced:
                    gs.valid_refs += 1
                else:
                    gs.invalid_refs += 1
                    recipe_invalid += 1
                    if len(gs.broken_samples) < 20:
                        gs.broken_samples.append({"recipe": title, "ref": ref})

        prod = step.get("produces")
        if isinstance(prod, str) and prod:
            produced.add(prod)

    if recipe_invalid > 0:
        gs.recipes_with_broken_refs += 1

    gs.orphan_ingredients += len(ing_ids - all_used)


def _audit_metadata(ms: MetadataStats, meta: dict, title: str):
    if not meta.get("totalTime"):
        ms.missing_times += 1
    if not meta.get("diets"):
        ms.missing_diets += 1
    if not meta.get("seasons"):
        ms.missing_seasons += 1

    rt = meta.get("recipeType", "")
    if rt and rt not in VALID_RECIPE_TYPES:
        ms.non_standard_recipe_types.append((rt, title))

    srv = meta.get("servings")
    if isinstance(srv, str):
        ms.string_servings.append((srv, title))
    elif isinstance(srv, (int, float)):
        ms.numeric_servings += 1


def _audit_ingredients(ist: IngredientStats, ings: list):
    for i in ings:
        if not isinstance(i, dict):
            continue
        ist.total += 1
        if not i.get("name_en"):
            ist.missing_name_en += 1
        if i.get("quantity") is None and not i.get("optional"):
            ist.missing_quantity_required += 1
        if not i.get("category"):
            ist.missing_category += 1
        if i.get("quantity") is not None and not i.get("unit"):
            ist.no_unit_with_qty += 1


def _audit_steps(ss: StepStats, steps: list):
    for step in steps:
        if not isinstance(step, dict):
            continue
        ss.total += 1
        if not step.get("duration"):
            ss.missing_duration += 1
        if not step.get("uses"):
            ss.empty_uses += 1
        st = step.get("stepType", "")
        if st and st not in VALID_STEP_TYPES:
            ss.non_standard_types.append(st)


def _build_summary(r: AuditResult):
    t = r.total_recipes
    if t == 0:
        return

    issues = []

    pct_high = 100 * r.nutrition.high / t
    if pct_high < 80:
        issues.append(f"Nutrition confidence <80% high ({pct_high:.0f}%)")
    if r.nutrition.missing > 0:
        issues.append(f"{r.nutrition.missing} recipes missing nutrition entirely")
    if r.nutrition.atwater_outliers:
        issues.append(f"{len(r.nutrition.atwater_outliers)} nutrition Atwater/calorie outliers")
    if r.nutrition.low_match_rate:
        issues.append(f"{len(r.nutrition.low_match_rate)} recipes with <70% ingredient match rate")

    if r.review.unreviewed > t * 0.1:
        issues.append(f"{r.review.unreviewed} recipes not reviewed ({100*r.review.unreviewed/t:.0f}%)")
    if r.review.low_score_recipes:
        issues.append(f"{len(r.review.low_score_recipes)} recipes scored <5/10")

    if r.graph.invalid_refs > 0:
        issues.append(f"{r.graph.invalid_refs} broken step uses references in {r.graph.recipes_with_broken_refs} recipes")
    if r.graph.orphan_ingredients > t * 0.05:
        issues.append(f"{r.graph.orphan_ingredients} orphan ingredients (never used in steps)")

    if r.metadata.non_standard_recipe_types:
        issues.append(f"{len(r.metadata.non_standard_recipe_types)} non-standard recipeType values")
    if r.metadata.string_servings:
        issues.append(f"{len(r.metadata.string_servings)} recipes with string servings (should be numeric)")

    if r.steps.total > 0:
        dur_pct = 100 * r.steps.missing_duration / r.steps.total
        if dur_pct > 5:
            issues.append(f"{dur_pct:.0f}% of steps missing duration")

    r.issues_summary = issues


# ─── Reporting ────────────────────────────────────────────────────────────────


def pct(n: int, total: int) -> str:
    return f"{100*n/total:.1f}%" if total > 0 else "N/A"


def print_report(r: AuditResult):
    t = r.total_recipes
    print(f"\n{'='*70}")
    print(f"  RECIPE QUALITY AUDIT — {r.directory}")
    print(f"  {t} recipes")
    print(f"{'='*70}\n")

    # Nutrition
    print("NUTRITION")
    print(f"  High confidence:    {r.nutrition.high:>5} ({pct(r.nutrition.high, t)})")
    print(f"  Medium confidence:  {r.nutrition.medium:>5} ({pct(r.nutrition.medium, t)})")
    print(f"  Low confidence:     {r.nutrition.low:>5} ({pct(r.nutrition.low, t)})")
    print(f"  Missing:            {r.nutrition.missing:>5} ({pct(r.nutrition.missing, t)})")

    if r.nutrition.calorie_values:
        cals = r.nutrition.calorie_values
        print(f"  Calories/srv:       median={statistics.median(cals):.0f}  mean={statistics.mean(cals):.0f}  range=[{min(cals):.0f}, {max(cals):.0f}]")

    if r.nutrition.atwater_outliers:
        print(f"  Atwater/cal outliers: {len(r.nutrition.atwater_outliers)}")
        for ratio, cal, atw, title in r.nutrition.atwater_outliers[:5]:
            if ratio > 0:
                print(f"    ratio={ratio:.2f} reported={cal:.0f} vs calc={atw:.0f} | {title}")
            else:
                print(f"    {title} ({cal:.0f} kcal)")

    if r.nutrition.low_match_rate:
        print(f"  Low match rate (<70%): {len(r.nutrition.low_match_rate)}")
        for m, tot, title in r.nutrition.low_match_rate[:5]:
            print(f"    {m}/{tot} ({pct(m, tot)}) | {title}")

    if r.nutrition.zero_macros:
        print(f"  Zero macros (cal>50):", end="")
        for macro, count in r.nutrition.zero_macros.most_common():
            print(f"  {macro}={count}", end="")
        print()

    # Review
    print(f"\nREVIEW AGENT")
    print(f"  Reviewed:           {r.review.reviewed:>5} ({pct(r.review.reviewed, t)})")
    print(f"  Unreviewed:         {r.review.unreviewed:>5}")
    if r.review.scores:
        avg = sum(r.review.scores) / len(r.review.scores)
        good = sum(1 for s in r.review.scores if s >= 8)
        bad = sum(1 for s in r.review.scores if s < 5)
        print(f"  Avg score:          {avg:.1f}/10  (>= 8: {good}, < 5: {bad})")
    if r.review.corrections_applied:
        print(f"  Avg corrections:    applied={sum(r.review.corrections_applied)/len(r.review.corrections_applied):.1f}  skipped={sum(r.review.corrections_skipped)/len(r.review.corrections_skipped):.1f}")
    if r.review.low_score_recipes:
        print(f"  Low score (<5):")
        for score, title in sorted(r.review.low_score_recipes):
            print(f"    score={score} | {title}")

    # Graph
    print(f"\nGRAPH INTEGRITY")
    total_refs = r.graph.valid_refs + r.graph.invalid_refs
    print(f"  Valid references:   {r.graph.valid_refs:>5} ({pct(r.graph.valid_refs, total_refs)})")
    print(f"  Invalid references: {r.graph.invalid_refs:>5}")
    print(f"  Broken recipes:     {r.graph.recipes_with_broken_refs:>5}/{t}")
    print(f"  Orphan ingredients: {r.graph.orphan_ingredients:>5}")
    if r.graph.broken_samples:
        for s in r.graph.broken_samples[:5]:
            print(f"    {s['recipe']} -> ref '{s['ref']}'")

    # Ingredients
    print(f"\nINGREDIENTS ({r.ingredients.total})")
    print(f"  Missing name_en:    {r.ingredients.missing_name_en:>5} ({pct(r.ingredients.missing_name_en, r.ingredients.total)})")
    print(f"  Missing qty (req):  {r.ingredients.missing_quantity_required:>5} ({pct(r.ingredients.missing_quantity_required, r.ingredients.total)})")
    print(f"  Missing category:   {r.ingredients.missing_category:>5}")
    print(f"  Qty without unit:   {r.ingredients.no_unit_with_qty:>5}")

    # Steps
    print(f"\nSTEPS ({r.steps.total})")
    print(f"  Missing duration:   {r.steps.missing_duration:>5} ({pct(r.steps.missing_duration, r.steps.total)})")
    print(f"  Empty uses:         {r.steps.empty_uses:>5} ({pct(r.steps.empty_uses, r.steps.total)})")
    if r.steps.non_standard_types:
        types = Counter(r.steps.non_standard_types)
        print(f"  Non-standard types: {dict(types.most_common(5))}")

    # Metadata
    print(f"\nMETADATA")
    print(f"  Missing times:      {r.metadata.missing_times:>5}")
    print(f"  Missing diets:      {r.metadata.missing_diets:>5}")
    print(f"  Missing seasons:    {r.metadata.missing_seasons:>5}")
    print(f"  Servings numeric:   {r.metadata.numeric_servings:>5}  string: {len(r.metadata.string_servings)}")
    print(f"  Has originalText:   {r.has_original_text:>5} ({pct(r.has_original_text, t)})")

    if r.metadata.non_standard_recipe_types:
        print(f"  Non-standard recipeType ({len(r.metadata.non_standard_recipe_types)}):")
        for rt, title in r.metadata.non_standard_recipe_types[:10]:
            print(f"    '{rt}' | {title}")

    if r.metadata.string_servings:
        print(f"  String servings (sample):")
        for srv, title in r.metadata.string_servings[:10]:
            print(f"    '{srv}' | {title}")

    # Summary
    print(f"\n{'─'*70}")
    if r.issues_summary:
        print(f"  ISSUES FOUND ({len(r.issues_summary)}):")
        for issue in r.issues_summary:
            print(f"    - {issue}")
    else:
        print("  NO MAJOR ISSUES FOUND")
    print(f"{'─'*70}\n")


def print_comparison(new: AuditResult, old: AuditResult):
    print(f"\n{'='*70}")
    print(f"  SIDE-BY-SIDE COMPARISON")
    print(f"{'='*70}\n")

    def row(label: str, old_num: float, new_num: float, old_fmt: str, new_fmt: str, better: str = "higher"):
        if old_num != new_num:
            if better == "higher":
                marker = " +" if new_num > old_num else " -"
            elif better == "lower":
                marker = " +" if new_num < old_num else " -"
            else:
                marker = " *"
        else:
            marker = ""
        print(f"  {label:<35} {old_fmt:>15} {new_fmt:>15}{marker}")

    ot = old.total_recipes
    nt = new.total_recipes

    print(f"  {'Metric':<35} {'OLD':>15} {'NEW':>15}")
    print(f"  {'─'*70}")

    row("Total recipes", ot, nt, str(ot), str(nt), "higher")

    o_nh = 100 * old.nutrition.high / ot if ot else 0
    n_nh = 100 * new.nutrition.high / nt if nt else 0
    row("Nutrition high %", o_nh, n_nh, f"{o_nh:.0f}%", f"{n_nh:.0f}%", "higher")
    row("Nutrition missing", old.nutrition.missing, new.nutrition.missing,
        str(old.nutrition.missing), str(new.nutrition.missing), "lower")

    o_rc = 100 * old.review.reviewed / ot if ot else 0
    n_rc = 100 * new.review.reviewed / nt if nt else 0
    row("Review coverage %", o_rc, n_rc, f"{o_rc:.0f}%", f"{n_rc:.0f}%", "higher")

    old_avg = sum(old.review.scores) / len(old.review.scores) if old.review.scores else 0
    new_avg = sum(new.review.scores) / len(new.review.scores) if new.review.scores else 0
    row("Avg review score", old_avg, new_avg, f"{old_avg:.1f}", f"{new_avg:.1f}", "higher")

    o_dur = 100 * (old.steps.total - old.steps.missing_duration) / old.steps.total if old.steps.total else 0
    n_dur = 100 * (new.steps.total - new.steps.missing_duration) / new.steps.total if new.steps.total else 0
    row("Steps w/ duration %", o_dur, n_dur, f"{o_dur:.0f}%", f"{n_dur:.0f}%", "higher")

    row("Broken graph refs", old.graph.invalid_refs, new.graph.invalid_refs,
        str(old.graph.invalid_refs), str(new.graph.invalid_refs), "lower")
    row("Orphan ingredients", old.graph.orphan_ingredients, new.graph.orphan_ingredients,
        str(old.graph.orphan_ingredients), str(new.graph.orphan_ingredients), "lower")

    o_nrt = len(old.metadata.non_standard_recipe_types)
    n_nrt = len(new.metadata.non_standard_recipe_types)
    row("Non-standard recipeType", o_nrt, n_nrt, str(o_nrt), str(n_nrt), "lower")

    o_ss = len(old.metadata.string_servings)
    n_ss = len(new.metadata.string_servings)
    row("String servings", o_ss, n_ss, str(o_ss), str(n_ss), "lower")

    o_mq = old.ingredients.missing_quantity_required / old.ingredients.total * 100 if old.ingredients.total else 0
    n_mq = new.ingredients.missing_quantity_required / new.ingredients.total * 100 if new.ingredients.total else 0
    row("Ingredients missing qty %", o_mq, n_mq, f"{o_mq:.1f}%", f"{n_mq:.1f}%", "lower")

    print()


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Deterministic recipe quality audit")
    parser.add_argument("--dir", type=str, default=None, help="Recipe directory to audit (default: data/recipes)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of terminal report")
    parser.add_argument("--compare", action="store_true", help="Compare data/recipes vs data/recipes_pre_v3")
    args = parser.parse_args()

    if args.compare:
        if not OLD_DIR.exists():
            print(f"Old recipes dir not found: {OLD_DIR}", file=sys.stderr)
            sys.exit(1)

        print("Auditing new recipes...")
        new_result = audit_recipes(DEFAULT_DIR)
        print("Auditing old recipes...")
        old_result = audit_recipes(OLD_DIR)

        if args.json:
            print(json.dumps({"new": asdict(new_result), "old": asdict(old_result)}, indent=2, default=str))
        else:
            print_report(new_result)
            print_report(old_result)
            print_comparison(new_result, old_result)
        return

    recipes_dir = Path(args.dir) if args.dir else DEFAULT_DIR
    if not recipes_dir.exists():
        print(f"Directory not found: {recipes_dir}", file=sys.stderr)
        sys.exit(1)

    result = audit_recipes(recipes_dir)

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
