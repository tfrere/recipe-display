#!/usr/bin/env python3
"""
CLI for the Recipe Review Agent.

Usage:
    # Review a single recipe
    poetry run python -m recipe_scraper.cli_review path/to/recipe.recipe.json

    # Review all recipes in a directory
    poetry run python -m recipe_scraper.cli_review --all --recipes-dir path/to/recipes/

    # Save report to JSON
    poetry run python -m recipe_scraper.cli_review --all --output review_report.json
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from recipe_scraper.agents.review_agent import ReviewAgent
from recipe_scraper.agents.models import ReviewReport

console = Console()


def _score_color(score: float, max_score: float) -> str:
    """Return a Rich color tag based on the score percentage."""
    pct = score / max_score if max_score > 0 else 0
    if pct >= 0.9:
        return "green"
    if pct >= 0.7:
        return "yellow"
    if pct >= 0.5:
        return "dark_orange"
    return "red"


def _print_report(report: ReviewReport) -> None:
    """Pretty-print a single review report to the console."""
    if report.error:
        console.print(f"  [red]ERROR[/red] {report.slug}: {report.error}")
        return

    sc = report.scorecard
    color = _score_color(sc.total_score, sc.total_max)

    console.print(f"\n  [{color}]{sc.score_10}/10[/{color}]  [bold]{report.title}[/bold]")

    table = Table(show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Axe", min_width=28)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Details", max_width=60)

    for axis in [
        sc.ingredient_completeness,
        sc.quantity_accuracy,
        sc.step_completeness,
        sc.dag_semantic_coherence,
        sc.metadata_quality,
    ]:
        c = _score_color(axis.score, axis.max_score)
        issues_str = ""
        if axis.issues:
            issues_str = " | ".join(axis.issues[:3])
            if len(axis.issues) > 3:
                issues_str += f" (+{len(axis.issues) - 3} more)"

        table.add_row(
            axis.axis.replace("_", " ").title(),
            f"[{c}]{axis.score}/{axis.max_score}[/{c}]",
            issues_str or axis.details[:60],
        )

    console.print(table)
    console.print(f"  [dim]{sc.summary}[/dim]")


def _print_summary(reports: List[ReviewReport]) -> None:
    """Print a batch summary table."""
    successful = [r for r in reports if r.scorecard]
    failed = [r for r in reports if r.error]

    if not successful:
        console.print("\n[red]No recipes could be reviewed.[/red]")
        return

    scores = [r.scorecard.score_10 for r in successful]
    avg = sum(scores) / len(scores)

    console.print(f"\n[bold]Batch Summary[/bold]")
    console.print(f"  Reviewed: {len(successful)}  |  Errors: {len(failed)}  |  Avg score: {avg:.1f}/10")

    table = Table(show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Recipe", min_width=40)
    table.add_column("Score", justify="right", min_width=8)

    for r in sorted(successful, key=lambda x: x.scorecard.score_10):
        c = _score_color(r.scorecard.total_score, r.scorecard.total_max)
        table.add_row(r.title, f"[{c}]{r.scorecard.score_10}/10[/{c}]")

    console.print(table)

    if failed:
        console.print(f"\n[red]Errors ({len(failed)}):[/red]")
        for r in failed:
            console.print(f"  [red]-[/red] {r.slug}: {r.error}")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recipe Review Agent — audit recipe fidelity against source text",
    )
    parser.add_argument(
        "recipe", nargs="?", type=str,
        help="Path to a single .recipe.json file",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Review all recipes in the recipes directory",
    )
    parser.add_argument(
        "--recipes-dir", type=str, default=None,
        help="Directory containing .recipe.json files (default: auto-detect)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Save JSON report to this file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not args.recipe and not args.all:
        parser.print_help()
        return 1

    # Find recipe files
    recipe_files: List[Path] = []

    if args.recipe:
        p = Path(args.recipe)
        if not p.exists():
            console.print(f"[red]File not found: {args.recipe}[/red]")
            return 1
        recipe_files = [p]

    elif args.all:
        recipes_dir = Path(args.recipes_dir) if args.recipes_dir else _find_recipes_dir()
        if not recipes_dir or not recipes_dir.is_dir():
            console.print(f"[red]Recipes directory not found. Use --recipes-dir.[/red]")
            return 1
        recipe_files = sorted(recipes_dir.glob("*.recipe.json"))
        if not recipe_files:
            console.print(f"[red]No .recipe.json files found in {recipes_dir}[/red]")
            return 1

    console.print(f"[bold]Recipe Review Agent[/bold]  ({len(recipe_files)} recipe(s))\n")

    agent = ReviewAgent()
    if not agent.is_available:
        console.print("[red]OPENROUTER_API_KEY not set. Cannot run LLM review.[/red]")
        return 1

    reports: List[ReviewReport] = []

    for i, recipe_file in enumerate(recipe_files):
        console.print(
            f"  [{i + 1}/{len(recipe_files)}] Reviewing {recipe_file.stem}...",
            end="",
        )
        try:
            with open(recipe_file, "r", encoding="utf-8") as f:
                recipe_data = json.load(f)

            report = await agent.review(recipe_data)
            reports.append(report)

            if report.error:
                console.print(f" [red]ERROR[/red]")
            else:
                sc = report.scorecard
                c = _score_color(sc.total_score, sc.total_max)
                console.print(f" [{c}]{sc.score_10}/10[/{c}]")

        except Exception as e:
            slug = recipe_file.stem.replace(".recipe", "")
            reports.append(ReviewReport(slug=slug, title=slug, error=str(e)))
            console.print(f" [red]ERROR: {e}[/red]")

    # Print detailed reports for single recipe, summary for batch
    if len(reports) == 1:
        _print_report(reports[0])
    else:
        _print_summary(reports)

    # Save JSON report if requested
    if args.output:
        output_data = [r.model_dump() for r in reports]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        console.print(f"\n[dim]Report saved to {args.output}[/dim]")

    return 0


def _find_recipes_dir() -> Path:
    """Auto-detect the recipes directory."""
    candidates = [
        Path(__file__).parent.parent.parent.parent.parent / "data" / "recipes",
        Path.cwd() / "data" / "recipes",
        Path.cwd() / "server" / "data" / "recipes",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
