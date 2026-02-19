"""Score 20 random recipes using the ReviewAgent."""

import asyncio
import json
import os
import random
import sys
from pathlib import Path

# Add the recipe_scraper package to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "recipe_scraper" / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from recipe_scraper.agents.review_agent import ReviewAgent


RECIPES_DIR = Path(__file__).parent.parent / "data" / "recipes"
NUM_RECIPES = 20


async def main():
    recipe_files = list(RECIPES_DIR.glob("*.recipe.json"))
    if len(recipe_files) < NUM_RECIPES:
        print(f"Only {len(recipe_files)} recipes available, scoring all.")
        selected = recipe_files
    else:
        selected = random.sample(recipe_files, NUM_RECIPES)

    agent = ReviewAgent()
    if not agent.is_available:
        print("ERROR: ReviewAgent not available (missing OPENROUTER_API_KEY)")
        return

    print(f"Scoring {len(selected)} random recipes with Gemini 2.5 Flash...\n")
    print(f"{'Recipe':<50} {'Score':>6} {'Ingr':>5} {'Qty':>5} {'Steps':>5} {'DAG':>5} {'Meta':>5}")
    print("─" * 90)

    reports = []
    errors = []

    for i, recipe_path in enumerate(selected, 1):
        with open(recipe_path) as f:
            recipe_data = json.load(f)

        title = recipe_data.get("metadata", {}).get("title", recipe_path.stem)
        short_title = title[:47] + "..." if len(title) > 50 else title

        report = await agent.review(recipe_data)

        if report.error:
            errors.append((short_title, report.error))
            print(f"  [{i:>2}/{len(selected)}] {short_title:<50} {'ERROR':>6}  {report.error[:30]}")
        else:
            sc = report.scorecard
            score_str = f"{sc.total_score:.0f}/100"
            print(
                f"  [{i:>2}/{len(selected)}] {short_title:<50} {score_str:>6}"
                f" {sc.ingredient_completeness.score:>5.0f}"
                f" {sc.quantity_accuracy.score:>5.0f}"
                f" {sc.step_completeness.score:>5.0f}"
                f" {sc.dag_semantic_coherence.score:>5.0f}"
                f" {sc.metadata_quality.score:>5.0f}"
            )
            reports.append(report)

    # Summary
    if reports:
        scores = [r.scorecard.total_score for r in reports]
        avg = sum(scores) / len(scores)
        median = sorted(scores)[len(scores) // 2]
        min_score = min(scores)
        max_score = max(scores)
        min_recipe = next(r for r in reports if r.scorecard.total_score == min_score)
        max_recipe = next(r for r in reports if r.scorecard.total_score == max_score)

        # Per-axis averages
        avg_ingr = sum(r.scorecard.ingredient_completeness.score for r in reports) / len(reports)
        avg_qty = sum(r.scorecard.quantity_accuracy.score for r in reports) / len(reports)
        avg_steps = sum(r.scorecard.step_completeness.score for r in reports) / len(reports)
        avg_dag = sum(r.scorecard.dag_semantic_coherence.score for r in reports) / len(reports)
        avg_meta = sum(r.scorecard.metadata_quality.score for r in reports) / len(reports)

        print("\n" + "═" * 90)
        print(f"\n  RÉSUMÉ ({len(reports)} recettes scorées, {len(errors)} erreurs)\n")
        print(f"  Score moyen:  {avg:.1f}/100  ({avg/10:.1f}/10)")
        print(f"  Médiane:      {median:.0f}/100")
        print(f"  Min:          {min_score:.0f}/100 — {min_recipe.title}")
        print(f"  Max:          {max_score:.0f}/100 — {max_recipe.title}")
        print(f"\n  Moyennes par axe:")
        print(f"    Ingrédients (/{30}):   {avg_ingr:.1f}")
        print(f"    Quantités (/{25}):     {avg_qty:.1f}")
        print(f"    Étapes (/{25}):        {avg_steps:.1f}")
        print(f"    DAG sémantique (/{10}): {avg_dag:.1f}")
        print(f"    Métadonnées (/{10}):   {avg_meta:.1f}")

        # Bottom 5
        bottom = sorted(reports, key=lambda r: r.scorecard.total_score)[:5]
        print(f"\n  Bottom 5:")
        for r in bottom:
            print(f"    {r.scorecard.total_score:>3.0f}/100 — {r.title}")
            if r.scorecard.ingredient_completeness.issues:
                for issue in r.scorecard.ingredient_completeness.issues[:2]:
                    print(f"             ⚠ ingr: {issue[:80]}")
            if r.scorecard.step_completeness.issues:
                for issue in r.scorecard.step_completeness.issues[:2]:
                    print(f"             ⚠ step: {issue[:80]}")

    if errors:
        print(f"\n  Erreurs ({len(errors)}):")
        for title, err in errors:
            print(f"    ✗ {title}: {err[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
