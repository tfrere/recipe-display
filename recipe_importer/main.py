import asyncio
import json
import argparse
import os
import shutil
from pathlib import Path
from rich.console import Console
import aiohttp
from src.importer import RecipeImporter

async def clear_output_directories(api_url: str, console: Console) -> None:
    """Nettoie les dossiers d'output (recipes et images) avant l'importation."""
    # Extraire le hostname de l'URL de l'API pour déterminer le chemin du serveur
    server_url = api_url.rstrip("/").split("://")[-1].split(":")[0]
    
    # Utiliser des chemins relatifs ou absolus selon que l'API est locale ou distante
    if server_url in ["localhost", "127.0.0.1"]:
        # Pour une API locale, trouver le répertoire du serveur (conventionnellement à côté du répertoire recipe_importer)
        server_dir = Path(__file__).parent.parent / "server"
        if not server_dir.exists():
            console.print("[yellow]Warning: Could not find local server directory, skipping cleanup[/yellow]")
            return
    else:
        console.print(f"[yellow]Warning: Cannot clean output directories on remote server '{server_url}'[/yellow]")
        return
    
    # Définir les chemins des dossiers à nettoyer
    recipes_dir = server_dir / "data" / "recipes"
    images_dir = recipes_dir / "images"
    
    console.print("[bold cyan]Cleaning output directories...[/bold cyan]")
    
    # Supprimer et recréer le dossier d'images
    if images_dir.exists():
        console.print(f"[yellow]Removing images directory: {images_dir}[/yellow]")
        shutil.rmtree(images_dir)
    
    # Supprimer tous les fichiers JSON dans le dossier de recettes
    if recipes_dir.exists():
        console.print(f"[yellow]Removing recipe files from: {recipes_dir}[/yellow]")
        for recipe_file in recipes_dir.glob("*.json"):
            recipe_file.unlink()
        
        # S'assurer que le dossier d'images existe
        images_dir.mkdir(exist_ok=True, parents=True)
    else:
        console.print(f"[red]Warning: Recipes directory not found: {recipes_dir}[/red]")
        
    console.print("[green]Output directories cleaned successfully[/green]")

async def main():
    parser = argparse.ArgumentParser(description="Import recipes from URLs or text files")
    
    # Groupe de sous-commandes pour les différents modes
    subparsers = parser.add_subparsers(dest="mode", help="Import mode", required=True)
    
    # Sous-commande pour le mode URL
    url_parser = subparsers.add_parser("url", help="Import recipes from a list of URLs")
    url_parser.add_argument(
        "-f", 
        "--file",
        type=str,
        required=True,
        help="Path to JSON file containing URLs to import"
    )
    
    # Sous-commande pour le mode texte
    text_parser = subparsers.add_parser("text", help="Import recipes from text files")
    text_parser.add_argument(
        "-d",
        "--directory",
        type=str,
        required=True,
        help="Directory containing text files and corresponding images"
    )
    
    # Arguments communs aux deux modes
    parser.add_argument(
        "-c",
        "--concurrent",
        type=int,
        default=5,
        help="Number of concurrent imports (default: 5)"
    )
    parser.add_argument(
        "-a",
        "--api-url",
        type=str,
        default="http://localhost:3001",
        help="API server URL (default: http://localhost:3001)"
    )
    parser.add_argument(
        "--auth",
        type=str,
        default="auth_presets.json",
        help="Path to authentication presets JSON file (default: auth_presets.json)"
    )
    parser.add_argument(
        "--list-recipes",
        action="store_true",
        help="List imported recipes after completion"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear output directories (server/data/recipes and images) before importing"
    )
    
    args = parser.parse_args()
    console = Console()
    
    try:
        # Nettoyer les dossiers d'output si demandé
        if args.clear:
            await clear_output_directories(args.api_url, console)
        
        # Créer l'importateur
        importer = RecipeImporter(
            concurrent_imports=args.concurrent,
            api_url=args.api_url,
            auth_presets_file=args.auth,
            console=console
        )
        
        if args.mode == "url":
            # Vérifier que le fichier d'URLs existe
            urls_file = Path(args.file)
            if not urls_file.exists():
                console.print(f"[red]Error: File {args.file} not found[/red]")
                return
                
            # Charger les URLs depuis le fichier JSON
            with open(urls_file) as f:
                data = json.load(f)
                if not isinstance(data, list):
                    console.print("[red]Error: JSON file must contain a list of URLs[/red]")
                    return
                urls = data
                
            # Lancer l'importation des URLs
            await importer.import_recipes(urls)
            
        elif args.mode == "text":
            # Vérifier que le dossier existe
            text_dir = Path(args.directory)
            if not text_dir.exists() or not text_dir.is_dir():
                console.print(f"[red]Error: Directory {args.directory} not found or is not a directory[/red]")
                return
                
            # Trouver tous les fichiers texte
            text_files = list(text_dir.glob("*.txt"))
            if not text_files:
                console.print(f"[red]Error: No .txt files found in {args.directory}[/red]")
                return
                
            # Préparer les données pour l'importation
            recipe_files = []
            for text_file in text_files:
                base_name = text_file.stem
                
                # Rechercher une image dans différents formats possibles
                image_file = None
                for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    possible_image = text_dir / f"{base_name}{ext}"
                    if possible_image.exists():
                        image_file = possible_image
                        break
                        
                if not image_file:
                    console.print(f"[yellow]Warning: No image file found for {base_name}.txt, will import without image[/yellow]")
                    
                recipe_files.append((text_file, image_file))
                
            # Lancer l'importation des fichiers texte
            await importer.import_text_recipes(recipe_files)
        
        # Lister les recettes importées si demandé
        if args.list_recipes:
            console.print("\n[bold yellow]Listing imported recipes...[/bold yellow]")
            async with aiohttp.ClientSession() as session:
                await importer.list_imported_recipes(session)
        
    except json.JSONDecodeError:
        console.print("[red]Error: Invalid JSON file[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    asyncio.run(main())
