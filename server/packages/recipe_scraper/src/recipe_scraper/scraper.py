"""
RecipeScraper package combines web_scraper and recipe_structurer to extract and structure recipes.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple
import uuid
from dotenv import load_dotenv
from datetime import datetime
import base64
import difflib  # Added for text similarity comparison

# Load environment variables
load_dotenv()

import httpx
from pydantic import BaseModel, ValidationError
from slugify import slugify

from web_scraper import WebScraper
from web_scraper.models import WebContent, AuthPreset
from recipe_structurer import RecipeStructurer
from .recipe_enricher import RecipeEnricher
from .services.recipe_reviewer import RecipeReviewer
from .observability import observe, langfuse_context

logger = logging.getLogger(__name__)

class RecipeScraper:
    """
    A class that combines web scraping and recipe structuring to extract and save recipes.
    """
    
    def __init__(self):
        """Initialize the RecipeScraper with web_scraper and recipe_structurer."""
        self.web_scraper = WebScraper()
        self.recipe_structurer = RecipeStructurer()
        self.recipe_enricher = RecipeEnricher()  # Initialize the recipe enricher
        self.recipe_reviewer = RecipeReviewer()  # Pass 3: adversarial reviewer
        self._recipe_output_folder = Path("./data/recipes")  # Default recipe output folder
        self._image_output_folder = Path("./data/recipes/images")  # Default image output folder
        self._debug_output_folder = Path("./data/recipes/debug")  # Debug traces folder
    
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
        
    @observe(name="scrape_from_url")
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
        langfuse_context.update_current_trace(
            metadata={"source_url": url},
        )
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
        try:
            async with self.web_scraper as scraper:
                web_content = await scraper.scrape_url(url, auth_preset)
        except Exception as exc:
            import traceback as _tb
            logger.error(f"Web scraping failed for {url}: {exc}")
            self._save_error_trace(
                url=url, title="(scraping failed)",
                error=exc, traceback_str=_tb.format_exc(),
                stage="scraping", raw_text=None,
            )
            langfuse_context.update_current_trace(
                name="FAILED:scraping",
                metadata={"error": True, "error_stage": "scraping", "error_message": str(exc)},
            )
            return {}
            
        if not web_content:
            logger.error("Failed to scrape web content: No content retrieved from URL")
            self._save_error_trace(
                url=url, title="(scraping failed)", 
                error=RuntimeError("No content retrieved from URL"),
                traceback_str="", stage="scraping", raw_text=None,
            )
            langfuse_context.update_current_trace(
                name=f"FAILED:scraping",
                metadata={"error": True, "error_stage": "scraping", "error_message": "No content retrieved"},
            )
            return {}
        
        logger.debug(f"Web content successfully retrieved. Title: \"{web_content.title}\"")
        
        # Créer un dictionnaire de métadonnées avec l'URL source
        metadata = {"sourceUrl": url}
        
        # Structure the recipe
        recipe_data = await self._structure_recipe(web_content, progress_callback, metadata=metadata)
        
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
        
        # Check for similar recipes using text similarity
        similar_recipe_path, similarity = self._find_similar_recipe(text.strip())
        if similar_recipe_path and similarity >= 0.85:  # 85% similarity threshold
            logger.warning(f"Recipe with similar content (similarity: {similarity:.2%}) already exists: {similar_recipe_path}")
            # Return None to match behavior of scrape_from_url when a duplicate is found
            return None
        
        # If file_name is provided, check if a recipe with a similar slug already exists
        if file_name:
            # Extract the file name without extension
            base_name = Path(file_name).stem
            potential_slug = self._generate_slug(base_name)
            
            # Check if a recipe with this slug already exists
            slug_match = self._check_slug_exists(potential_slug)
            if slug_match:
                logger.warning(f"Recipe with similar title from file {file_name} already exists: {slug_match}")
                return None
        
        # Create a WebContent object with the provided text
        web_content = WebContent(
            title="Recipe from Text",
            main_content=text,
            image_urls=[]  # No images from text mode
        )
        
        # Créer un dictionnaire de métadonnées avec le texte original
        metadata = {
            "originalContent": text  # Store the original text for similarity comparison
        }
        
        # Structure the recipe
        recipe_data = await self._structure_recipe(web_content, progress_callback, metadata=metadata)
        
        return recipe_data
    
    def _find_similar_recipe(self, text: str) -> Tuple[Optional[str], float]:
        """
        Find the most similar recipe based on text content.
        
        Args:
            text: The recipe text to compare
            
        Returns:
            A tuple containing the path to the most similar recipe and its similarity score (0-1)
        """
        if not self._recipe_output_folder.exists():
            logger.warning(f"Recipe output folder does not exist: {self._recipe_output_folder}")
            return None, 0.0
        
        logger.info(f"Checking for similar recipes in {self._recipe_output_folder}")
        
        # Look for recipe files in the output folder
        recipe_files = list(self._recipe_output_folder.glob("*.recipe.json"))
        
        # If there are no recipe files, return None
        if not recipe_files:
            logger.warning(f"No recipe files found in {self._recipe_output_folder}")
            return None, 0.0
        
        logger.info(f"Found {len(recipe_files)} recipe files to check for similarity")
        
        # Track the most similar recipe and its score
        most_similar_recipe = None
        highest_similarity = 0.0
        
        # Check each recipe file for originalContent to compare
        for recipe_file in recipe_files:
            try:
                with open(recipe_file, "r") as f:
                    recipe_data = json.load(f)
                    
                # Get the original content for comparison
                original_content = recipe_data.get("metadata", {}).get("originalContent")
                if not original_content:
                    logger.debug(f"Recipe {recipe_file.name} has no original content to compare")
                    continue
                    
                # Compare the text with the original content
                similarity = self._calculate_similarity(text, original_content)
                logger.debug(f"Recipe {recipe_file.name} similarity: {similarity:.2%}")
                
                # Update if this is the most similar recipe so far
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    most_similar_recipe = str(recipe_file)
                    
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Error reading {recipe_file}: {str(e)}")
                continue
        
        if highest_similarity > 0:
            logger.info(f"Most similar recipe found: {most_similar_recipe} with similarity {highest_similarity:.2%}")
        else:
            logger.info("No similar recipes found")
            
        return most_similar_recipe, highest_similarity
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate the similarity between two texts.
        
        Args:
            text1: First text to compare
            text2: Second text to compare
            
        Returns:
            A similarity score between 0 and 1
        """
        # Normalize texts by removing extra spaces and converting to lowercase
        text1 = " ".join(text1.lower().split())
        text2 = " ".join(text2.lower().split())
        
        # Use difflib's SequenceMatcher to calculate similarity
        matcher = difflib.SequenceMatcher(None, text1, text2)
        similarity = matcher.ratio()
        
        return similarity
    
    @observe(name="structure_recipe")
    async def _structure_recipe(self, web_content: WebContent, progress_callback: Optional[Callable[[str], None]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Structure the web content into a recipe and download one image.
        Uses DeepSeek V3.2.
        
        Args:
            web_content: The WebContent object containing the scraped data
            progress_callback: Optional callback for streaming progress updates
            metadata: Optional metadata to add to the recipe
            
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
            
            recipe_obj = await self.recipe_structurer.structure(
                web_content,
                progress_callback=structurer_callback
            )
            
            # Convert to dictionary
            recipe_data = self.recipe_structurer.to_dict(recipe_obj)
            
            logger.info("Recipe successfully structured")
            
            # Generate slug from title
            title = recipe_data.get("metadata", {}).get("title", "recipe")
            slug = self._generate_slug(title)
            recipe_data["metadata"]["slug"] = slug
            logger.debug(f"Generated slug for recipe: {slug}")
            
            # Save debug traces (raw scraped text + preformatted text)
            self._save_debug_traces(
                slug=slug,
                raw_text=web_content.main_content,
                preformatted_text=recipe_data.pop("preformattedText", None),
                source_url=metadata.get("sourceUrl") if metadata else None,
            )
            # Keep originalText in the saved recipe for UI display
            # (also saved in debug traces as raw text)
            
            # Map imageUrl to sourceImageUrl for compatibility
            if recipe_data["metadata"].get("imageUrl"):
                recipe_data["metadata"]["sourceImageUrl"] = recipe_data["metadata"]["imageUrl"]
            
            # Add any provided metadata (sourceUrl, originalContent, etc.)
            if metadata:
                recipe_data["metadata"].update(metadata)
                logger.debug(f"Added custom metadata: {metadata}")

            # Pass schema.org structured data to enricher (for time cross-check)
            if hasattr(web_content, "structured_data") and web_content.structured_data:
                recipe_data["metadata"]["_schema_data"] = web_content.structured_data
            
            # Get the source image URL from the metadata if available
            source_image_url = recipe_data.get("metadata", {}).get("sourceImageUrl")
            
            if source_image_url:
                if progress_callback:
                    await progress_callback("Downloading recipe image")
                    
                logger.info(f"Using source image URL from metadata: {source_image_url}")
                # Download the image
                image_filename = await self._download_image(
                    source_image_url,
                    slug,
                    auth_values=web_content.auth_values if hasattr(web_content, 'auth_values') else None
                )
                if image_filename:
                    recipe_data["metadata"]["image"] = image_filename
                    logger.debug(f"Image successfully downloaded and saved as: {image_filename}")
            else:
                logger.warning("No source image URL found in metadata")
            
            # Enrich the recipe with diet, season, and nutrition information
            if progress_callback:
                await progress_callback("Enriching recipe data (diet, season, nutrition)")
                
            recipe_data = await self.recipe_enricher.enrich_recipe_async(recipe_data)
            logger.info("Recipe enriched with diet, season, and nutrition information")

            # Remove internal schema data (not needed in saved JSON)
            recipe_data.get("metadata", {}).pop("_schema_data", None)
            
            # ── Pass 3: Adversarial review ────────────────────────────
            if self.recipe_reviewer.is_available and web_content.main_content:
                if progress_callback:
                    await progress_callback("Reviewing recipe quality (Pass 3)...")
                
                try:
                    source_url = recipe_data.get("metadata", {}).get("sourceUrl")
                    review = await self.recipe_reviewer.review(
                        recipe_data=recipe_data,
                        source_text=web_content.main_content,
                        source_url=source_url,
                    )
                    if review:
                        # Store summary in recipe metadata (lightweight)
                        recipe_data["metadata"]["reviewScore"] = review.overall_score
                        # Save full review as debug trace
                        self._save_review_trace(slug, review.model_dump(), source_url)
                        logger.info(
                            f"[Pass 3] Score: {review.overall_score}/10 — "
                            f"{len(review.ingredient_corrections)} ing corrections, "
                            f"{len(review.step_corrections)} step corrections, "
                            f"{len(review.culinary_issues)} culinary issues"
                        )
                        # Auto-apply corrections from the review
                        recipe_data = self.recipe_reviewer.apply_corrections(
                            recipe_data, review
                        )
                except Exception as e:
                    logger.warning(f"[Pass 3] Review failed (non-blocking): {e}")

            # ── Attach Langfuse metadata & scores ─────────────────────
            title = recipe_data.get("metadata", {}).get("title", "?")
            langfuse_context.update_current_trace(
                name=f"import:{title[:60]}",
                metadata={
                    "recipe_title": title,
                    "slug": slug,
                    "ingredients_count": len(recipe_data.get("ingredients", [])),
                    "steps_count": len(recipe_data.get("steps", [])),
                    "total_time_min": recipe_data.get("metadata", {}).get("totalTimeMinutes", 0),
                },
            )
            review_score = recipe_data.get("metadata", {}).get("reviewScore")
            if review_score is not None:
                langfuse_context.score_current_trace(
                    name="review_score", value=float(review_score),
                )

            return recipe_data
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Failed to structure recipe: {str(e)}")
            logger.error(tb)

            # ── Save error trace for debugging ────────────────────────
            error_stage = self._classify_error(e, tb)
            self._save_error_trace(
                url=metadata.get("sourceUrl", "unknown") if metadata else "unknown",
                title=web_content.title if web_content else "unknown",
                error=e,
                traceback_str=tb,
                stage=error_stage,
                raw_text=web_content.main_content if web_content else None,
            )

            # ── Tag Langfuse trace with error info ────────────────────
            langfuse_context.update_current_trace(
                name=f"FAILED:{web_content.title[:40] if web_content else 'unknown'}",
                metadata={
                    "error": True,
                    "error_stage": error_stage,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:500],
                },
            )

            return {}
    
    def _save_debug_traces(
        self,
        slug: str,
        raw_text: str,
        preformatted_text: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> None:
        """
        Save intermediate pipeline data for debugging and quality improvement.
        
        Creates debug files alongside recipes:
        - {slug}.raw.txt: Raw scraped content from the web page
        - {slug}.preformat.txt: Output of Pass 1 (preformat LLM call)
        
        Args:
            slug: Recipe slug for file naming
            raw_text: Raw text from the web scraper
            preformatted_text: Output of Pass 1 (preformat), if available
            source_url: Source URL for reference header
        """
        try:
            self._debug_output_folder.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().isoformat()
            header = f"# Debug trace — {timestamp}\n"
            if source_url:
                header += f"# Source: {source_url}\n"
            header += f"# Slug: {slug}\n"
            header += "# " + "=" * 60 + "\n\n"
            
            # Save raw scraped text
            raw_path = self._debug_output_folder / f"{slug}.raw.txt"
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(raw_text)
            logger.info(f"Debug trace saved: {raw_path} ({len(raw_text)} chars)")
            
            # Save preformatted text (Pass 1 output)
            if preformatted_text:
                preformat_path = self._debug_output_folder / f"{slug}.preformat.txt"
                with open(preformat_path, "w", encoding="utf-8") as f:
                    f.write(header)
                    f.write(preformatted_text)
                logger.info(f"Debug trace saved: {preformat_path} ({len(preformatted_text)} chars)")
                
        except Exception as e:
            # Debug traces are non-critical — never fail the pipeline
            logger.warning(f"Failed to save debug traces for '{slug}': {e}")

    def _save_review_trace(
        self,
        slug: str,
        review_data: dict,
        source_url: Optional[str] = None,
    ) -> None:
        """
        Save the Pass 3 adversarial review as a debug trace file.
        
        Creates: {slug}.review.json in the debug output folder.
        """
        try:
            self._debug_output_folder.mkdir(parents=True, exist_ok=True)
            review_path = self._debug_output_folder / f"{slug}.review.json"
            with open(review_path, "w", encoding="utf-8") as f:
                json.dump(review_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Review trace saved: {review_path}")
        except Exception as e:
            logger.warning(f"Failed to save review trace for '{slug}': {e}")

    @staticmethod
    def _classify_error(error: Exception, traceback_str: str) -> str:
        """Classify an error into a pipeline stage for easier triage."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        tb_lower = traceback_str.lower()

        # Pydantic / schema validation
        if "ValidationError" in error_type or "validation" in error_msg:
            return "pass2_validation"

        # LLM API errors
        if any(kw in error_msg for kw in ("rate limit", "429", "quota", "insufficient")):
            return "llm_rate_limit"
        if any(kw in error_msg for kw in ("timeout", "timed out", "connect")):
            return "llm_timeout"
        if any(kw in error_msg for kw in ("api", "openai", "openrouter", "500", "502", "503")):
            return "llm_api_error"

        # Recipe rejection
        if "rejected" in error_msg or "not_a_recipe" in error_msg:
            return "recipe_rejected"

        # Preformat pass
        if "preformat" in tb_lower:
            return "pass1_preformat"

        # DAG construction
        if "pass 2" in tb_lower or "dag" in tb_lower or "instructor" in tb_lower:
            return "pass2_dag"

        # Enrichment
        if "enrich" in tb_lower or "nutrition" in tb_lower:
            return "enrichment"

        # Web scraping
        if "scrape" in tb_lower or "httpx" in tb_lower or "web_scraper" in tb_lower:
            return "scraping"

        return "unknown"

    def _save_error_trace(
        self,
        url: str,
        title: str,
        error: Exception,
        traceback_str: str,
        stage: str,
        raw_text: Optional[str] = None,
    ) -> None:
        """
        Save a structured error trace for failed imports.

        Creates: errors/{timestamp}_{slug}.error.json in the debug folder.
        """
        try:
            errors_dir = self._debug_output_folder / "errors"
            errors_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_slug = slugify(title)[:60] if title else "unknown"
            filename = f"{timestamp}_{safe_slug}.error.json"

            error_data = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "title": title,
                "stage": stage,
                "error_type": type(error).__name__,
                "error_message": str(error)[:2000],
                "traceback": traceback_str[-3000:],  # Last 3000 chars of traceback
            }

            # Include raw text preview if available (for debugging prompts)
            if raw_text:
                error_data["raw_text_preview"] = raw_text[:1000]
                error_data["raw_text_length"] = len(raw_text)

            error_path = errors_dir / filename
            with open(error_path, "w", encoding="utf-8") as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Error trace saved: {error_path} (stage={stage})")
        except Exception as save_err:
            logger.warning(f"Failed to save error trace: {save_err}")

    def _generate_slug(self, title: str) -> str:
        """Generate a unique slug from a title.

        If a recipe file with the same slug already exists on disk,
        a numeric suffix (-2, -3, ...) is appended to avoid silent
        overwrites.
        """
        base = slugify(title) if title else ""
        if not base:
            base = f"recipe-{uuid.uuid4().hex[:8]}"

        candidate = base
        counter = 2
        while (self._recipe_output_folder / f"{candidate}.recipe.json").exists():
            candidate = f"{base}-{counter}"
            counter += 1

        return candidate
    
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
        
        # Si c'est une data URL, on la traite directement
        if image_url.startswith("data:"):
            try:
                # Extraire le type MIME et les données
                header, encoded = image_url.split(",", 1)
                mime_type = header.split(":")[1].split(";")[0]
                
                # Déterminer l'extension
                if mime_type == "image/svg+xml":
                    ext = "svg"
                else:
                    ext = mime_type.split("/")[1]
                    if ext == "jpeg":
                        ext = "jpg"
                
                # Créer le nom du fichier
                image_filename = f"{slug}.{ext}"
                
                # Créer le dossier de sortie s'il n'existe pas
                output_dir = self._image_output_folder
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Sauvegarder l'image
                image_path = output_dir / image_filename
                with open(image_path, "wb") as f:
                    f.write(base64.b64decode(encoded))
                
                logger.info(f"Data URL image successfully saved to {image_path}")
                return f"images/{image_filename}"
                
            except Exception as e:
                logger.error(f"Failed to process data URL image: {str(e)}")
                return None
        
        # Pour les URLs normales, on continue avec le code existant
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