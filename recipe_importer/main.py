import asyncio
import json
import argparse
from pathlib import Path
from rich.console import Console
from importer import RecipeImporter

async def main():
    parser = argparse.ArgumentParser(description="Import recipes from URLs")
    parser.add_argument(
        "-f", 
        "--file",
        type=str,
        required=True,
        help="Path to JSON file containing URLs to import"
    )
    parser.add_argument(
        "-c",
        "--concurrent",
        type=int,
        default=5,
        help="Number of concurrent imports (default: 5)"
    )
    
    args = parser.parse_args()
    console = Console()
    
    # Vérifier que le fichier existe
    urls_file = Path(args.file)
    if not urls_file.exists():
        console.print(f"[red]Error: File {args.file} not found[/red]")
        return
        
    try:
        # Charger les URLs depuis le fichier JSON
        with open(urls_file) as f:
            data = json.load(f)
            if not isinstance(data, list):
                console.print("[red]Error: JSON file must contain a list of URLs[/red]")
                return
            urls = data
            
        # Créer et lancer l'importateur
        importer = RecipeImporter(
            concurrent_imports=args.concurrent,
            console=console
        )
        await importer.import_recipes(urls)
        
    except json.JSONDecodeError:
        console.print("[red]Error: Invalid JSON file[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    asyncio.run(main())
