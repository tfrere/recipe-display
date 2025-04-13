"""
RecipeScraper package combines web_scraper and recipe_structurer to extract and structure recipes.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import uuid
from dotenv import load_dotenv
import unicodedata  # Added for handling accents
from datetime import datetime

# Load environment variables
load_dotenv()

import httpx
from pydantic import BaseModel, ValidationError
from slugify import slugify

from web_scraper import WebScraper
from web_scraper.models import WebContent, AuthPreset
from recipe_structurer import RecipeStructurer
from .recipe_enricher import RecipeEnricher

logger = logging.getLogger(__name__)

class RecipeScraper:
    """
    A class that combines web scraping and recipe structuring to extract and save recipes.
    """
    
    def __init__(self):
        """Initialize the RecipeScraper with web_scraper and recipe_structurer."""
        self.web_scraper = WebScraper()
        self.recipe_structurer = RecipeStructurer("huggingface")  # Using deepseek as default provider
        self.recipe_enricher = RecipeEnricher()  # Initialize the recipe enricher
        self._recipe_output_folder = Path("./data/recipes")  # Default recipe output folder
        self._image_output_folder = Path("./data/recipes/images")  # Default image output folder
    
    def _check_slug_exists(self, slug: str) -> Optional[str]:
        """
        Check if a recipe with the given slug already exists.
        
        Args:
            slug: The slug to check
            
        Returns:
            The path to the existing recipe file if found, None otherwise
        """
        if not self._recipe_output_folder.exists():
            return None
            
        # Check for exact slug match
        recipe_file = self._recipe_output_folder / f"{slug}.recipe.json"
        if recipe_file.exists():
            logger.info(f"Recipe with slug '{slug}' already exists: {recipe_file}")
            return str(recipe_file)
            
        return None
        
    def _recipe_exists(self, url: str) -> Optional[str]:
        """
        Check if a recipe from the given URL already exists in the output folder.
        
        Args:
            url: The URL of the recipe to check
            
        Returns:
            The path to the existing recipe file if found, None otherwise
        """
        if not self._recipe_output_folder.exists():
            return None
            
        # Look for recipe files in the output folder
        recipe_files = list(self._recipe_output_folder.glob("*.recipe.json"))
        
        # If there are no recipe files, return None
        if not recipe_files:
            return None
            
        # Check each recipe file for the sourceUrl first (priority check)
        for recipe_file in recipe_files:
            try:
                with open(recipe_file, "r") as f:
                    recipe_data = json.load(f)
                    
                # Check if the sourceUrl matches (exact match)
                source_url = recipe_data.get("metadata", {}).get("sourceUrl")
                if source_url and source_url == url:
                    logger.info(f"Recipe from URL {url} already exists: {recipe_file}")
                    return str(recipe_file)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        # Now check slug only as a fallback if we didn't find an exact URL match
        # Extract potential title from URL to check slug
        url_parts = url.rstrip('/').split('/')
        if url_parts:
            potential_title = url_parts[-1].replace('-', ' ').replace('_', ' ')
            potential_slug = self._generate_slug(potential_title)
            
            # Check if a recipe with this slug already exists
            slug_match = self._check_slug_exists(potential_slug)
            if slug_match:
                logger.info(f"Recipe with similar slug from URL {url} might exist: {slug_match}")
                return slug_match
                
        return None
        
    async def scrape_from_url(self, url: str, auth_values: Optional[Dict[str, Any]] = None, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Scrape a recipe from a URL, structure it, and download one image.
        
        Args:
            url: The URL of the recipe to scrape
            auth_values: Optional authentication values for the website
            progress_callback: Optional callback for streaming progress updates
            
        Returns:
            A dictionary containing the structured recipe data
        """
        if progress_callback:
            await progress_callback("Starting recipe processing")
            
        logger.info(f"Scraping recipe from URL: {url}")
        
        # Create auth preset if authentication provided
        auth_preset = None
        if auth_values:
            try:
                auth_preset = AuthPreset(
                    type=auth_values.get("type", "cookie"),
                    domain=url.split("//")[-1].split("/")[0],  # Extract domain from URL
                    values=auth_values.get("values", {}),
                    description=auth_values.get("description", "Automatic auth preset")
                )
                logger.debug(f"Authentication preset created for domain: {auth_preset.domain}")
            except ValidationError as e:
                logger.warning(f"Failed to create authentication preset: {str(e)}")
                auth_preset = None
        
        # Scrape the web content
        if progress_callback:
            await progress_callback("Fetching web content")
            
        logger.info("Fetching web content...")
        async with self.web_scraper as scraper:
            web_content = await scraper.scrape_url(url, auth_preset)
            
        if not web_content:
            logger.error("Failed to scrape web content: No content retrieved from URL")
            return {}
        
        logger.debug(f"Web content successfully retrieved. Title: \"{web_content.title}\"")
        
        # Structure the recipe
        recipe_data = await self._structure_recipe(web_content, progress_callback)
        
        # Add the source URL to the recipe metadata
        if recipe_data and "metadata" in recipe_data:
            recipe_data["metadata"]["sourceUrl"] = url
            logger.debug("Source URL added to recipe metadata")
            
        if progress_callback:
            await progress_callback("Processing completed")
            
        return recipe_data
    
    async def scrape_from_text(self, text: str, file_name: Optional[str] = None, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Structure a recipe from plain text.
        
        Args:
            text: The recipe text to structure
            file_name: Optional name of the text file for slug checking
            progress_callback: Optional callback for streaming progress updates
            
        Returns:
            A dictionary containing the structured recipe data
        """
        if progress_callback:
            await progress_callback("Starting recipe processing")
            
        logger.info("Processing recipe from text input")
        
        # If file_name is provided, check if a recipe with a similar slug already exists
        if file_name:
            # Extract the file name without extension
            base_name = Path(file_name).stem
            potential_slug = self._generate_slug(base_name)
            
            # Check if a recipe with this slug already exists
            slug_match = self._check_slug_exists(potential_slug)
            if slug_match:
                logger.warning(f"Recipe with similar title from file {file_name} already exists: {slug_match}")
                return {"error": "Recipe already exists", "file": slug_match, "slug": potential_slug}
        
        # Create a WebContent object with the provided text
        web_content = WebContent(
            title="Recipe from Text",
            main_content=text,
            image_urls=[]  # No images from text mode
        )
        
        # Structure the recipe
        return await self._structure_recipe(web_content, progress_callback)
    
    async def _structure_recipe(self, web_content: WebContent, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Structure the web content into a recipe and download one image.
        
        Args:
            web_content: The WebContent object containing the scraped data
            progress_callback: Optional callback for streaming progress updates
            
        Returns:
            A dictionary containing the structured recipe data
        """
        if progress_callback:
            await progress_callback("Structuring recipe data")
            
        logger.info(f"Structuring recipe: {web_content.title}")
        
        try:
            # Structure the recipe
            logger.info("Processing content through recipe structurer...")
            
            # Create a listener for recipe_structurer stream if we have a callback
            structurer_callback = None
            if progress_callback:
                async def structurer_callback(message: str):
                    await progress_callback(message)
                    logger.debug(f"Recipe structurer progress: {message}")
            
            # Structure the recipe with progress updates if available
            recipe_data = await self.recipe_structurer.structure(
                web_content,
                progress_callback=structurer_callback
            )
            
            logger.info("Recipe successfully structured")
            
            # If the recipe doesn't have a slug, generate one
            if not recipe_data.get("metadata", {}).get("slug"):
                title = recipe_data.get("metadata", {}).get("title", "recipe")
                slug = self._generate_slug(title)
                if "metadata" not in recipe_data:
                    recipe_data["metadata"] = {}
                recipe_data["metadata"]["slug"] = slug
                logger.debug(f"Generated slug for recipe: {slug}")
            
            # Get the source image URL from the metadata if available
            source_image_url = recipe_data.get("metadata", {}).get("sourceImageUrl")
            
            if source_image_url:
                if progress_callback:
                    await progress_callback("Downloading recipe image")
                    
                logger.info(f"Using source image URL from metadata: {source_image_url}")
                # Download the image
                image_filename = await self._download_image(
                    source_image_url,
                    recipe_data["metadata"]["slug"],
                    auth_values=web_content.auth_values if hasattr(web_content, 'auth_values') else None
                )
                if image_filename:
                    # Update the image path in the recipe data
                    if "metadata" in recipe_data:
                        recipe_data["metadata"]["image"] = image_filename
                        logger.debug(f"Image successfully downloaded and saved as: {image_filename}")
            else:
                logger.warning("No source image URL found in metadata")
            
            # Enrich the recipe with diet and season information
            if progress_callback:
                await progress_callback("Enriching recipe data")
                
            recipe_data = self.recipe_enricher.enrich_recipe(recipe_data)
            logger.info("Recipe enriched with diet and season information")
            
            return recipe_data
            
        except Exception as e:
            logger.error(f"Failed to structure recipe: {str(e)}")
            return {}
    
    def _generate_slug(self, title: str) -> str:
        """
        Generate a slug from a title using python-slugify.
        
        Args:
            title: The title to generate a slug from
            
        Returns:
            A URL-friendly slug
        """
        # Use python-slugify to handle accents and special characters
        slug = slugify(title)
        
        # Ensure uniqueness by adding a UUID suffix if necessary
        if not slug:
            slug = f"recipe-{uuid.uuid4().hex[:8]}"
        
        return slug
    
    async def _download_image(self, image_url: str, slug: str, auth_values: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Download an image from a URL and save it locally.
        First attempts without authentication, then with authentication if first attempt fails.
        
        Args:
            image_url: The URL of the image to download
            slug: The recipe slug to use in the filename
            auth_values: Optional authentication values for the website
            
        Returns:
            The filename of the downloaded image, or None if download failed
        """
        logger.info(f"Downloading image from: {image_url}")
        
        # First try without authentication
        try:
            logger.debug("Attempting to download image without authentication")
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                
                # Process the successful response
                return await self._process_image_response(response, image_url, slug)
                
        except httpx.HTTPStatusError as e:
            # Si erreur 403, le fichier existe mais l'accès est interdit
            if e.response.status_code == 403 and auth_values:
                logger.warning(f"Access forbidden (403) without authentication for: {image_url}")
                # Essayer avec authentification
                return await self._download_image_with_auth(image_url, slug, auth_values)
            logger.error(f"HTTP error when downloading image: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to download image: {str(e)}")
            return None
    
    async def _download_image_with_auth(self, image_url: str, slug: str, auth_values: Dict[str, Any]) -> Optional[str]:
        """
        Download an image with authentication.
        
        Args:
            image_url: The URL of the image to download
            slug: The recipe slug to use in the filename
            auth_values: Authentication values for the website
            
        Returns:
            The filename of the downloaded image, or None if download failed
        """
        try:
            logger.info(f"Attempting to download image with authentication from: {image_url}")
            
            # Create cookies if authentication type is cookie
            cookies = {}
            if auth_values.get("type") == "cookie" and auth_values.get("values"):
                cookies = auth_values.get("values", {})
            
            # Download the image with cookies
            async with httpx.AsyncClient(follow_redirects=True, cookies=cookies) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return await self._process_image_response(response, image_url, slug)
                
        except Exception as e:
            logger.error(f"Failed to download image with authentication: {str(e)}")
            return None
    
    async def _process_image_response(self, response: httpx.Response, image_url: str, slug: str) -> Optional[str]:
        """
        Process an image response and save the image to disk.
        
        Args:
            response: The HTTP response containing the image
            image_url: The URL of the image (for extension fallback)
            slug: The recipe slug to use in the filename
            
        Returns:
            The filename of the downloaded image, or None if processing failed
        """
        try:
            # Determine the content type from the headers
            content_type = response.headers.get("content-type", "").lower()
            
            # Determine the extension based on content-type
            if content_type.startswith("image/"):
                mime_ext = content_type.split("/")[1].split(";")[0]  # Extract extension from MIME type
                if mime_ext in ["jpeg", "jpg", "png", "gif", "webp", "svg+xml", "svg"]:
                    ext = mime_ext if mime_ext != "jpeg" else "jpg"
                    # Handle SVG content type
                    if mime_ext in ["svg+xml", "svg"]:
                        ext = "svg"
                else:
                    ext = "jpg"  # Default to jpg
            else:
                # Fallback to URL extension if content-type is not helpful
                ext = image_url.split(".")[-1].lower()
                if ext not in ["jpg", "jpeg", "png", "webp", "gif", "svg"]:
                    ext = "jpg"  # Default to jpg if extension is not recognized
                if ext == "jpeg":
                    ext = "jpg"  # Normalize jpeg to jpg
            
            logger.debug(f"Image content type: {content_type}, using extension: {ext}")
            
            # Create a filename
            image_filename = f"{slug}.{ext}"
            
            # Create the output directory if it doesn't exist
            output_dir = self._image_output_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the image to disk
            image_path = output_dir / image_filename
            with open(image_path, "wb") as f:
                f.write(response.content)
            
            # Verify file size to ensure it was downloaded correctly
            file_size = image_path.stat().st_size
            if file_size < 100:  # If file is too small, it's probably corrupted
                logger.error(f"Downloaded image is too small ({file_size} bytes), possibly corrupted")
                return None
            
            logger.info(f"Image successfully downloaded to {image_path} ({file_size} bytes)")
            return f"images/{image_filename}"
        
        except Exception as e:
            logger.error(f"Failed to process image response: {str(e)}")
            return None 