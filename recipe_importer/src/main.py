"""Point d'entrée CLI de l'importateur de recettes."""

import asyncio
import json
import argparse
import shutil
from pathlib import Path

from rich.console import Console

from src.importer import RecipeImporter


async def clear_output(console: Console) -> None:
    """Nettoie les dossiers d'output (recipes et images) avant l'importation."""
    server_dir = Path(__file__).parent.parent.parent / "server"
    if not server_dir.exists():
        console.print("[yellow]Dossier serveur introuvable, nettoyage ignoré[/yellow]")
        return

    recipes_dir = server_dir / "data" / "recipes"
    images_dir = recipes_dir / "images"

    console.print("[bold cyan]Nettoyage des dossiers…[/bold cyan]")

    if images_dir.exists():
        shutil.rmtree(images_dir)
    if recipes_dir.exists():
        for f in recipes_dir.glob("*.json"):
            f.unlink()

    images_dir.mkdir(parents=True, exist_ok=True)
    console.print("[green]Dossiers nettoyés[/green]")


async def main():
    parser = argparse.ArgumentParser(description="Import recipes from URLs or text files")

    # Arguments communs
    parser.add_argument("-c", "--concurrent", type=int, default=10, help="Concurrent imports (default: 10)")
    parser.add_argument("-a", "--api-url", type=str, default="http://localhost:3001", help="API URL")
    parser.add_argument("--auth", type=str, default="auth_presets.json", help="Auth presets file")
    parser.add_argument("--list-recipes", action="store_true", help="List recipes after import")
    parser.add_argument("--clear", action="store_true", help="Clear recipes before import")
    parser.add_argument("--headless", action="store_true", help="No TUI, console output only")
    parser.add_argument("--max-per-domain", type=int, default=8, help="Max concurrent requests per domain (default: 8)")

    # Sous-commandes
    subparsers = parser.add_subparsers(dest="mode", required=True)

    url_parser = subparsers.add_parser("url", help="Import from URLs")
    url_parser.add_argument("-f", "--file", type=str, required=True, help="JSON file with URLs")

    text_parser = subparsers.add_parser("text", help="Import from text files")
    text_parser.add_argument("-d", "--directory", type=str, required=True, help="Directory with .txt + images")

    args = parser.parse_args()
    console = Console()

    try:
        if args.clear:
            await clear_output(console)

        importer = RecipeImporter(
            concurrent_imports=args.concurrent,
            api_url=args.api_url,
            auth_presets_file=args.auth,
            console=console,
            headless=args.headless,
            max_per_domain=args.max_per_domain,
        )

        if args.mode == "url":
            urls_file = Path(args.file)
            if not urls_file.exists():
                console.print(f"[red]Fichier introuvable: {args.file}[/red]")
                return

            with open(urls_file) as f:
                urls = json.load(f)
            if not isinstance(urls, list):
                console.print("[red]Le fichier JSON doit contenir une liste d'URLs[/red]")
                return

            await importer.import_urls(urls)

        elif args.mode == "text":
            text_dir = Path(args.directory)
            if not text_dir.is_dir():
                console.print(f"[red]Dossier introuvable: {args.directory}[/red]")
                return

            text_files = list(text_dir.glob("*.txt"))
            if not text_files:
                console.print(f"[red]Aucun .txt trouvé dans {args.directory}[/red]")
                return

            # Associer chaque .txt à son image (même nom, extension image)
            recipe_files = []
            for tf in text_files:
                image = None
                for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                    candidate = tf.with_suffix(ext)
                    if candidate.exists():
                        image = candidate
                        break
                if not image:
                    console.print(f"[yellow]Pas d'image pour {tf.name}[/yellow]")
                recipe_files.append((tf, image))

            await importer.import_text_recipes(recipe_files)

        if args.list_recipes:
            await importer.list_imported_recipes()

    except json.JSONDecodeError:
        console.print("[red]Fichier JSON invalide[/red]")
    except Exception as e:
        console.print(f"[red]Erreur: {e}[/red]")


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
