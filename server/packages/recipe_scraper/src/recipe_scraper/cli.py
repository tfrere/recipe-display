#!/usr/bin/env python3
"""
Command-line interface for recipe-scraper.
This tool scrapes recipes from URLs or text files, structures them, and saves them as JSON.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .scraper import RecipeScraper

def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    # Set default log level for all loggers
    logging.getLogger().setLevel(log_level)
    
    # Reduce verbosity of some loggers
    if not verbose:
        # Set more specific log levels for our components
        logging.getLogger("web_scraper").setLevel(logging.WARNING)
        logging.getLogger("recipe_structurer").setLevel(logging.WARNING)
        logging.getLogger("recipe_scraper.recipe_enricher").setLevel(logging.WARNING)
        
        # And for external libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

def parse_credentials(credentials_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse authentication credentials from a JSON file."""
    if not credentials_path:
        return None
    
    try:
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
        
        # Extract the first preset, or return None if empty
        if not credentials_data:
            return None
        
        # Return the first preset's values
        first_domain = next(iter(credentials_data))
        return credentials_data[first_domain]
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error reading credentials file: {e}")
        return None

async def main_async(args: argparse.Namespace) -> int:
    """Asynchronous main function to handle recipe scraping."""
    # Setup the output folders
    recipe_output_folder = Path(args.recipe_output_folder)
    image_output_folder = Path(args.image_output_folder)
    recipe_output_folder.mkdir(parents=True, exist_ok=True)
    image_output_folder.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"Starting recipe scraper with mode: {args.mode}")
    logging.info(f"Recipe output folder: {recipe_output_folder.absolute()}")
    logging.info(f"Image output folder: {image_output_folder.absolute()}")
    
    # Create the scraper
    scraper = RecipeScraper()
    
    # Set the output folders for recipes and images
    scraper._recipe_output_folder = recipe_output_folder
    scraper._image_output_folder = image_output_folder
    
    # Parse credentials if provided
    credentials = None
    if args.credentials:
        logging.info(f"Reading authentication credentials from: {args.credentials}")
        credentials = parse_credentials(args.credentials)
        if not credentials:
            logging.warning("No valid credentials found or failed to parse credentials file")
    
    # Define the progress callback function
    async def progress_callback(message: str):
        # In non-verbose mode, we only print the main stage updates
        if not args.verbose:
            print(f">>> {message}")
        else:
            # Ensure that all progress messages in verbose mode also use the >>> prefix
            # so the recipe_service can properly track them
            if "Fetching" in message or "Structuring" in message or "Processing" in message or \
               "Saving" in message or "sauvegarde" in message.lower() or "Downloading" in message or \
               "Enriching" in message:
                print(f">>> {message}")
            else:
                print(f"CLI output: {message}")
    
    try:
        recipe_data = {}
        
        if args.mode == "url":
            if not args.url:
                logging.error("URL must be provided in URL mode")
                return 1
                
            logging.info(f"Processing URL: {args.url}")
            
            # Check if recipe already exists before scraping
            existing_recipe = scraper._recipe_exists(args.url)
            if existing_recipe and not args.force:
                logging.warning(f"Recipe already exists: {existing_recipe}")
                logging.info("Use --force to override this check")
                return 0  # Exit with success since it's not an error
            elif existing_recipe and args.force:
                logging.info(f"Recipe exists at {existing_recipe}, but force flag is set. Continuing...")
            
            # Scrape from URL
            recipe_data = await scraper.scrape_from_url(
                args.url, 
                credentials,
                progress_callback=progress_callback if not args.quiet else None
            )
            
        else:  # text mode
            if not args.input_file:
                logging.error("Input file must be provided in text mode")
                return 1
                
            logging.info(f"Processing text file: {args.input_file}")
            
            # Read text from file
            try:
                with open(args.input_file, 'r') as f:
                    text_content = f.read()
                    logging.info(f"Successfully read {len(text_content)} characters from input file")
            except FileNotFoundError:
                logging.error(f"Input file not found: {args.input_file}")
                return 1
            except Exception as e:
                logging.error(f"Error reading input file: {str(e)}")
                return 1
            
            # Process image file if provided
            modified_text_content = text_content
            image_path = None
            if args.image_file:
                try:
                    # Check if image file exists
                    image_file_path = Path(args.image_file)
                    if not image_file_path.exists():
                        logging.error(f"Image file not found: {args.image_file}")
                        return 1
                    
                    # Reference image in the text content
                    image_filename = image_file_path.name
                    image_reference = f"\n\Main recipe image: {image_filename}"
                    
                    # Only add the image reference if it's not already mentioned
                    if "Image:" not in text_content:
                        modified_text_content = f"{text_content}{image_reference}"
                        logging.info(f"Added image reference to text: {image_filename}")
                    
                    # Store the image path for later processing
                    image_path = image_file_path
                    
                except Exception as e:
                    logging.error(f"Error processing image file: {str(e)}")
                    return 1
            
            # Scrape from text, passing the input file name for slug checking
            recipe_data = await scraper.scrape_from_text(
                modified_text_content, 
                file_name=args.input_file, 
                progress_callback=progress_callback if not args.quiet else None
            )
            
            # Check if a duplicate was detected
            if "error" in recipe_data and recipe_data.get("error") == "Recipe already exists":
                if not args.force:
                    logging.warning(f"Recipe with similar title already exists: {recipe_data.get('file')}")
                    logging.info(f"Duplicate detected with slug: {recipe_data.get('slug', 'unknown')}")
                    logging.info("Use --force to override this check")
                    return 0  # Exit with success since it's not an error
                else:
                    logging.info(f"Recipe with similar title exists, but force flag is set. Continuing...")
                    # We need to re-process but force it to continue
                    recipe_data = await scraper.scrape_from_text(
                        modified_text_content,
                        progress_callback=progress_callback if not args.quiet else None
                    )
        
        # Save the data
        if recipe_data and "error" not in recipe_data:
            # Get the slug for the filename
            slug = recipe_data.get("metadata", {}).get("slug", "recipe")
            
            # Stream final step
            if not args.quiet:
                print(f">>> Sauvegarde de la recette")
            
            # Ensure totalCookingTime is available at the root level if present in metadata
            if "totalCookingTime" in recipe_data.get("metadata", {}):
                recipe_data["totalCookingTime"] = recipe_data["metadata"]["totalCookingTime"]
            
            # Save JSON
            json_path = recipe_output_folder / f"{slug}.recipe.json" 
            with open(json_path, 'w') as f:
                json.dump(recipe_data, f, indent=2)
            
            # Copy the image to the images directory if provided
            if image_path and image_path.exists():
                try:
                    # Create image destination path
                    image_dest = image_output_folder / image_path.name
                    
                    # Copy the image
                    import shutil
                    shutil.copy2(image_path, image_dest)
                    
                    # Update the image path in the recipe metadata if not already set
                    if not recipe_data.get("metadata", {}).get("sourceImageUrl"):
                        if "metadata" not in recipe_data:
                            recipe_data["metadata"] = {}
                        recipe_data["metadata"]["sourceImageUrl"] = image_path.name
                        
                        # Update the JSON file again with the image path
                        with open(json_path, 'w') as f:
                            json.dump(recipe_data, f, indent=2)
                        
                    logging.info(f"Image copied to: {image_dest}")
                except Exception as e:
                    logging.error(f"Error copying image: {str(e)}")
            
            logging.info(f"Recipe successfully saved to: {json_path}")
            
            # Report some stats about the recipe
            title = recipe_data.get("metadata", {}).get("title", "Untitled recipe")
            ingredient_count = len(recipe_data.get("ingredients", []))
            step_count = len(recipe_data.get("steps", []))
            diets = recipe_data.get("metadata", {}).get("diets", [])
            seasons = recipe_data.get("metadata", {}).get("seasons", [])
            
            logging.info(f"Recipe summary: \"{title}\" - {ingredient_count} ingredients, {step_count} steps")
            logging.info(f"Diet classifications: {', '.join(diets)}")
            logging.info(f"Seasonal availability: {', '.join(seasons)}")
            
            return 0
        elif "error" in recipe_data:
            # This is not an error case, just a notification
            # Make sure to print this in the right format for tracking
            if "Recipe already exists" in recipe_data.get("error", ""):
                print(f">>> Recipe already exists: {recipe_data.get('slug', 'unknown')}")
            return 0  
        else:
            logging.error("Failed to process recipe: No data returned from scraper")
            return 1
            
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

def main() -> int:
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Scrape and structure recipes from URLs or text files"
    )
    
    parser.add_argument(
        "--mode",
        choices=["url", "text"],
        required=True,
        help="Scraping mode: 'url' for web scraping, 'text' for text file processing"
    )
    
    parser.add_argument(
        "--url",
        help="URL to scrape (required in 'url' mode)"
    )
    
    parser.add_argument(
        "--input-file",
        help="Text file to process (required in 'text' mode)"
    )
    
    parser.add_argument(
        "--image-file",
        help="Image file to include with the text recipe (only for 'text' mode)"
    )
    
    parser.add_argument(
        "--credentials",
        help="Path to JSON file containing authentication credentials"
    )
    
    parser.add_argument(
        "--recipe-output-folder",
        default="./data/recipes",
        help="Folder to save the recipe JSON files (default: ./data/recipes)"
    )
    
    parser.add_argument(
        "--image-output-folder",
        default="./data/recipes/images",
        help="Folder to save the downloaded images (default: ./data/recipes/images)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging with detailed information"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Disable streaming progress updates"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force processing even if recipe already exists"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Run the async main function
    return asyncio.run(main_async(args))

if __name__ == "__main__":
    sys.exit(main()) 