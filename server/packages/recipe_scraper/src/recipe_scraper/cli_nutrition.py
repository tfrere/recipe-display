#!/usr/bin/env python3
"""
CLI for the Nutrition Validation Agent.

Usage:
    # Validate a single recipe
    poetry run python -m recipe_scraper.cli_nutrition path/to/recipe.recipe.json

    # Validate all recipes in a directory
    poetry run python -m recipe_scraper.cli_nutrition --all

    # Save report to JSON
    poetry run python -m recipe_scraper.cli_nutrition --all --output nutrition_report.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from recipe_scraper.agents.nutrition_agent import NutritionAgent
from recipe_scraper.agents.models import NutritionReport

console = Console()


def _verdict_style(verdict: str) -> str:
    """Return a Rich color for the verdict."""
    return {"pass": "green", "warning": "yellow", "fail": "red"}.get(verdict, "dim")


def _dev_color(dev: float) -> str:
    """Return a Rich color based on deviation percentage."""
    if dev <= 10:
        return "green"
    if dev <= 30:
        return "yellow"
    if dev <= 50:
        return "dark_orange"
    return "red"


def _print_report(report: NutritionReport) -> None:
    """Pretty-print a single nutrition report."""
    if report.error:
        console.print(f"  [red]ERROR[/red] {report.slug}: {report.error}")
        return

    style = _verdict_style(report.verdict)
    console.print(f"\n  [{style}]{report.verdict.upper()}[/{style}]  [bold]{report.title}[/bold]")

    table = Table(show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Macro", min_width=10)
    table.add_column("Computed", justify="right", min_width=10)
    table.add_column("Reference", justify="right", min_width=10)
    table.add_column("Deviation", justify="right", min_width=10)

    for field in ["calories", "protein", "fat", "carbs", "fiber"]:
        comp_val = getattr(report.computed, field, 0)
        ref_val = getattr(report.reference, field, 0)
        dev_val = getattr(report.deviation_pct, field, 0)

        unit = "kcal" if field == "calories" else "g"
        c = _dev_color(dev_val)

        table.add_row(
            field.capitalize(),
            f"{comp_val} {unit}",
            f"{ref_val} {unit}",
            f"[{c}]{dev_val}%[/{c}]",
        )

    console.print(table)

    if report.issues:
        console.print(f"\n  Issues ({len(report.issues)}):")
        for issue in report.issues:
            icon = "[red]x[/red]" if issue.severity == "error" else "[yellow]![/yellow]"
            console.print(f"    {icon} {issue.detail}")

    # Ingredient match summary
    matched = sum(1 for d in report.ingredient_details if d.matched_in_ref)
    total = len(report.ingredient_details)
    console.print(f"\n  [dim]Ingredients matched in reference: {matched}/{total}[/dim]")


def _print_summary(reports: List[NutritionReport]) -> None:
    """Print a batch summary table."""
    successful = [r for r in reports if not r.error]
    failed = [r for r in reports if r.error]

    if not successful:
        console.print("\n[red]No recipes could be validated.[/red]")
        return

    pass_count = sum(1 for r in successful if r.verdict == "pass")
    warn_count = sum(1 for r in successful if r.verdict == "warning")
    fail_count = sum(1 for r in successful if r.verdict == "fail")

    console.print(f"\n[bold]Batch Summary[/bold]")
    console.print(
        f"  [green]{pass_count} pass[/green]  "
        f"[yellow]{warn_count} warning[/yellow]  "
        f"[red]{fail_count} fail[/red]  "
        f"[dim]{len(failed)} errors[/dim]"
    )

    # Show only problematic recipes
    problematic = [r for r in successful if r.verdict != "pass"]
    if problematic:
        table = Table(show_header=True, header_style="bold", padding=(0, 1))
        table.add_column("Recipe", min_width=40)
        table.add_column("Verdict", min_width=8)
        table.add_column("Issues", min_width=30)

        for r in sorted(problematic, key=lambda x: x.verdict):
            style = _verdict_style(r.verdict)
            issues_str = "; ".join(i.detail[:50] for i in r.issues[:3])
            table.add_row(
                r.title,
                f"[{style}]{r.verdict}[/{style}]",
                issues_str,
            )

        console.print(table)

    if failed:
        console.print(f"\n[red]Errors ({len(failed)}):[/red]")
        for r in failed:
            console.print(f"  [red]-[/red] {r.slug}: {r.error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nutrition Validation Agent — cross-check recipe nutrition against OpenNutrition reference",
    )
    parser.add_argument(
        "recipe", nargs="?", type=str,
        help="Path to a single .recipe.json file",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Validate all recipes in the recipes directory",
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

    console.print(f"[bold]Nutrition Validation Agent[/bold]  ({len(recipe_files)} recipe(s))\n")

    agent = NutritionAgent()
    reports: List[NutritionReport] = []

    for i, recipe_file in enumerate(recipe_files):
        console.print(
            f"  [{i + 1}/{len(recipe_files)}] Validating {recipe_file.stem}...",
            end="",
        )
        try:
            with open(recipe_file, "r", encoding="utf-8") as f:
                recipe_data = json.load(f)

            report = agent.validate(recipe_data)
            reports.append(report)

            if report.error:
                console.print(f" [red]ERROR[/red]")
            else:
                style = _verdict_style(report.verdict)
                console.print(f" [{style}]{report.verdict}[/{style}]")

        except Exception as e:
            slug = recipe_file.stem.replace(".recipe", "")
            reports.append(NutritionReport(slug=slug, title=slug, error=str(e)))
            console.print(f" [red]ERROR: {e}[/red]")

    # Print detailed report for single recipe, summary for batch
    if len(reports) == 1:
        _print_report(reports[0])
    else:
        _print_summary(reports)

    # Save JSON report
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
    sys.exit(main())
