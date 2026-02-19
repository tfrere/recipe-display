"""
Full nutrition audit — runs NutritionAgent on all recipes.

100% deterministic, no LLM, no API cost.

Usage:
    cd server
    poetry run python scripts/nutrition_audit.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

SERVER_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SERVER_ROOT / "packages" / "recipe_scraper" / "src"))

from recipe_scraper.agents.nutrition_agent import NutritionAgent

RECIPES_DIR = SERVER_ROOT / "data" / "recipes"


def main():
    recipe_files = sorted(RECIPES_DIR.glob("*.recipe.json"))
    total = len(recipe_files)
    print(f"Scanning {total} recipes...\n")

    agent = NutritionAgent()

    verdicts = Counter()
    severity_counts = Counter()
    field_issues = Counter()
    high_cal = []
    errors_list = []
    warnings_list = []
    fails = []
    no_nutrition = []
    confidence_dist = Counter()
    resolution_buckets = {"high (>=90%)": 0, "medium (50-89%)": 0, "low (<50%)": 0}
    total_deviation_calories = []
    kcal_per_serving_all = []

    for i, path in enumerate(recipe_files):
        with open(path) as f:
            recipe = json.load(f)

        report = agent.validate(recipe)
        verdicts[report.verdict or "error"] += 1

        if report.error:
            if "No nutritionPerServing" in report.error:
                no_nutrition.append(report.title)
            errors_list.append((report.title, report.error))
            continue

        # Confidence distribution
        nps = recipe.get("metadata", {}).get("nutritionPerServing", {})
        confidence_dist[nps.get("confidence", "unknown")] += 1

        # Kcal per serving
        kcal = nps.get("calories", 0)
        kcal_per_serving_all.append(kcal)

        # Resolution rate
        resolved = nps.get("resolvedIngredients", 0)
        total_ing = nps.get("totalIngredients", 0)
        if total_ing > 0:
            rate = resolved / total_ing
            if rate >= 0.9:
                resolution_buckets["high (>=90%)"] += 1
            elif rate >= 0.5:
                resolution_buckets["medium (50-89%)"] += 1
            else:
                resolution_buckets["low (<50%)"] += 1

        # Calorie deviation
        if report.computed and report.reference and report.reference.calories > 0:
            total_deviation_calories.append(report.deviation_pct.calories)

        # Issues
        for issue in (report.issues or []):
            severity_counts[issue.severity] += 1
            field_issues[issue.field] += 1
            if issue.severity == "error":
                fails.append((report.title, issue.detail))
            elif issue.severity == "warning" and "Very high calories" in issue.detail:
                high_cal.append((report.title, issue.detail))
            elif issue.severity == "warning":
                warnings_list.append((report.title, issue.detail))

    # ── Report ────────────────────────────────────────────────────────
    print("=" * 90)
    print("  RAPPORT D'AUDIT NUTRITION")
    print("=" * 90)

    print(f"\n  Recettes analysees: {total}")
    print(f"  Sans nutrition:     {len(no_nutrition)}")
    print(f"  Avec nutrition:     {total - len(no_nutrition)}")

    # Verdicts
    print(f"\n  ── Verdicts ──")
    for v in ["pass", "warning", "inconclusive", "fail", "error"]:
        count = verdicts.get(v, 0)
        pct = 100 * count / total if total > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"    {v:15s} {count:5d} ({pct:5.1f}%)  {bar}")

    # Confidence
    print(f"\n  ── Confiance ──")
    for level in ["high", "medium", "low", "unknown"]:
        count = confidence_dist.get(level, 0)
        print(f"    {level:10s} {count:5d}")

    # Resolution
    print(f"\n  ── Taux de resolution ingredients ──")
    for bucket, count in resolution_buckets.items():
        print(f"    {bucket:20s} {count:5d}")

    # Kcal distribution
    if kcal_per_serving_all:
        kcal_sorted = sorted(kcal_per_serving_all)
        n = len(kcal_sorted)
        print(f"\n  ── Distribution kcal/serving ──")
        print(f"    Min:      {kcal_sorted[0]:7.0f}")
        print(f"    P10:      {kcal_sorted[n // 10]:7.0f}")
        print(f"    P25:      {kcal_sorted[n // 4]:7.0f}")
        print(f"    Mediane:  {kcal_sorted[n // 2]:7.0f}")
        print(f"    P75:      {kcal_sorted[3 * n // 4]:7.0f}")
        print(f"    P90:      {kcal_sorted[9 * n // 10]:7.0f}")
        print(f"    P99:      {kcal_sorted[int(n * 0.99)]:7.0f}")
        print(f"    Max:      {kcal_sorted[-1]:7.0f}")

        # Buckets
        buckets = {"0": 0, "1-200": 0, "201-400": 0, "401-600": 0, "601-800": 0,
                   "801-1000": 0, "1001-1500": 0, "1501-2000": 0, ">2000": 0}
        for k in kcal_sorted:
            if k == 0:
                buckets["0"] += 1
            elif k <= 200:
                buckets["1-200"] += 1
            elif k <= 400:
                buckets["201-400"] += 1
            elif k <= 600:
                buckets["401-600"] += 1
            elif k <= 800:
                buckets["601-800"] += 1
            elif k <= 1000:
                buckets["801-1000"] += 1
            elif k <= 1500:
                buckets["1001-1500"] += 1
            elif k <= 2000:
                buckets["1501-2000"] += 1
            else:
                buckets[">2000"] += 1

        print(f"\n    Repartition:")
        for bucket, count in buckets.items():
            pct = 100 * count / n
            bar = "█" * int(pct / 2)
            print(f"      {bucket:>10s}: {count:5d} ({pct:5.1f}%)  {bar}")

    # Calorie deviation
    if total_deviation_calories:
        devs = sorted(total_deviation_calories)
        n = len(devs)
        print(f"\n  ── Deviation calories (computed vs reference) ──")
        print(f"    Recettes comparables: {n}")
        print(f"    Deviation mediane:    {devs[n // 2]:5.1f}%")
        print(f"    Deviation moyenne:    {sum(devs) / n:5.1f}%")
        print(f"    Deviation P90:        {devs[int(n * 0.9)]:5.1f}%")
        low_dev = sum(1 for d in devs if d <= 20)
        med_dev = sum(1 for d in devs if 20 < d <= 50)
        high_dev = sum(1 for d in devs if d > 50)
        print(f"    <=20% (bon):          {low_dev:5d} ({100 * low_dev / n:.1f}%)")
        print(f"    20-50% (acceptable):  {med_dev:5d} ({100 * med_dev / n:.1f}%)")
        print(f"    >50% (problematique): {high_dev:5d} ({100 * high_dev / n:.1f}%)")

    # Issues by field
    print(f"\n  ── Issues par champ ──")
    for field, count in field_issues.most_common():
        print(f"    {field:15s} {count:5d}")

    # Top fails
    if fails:
        print(f"\n  ── Top erreurs (deviation >50%) : {len(fails)} ──")
        for title, detail in fails[:15]:
            short = title[:45] + "..." if len(title) > 45 else title
            print(f"    {short}")
            print(f"      {detail[:90]}")

    # High calories
    if high_cal:
        print(f"\n  ── Calories tres elevees : {len(high_cal)} ──")
        for title, detail in high_cal[:10]:
            short = title[:45] + "..." if len(title) > 45 else title
            print(f"    {short}: {detail}")

    # No nutrition
    if no_nutrition:
        print(f"\n  ── Sans nutrition : {len(no_nutrition)} ──")
        for title in no_nutrition[:10]:
            print(f"    {title}")
        if len(no_nutrition) > 10:
            print(f"    ... et {len(no_nutrition) - 10} autres")

    print(f"\n{'=' * 90}")
    print(f"  FIN DU RAPPORT")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
