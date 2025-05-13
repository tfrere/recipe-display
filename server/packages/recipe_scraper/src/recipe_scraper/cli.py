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
import time
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
    # Initialize variables
    image_path = None
    credentials = None
    
    try:
        # Load credentials if provided
        if args.credentials:
            try:
                with open(args.credentials, "r") as f:
                    credentials = json.load(f)
                logging.info(f"Reading authentication credentials from: {args.credentials}")
            except Exception as e:
                logging.error(f"Failed to read credentials file: {str(e)}")
                return 1

        # Initialize scraper with correct paths immediately
        scraper = RecipeScraper()
        
        # Convert paths to absolute paths to avoid relative path issues
        recipe_output_folder = os.path.abspath(args.recipe_output_folder)
        image_output_folder = os.path.abspath(args.image_output_folder)
        
        # Set the paths before any operations that might check for existing recipes
        scraper._recipe_output_folder = Path(recipe_output_folder)
        scraper._image_output_folder = Path(image_output_folder)
        
        logging.info(f"Recipe output folder: {scraper._recipe_output_folder}")
        logging.info(f"Image output folder: {scraper._image_output_folder}")

        # Create progress callback if not quiet
        progress_callback = None
        if not args.quiet:
            async def progress_callback(message: str):
                print(f">>> {message}")

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
            if args.image_file:
                try:
                    # Check if image file exists
                    image_path = Path(args.image_file)
                    if not image_path.exists():
                        logging.error(f"Image file not found: {args.image_file}")
                        return 1
                    
                    # Reference image in the text content
                    image_filename = image_path.name
                    image_reference = f"\nMain recipe image: {image_filename}"
                    
                    # Only add the image reference if it's not already mentioned
                    if "Image:" not in text_content:
                        modified_text_content = f"{text_content}{image_reference}"
                        logging.info(f"Added image reference to text: {image_filename}")
                    
                except Exception as e:
                    logging.error(f"Error processing image file: {str(e)}")
                    return 1
            
            # Scrape from text, passing the input file name for slug checking
            recipe_data = await scraper.scrape_from_text(
                modified_text_content, 
                file_name=args.input_file, 
                progress_callback=progress_callback if not args.quiet else None
            )
            
            # Check if recipe already exists (will return None if duplicate)
            if recipe_data is None:
                logging.warning(f"Recipe with similar content already exists")
                if not args.force:
                    logging.info("Use --force to override this check")
                    # Print a specific error message that can be detected by the service
                    print("ERROR: Recipe already exists (similar content detected with high similarity)")
                    # Exit with error code 100 (specific to duplicates)
                    return 100  # Exit with a specific error code for duplicates
                else:
                    logging.info("Force flag is set. Continuing with recipe generation...")
                    # Re-attempt the scraping with a modified hash to bypass the check
                    # Add a timestamp to make the content unique
                    timestamp = str(time.time())
                    modified_content = f"{modified_text_content}\n\n<!-- Generated at: {timestamp} -->"
                    recipe_data = await scraper.scrape_from_text(
                        modified_content,
                        file_name=args.input_file,
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
            json_path = scraper._recipe_output_folder / f"{slug}.recipe.json" 
            with open(json_path, 'w') as f:
                json.dump(recipe_data, f, indent=2)
            
            # Copy the image to the images directory if provided
            if image_path and image_path.exists():
                try:
                    # Create image destination path
                    image_ext = image_path.suffix.lstrip('.')  # Get extension without dot
                    image_dest = scraper._image_output_folder / f"{slug}.{image_ext}"
                    
                    # Copy the image
                    import shutil
                    shutil.copy2(image_path, image_dest)
                    
                    # Update the image path in the recipe metadata
                    if "metadata" not in recipe_data:
                        recipe_data["metadata"] = {}
                    recipe_data["metadata"]["sourceImageUrl"] = f"{slug}.{image_ext}"
                    recipe_data["metadata"]["image"] = f"images/{slug}.{image_ext}"
                    
                    # Update the JSON file again with the image path
                    with open(json_path, 'w') as f:
                        json.dump(recipe_data, f, indent=2)
                        
                    logging.info(f"Image copied to: {image_dest}")
                except Exception as e:
                    logging.error(f"Error copying image: {str(e)}")
            
            logging.info(f"Recipe successfully saved to: {json_path}")
            return 0
        elif recipe_data and "error" in recipe_data:
            # Vérifier si c'est une erreur de recette existante
            if "Recipe already exists" in recipe_data["error"]:
                error_msg = f"Recipe already exists: {recipe_data.get('file', '')}"
                if "slug" in recipe_data:
                    error_msg += f", slug: {recipe_data['slug']}"
                logging.error(error_msg)
                print(error_msg, file=sys.stderr)
                return 1
            else:
                logging.error(f"Error: {recipe_data['error']}")
                print(f"Error: {recipe_data['error']}", file=sys.stderr)
                return 1
        else:
            error_msg = "Failed to generate recipe from text"
            logging.error(error_msg)
            print(error_msg, file=sys.stderr)
            return 1
        
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return 1
        
    finally:
        # Clean up temporary credentials file
        if args.credentials and Path(args.credentials).exists():
            try:
                Path(args.credentials).unlink()
                logging.debug(f"Removed temporary credentials file: {args.credentials}")
            except Exception as e:
                logging.error(f"Failed to remove temporary credentials file: {str(e)}")

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