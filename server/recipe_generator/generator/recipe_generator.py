from typing import Optional, Dict, Any, Callable, Protocol, Union
from ..models.web_content import WebContent
from ..models.text_content import TextContent
from ..models.recipe import Recipe
from ..services.web_scraper import WebScraper
from ..services.content_cleaner import ContentCleaner
from ..services.recipe_structurer import RecipeStructurer
from ..utils.string_utils import generate_slug
from ..llm.factory import create_provider
from ..config import load_config
import asyncio
from dataclasses import dataclass
from enum import Enum
import aiohttp
import aiofiles
from pathlib import Path
import uuid
from PIL import Image
import io
import json

class ProgressUpdater(Protocol):
    async def update_step(
        self,
        progress_id: str,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        ...

    async def get_progress(self, progress_id: str) -> Optional[Dict[str, Any]]:
        ...

    async def set_error(self, progress_id: str, error: str) -> None:
        ...

@dataclass
class GenerationContext:
    url: Optional[str] = None
    text: Optional[str] = None
    image_data: Optional[bytes] = None
    credentials: Optional[Dict[str, Any]] = None
    progress_service: Optional[ProgressUpdater] = None
    progress_id: Optional[str] = None

class RecipeGenerator:
    """Main service for generating recipes from URLs or text."""
    
    def __init__(self, base_path: str, images_path: str, recipes_path: str):
        """Initialize the recipe generator with its dependencies."""
        # Load configuration
        self.config = load_config()
        
        # Create LLM provider
        self.provider = create_provider(
            provider_type=self.config["provider"],
            api_key=self.config[f"{self.config['provider']}_api_key"],
            task="cleanup"
        )
        
        # Initialize services
        self.web_scraper = WebScraper()
        self.content_cleaner = ContentCleaner(self.provider)
        self.recipe_structurer = RecipeStructurer(self.provider)
        
        # Set paths
        self.base_path = Path(base_path)
        self.images_path = Path(images_path)
        self.recipes_path = Path(recipes_path)

    async def _update_progress(
        self,
        ctx: GenerationContext,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """Helper to update progress if a progress service is available."""
        if ctx.progress_service and ctx.progress_id:
            await ctx.progress_service.update_step(
                progress_id=ctx.progress_id,
                step=step,
                status=status,
                progress=progress,
                message=message,
                details=details
            )

    async def _fetch_url_content(self, ctx: GenerationContext) -> WebContent:
        """Fetch content from URL."""
        try:
            # Fetch URL content silently (no progress update)
            web_content = await self.web_scraper.scrape_url(
                ctx.url,
                ctx.credentials
            )
            
            return web_content
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch URL content: {str(e)}")
            raise

    async def _clean_content(self, ctx: GenerationContext, content: Union[WebContent, str]) -> Union[WebContent, TextContent]:
        """Clean and structure the content."""
        try:
            # Update progress for cleanup
            await self._update_progress(
                ctx,
                step="cleanup_content",
                status="in_progress",
                progress=0,
                message="Cleaning up content..."
            )
            
            # Clean content with streaming updates
            total_chunks = 0
            async def update_cleaning_progress(content: str):
                nonlocal total_chunks
                total_chunks += 1
                # Calculate progress between 0 and 90%
                progress = min(90, int((total_chunks / 50) * 100))  # Assuming ~50 chunks on average
                await self._update_progress(
                    ctx,
                    step="cleanup_content",
                    status="in_progress",
                    progress=progress,
                    details=content
                )
            
            # Choose cleaning method based on content type
            if isinstance(content, WebContent):
                cleaned_content = await self.content_cleaner.clean_content(
                    content,
                    on_progress=update_cleaning_progress
                )
            else:
                cleaned_content = await self.content_cleaner.clean_text_content(
                    content,
                    on_progress=update_cleaning_progress
                )
            
            await self._update_progress(
                ctx,
                step="cleanup_content",
                status="completed",
                progress=100,
                message="Content cleaned successfully"
            )
            
            return cleaned_content
            
        except Exception as e:
            print(f"[ERROR] Failed to clean content: {str(e)}")
            raise

    async def _structure_recipe(
        self,
        ctx: GenerationContext,
        content: Union[WebContent, TextContent]
    ) -> Dict[str, Any]:
        """Structure the content into a recipe format."""
        print("[DEBUG] Starting recipe structuring...")
        
        await self._update_progress(
            ctx,
            step="generate_recipe",
            status="in_progress",
            progress=0,
            message="Starting recipe generation..."
        )

        try:
            # In text mode, we don't pass any image URLs as images are handled separately
            image_urls = []
            if isinstance(content, WebContent):
                image_urls = [content.selected_image_url] if content.selected_image_url else []

            # Generate structured recipe
            recipe = await self.recipe_structurer.generate_structured_recipe(
                content=content,
                source_url=ctx.url,
                image_urls=image_urls,
                progress_service=ctx.progress_service,
                progress_id=ctx.progress_id
            )
            
            print("[DEBUG] Recipe structured successfully")
            print(f"[DEBUG] Generated recipe title: {recipe.get('metadata', {}).get('title')}")
            
            await self._update_progress(
                ctx,
                step="generate_recipe",
                status="completed",
                progress=100,
                message="Recipe generated successfully"
            )
            
            return recipe
            
        except Exception as e:
            print(f"[ERROR] Failed to structure recipe: {str(e)}")
            await self._update_progress(
                ctx,
                step="generate_recipe",
                status="error",
                progress=0,
                message=f"Failed to structure recipe: {str(e)}"
            )
            raise

    async def _save_recipe(self, ctx: GenerationContext, recipe: Dict[str, Any]) -> None:
        """Save recipe and download associated image."""
        try:
            # Update progress for saving
            await self._update_progress(
                ctx,
                step="save_recipe",
                status="in_progress",
                progress=0,
                message="Saving recipe..."
            )

            # Save recipe
            await self.save_recipe(recipe)
            
            # Download and save image silently if URL is present AND we're in URL mode
            if ctx.url and recipe.get("metadata", {}).get("sourceImageUrl"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(recipe["metadata"]["sourceImageUrl"]) as response:
                            if response.status == 200:
                                image_data = await response.read()
                                image_path = await self.save_image(image_data, recipe["metadata"]["slug"])
                                recipe["metadata"]["imageUrl"] = image_path
                                
                                # Save recipe again with updated image URL
                                await self.save_recipe(recipe)
                            else:
                                print(f"[ERROR] Failed to download image: {response.status}")
                except Exception as e:
                    print(f"[ERROR] Failed to download image: {str(e)}")
                    # Continue execution even if image download fails

            # Mark save step as completed
            await self._update_progress(
                ctx,
                step="save_recipe",
                status="completed",
                progress=100,
                message="Recipe saved successfully"
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to save recipe: {str(e)}")
            await self._update_progress(
                ctx,
                step="save_recipe",
                status="error",
                message=f"Failed to save recipe: {str(e)}"
            )
            raise

    async def generate_from_url(
        self,
        url: str,
        credentials: Optional[Dict[str, Any]] = None,
        progress_service: Optional[ProgressUpdater] = None,
        progress_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a recipe from a URL with progress tracking."""
        ctx = GenerationContext(
            url=url,
            credentials=credentials,
            progress_service=progress_service,
            progress_id=progress_id
        )
        
        try:
            # Fetch URL content
            print("[DEBUG] Fetching URL content...")
            web_content = await self._fetch_url_content(ctx)
            print(f"[DEBUG] web_content type: {type(web_content)}")
            print(f"[DEBUG] web_content attributes: {dir(web_content)}")
            
            # Clean and structure content
            print("[DEBUG] Cleaning content...")
            cleaned_content = await self._clean_content(ctx, web_content)
            print(f"[DEBUG] cleaned_content type: {type(cleaned_content)}")
            print(f"[DEBUG] cleaned_content attributes: {dir(cleaned_content)}")
            
            # Generate structured recipe
            print("[DEBUG] Structuring recipe...")
            recipe = await self._structure_recipe(ctx, cleaned_content)
            print(f"[DEBUG] recipe type: {type(recipe)}")
            
            # Generate slug from title
            if recipe.get("metadata", {}).get("title"):
                recipe["metadata"]["slug"] = generate_slug(recipe["metadata"]["title"])
            
            # Save recipe
            await self._save_recipe(ctx, recipe)
            
            return recipe
            
        except Exception as e:
            # Log error and update progress
            error_msg = f"Error generating recipe: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
            
            # Get current step from progress service
            current_step = None
            if ctx.progress_service and ctx.progress_id:
                progress = await ctx.progress_service.get_progress(ctx.progress_id)
                if progress:
                    current_step = progress.current_step
            
            # Update current step to error state
            if current_step:
                await self._update_progress(
                    ctx,
                    step=current_step,
                    status="error",
                    progress=0,
                    message=error_msg
                )
            
            raise

    async def process_text(self, text: str) -> str:
        """Process raw text input into a format suitable for recipe generation."""
        # For now, just return the text as is
        # Later we can add text cleaning if needed
        return text

    async def save_image(self, image_data: bytes, slug: str) -> str:
        """Save an image and create different sizes."""
        try:
            # Open and verify the image
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verify it's a valid image
            
            # Check if it's an SVG (based on the first few bytes)
            is_svg = image_data[:5].lower() == b'<?xml' or image_data[:4].lower() == b'<svg'
            
            if is_svg:
                # For SVG, save directly without processing
                original_filename = f"{slug}.svg"
                original_path = self.images_path / "original" / original_filename
                original_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiofiles.open(original_path, 'wb') as f:
                    await f.write(image_data)
                
                return f"recipes/images/original/{original_filename}"
            
            # For bitmap images, process and convert to WebP
            # Reopen the image after verify (verify closes the file)
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            
            # Save original image in WebP format
            original_filename = f"{slug}.webp"
            original_path = self.images_path / "original" / original_filename
            original_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to WebP and save with high quality
            image.save(str(original_path), "WEBP", quality=95, method=6)
            
            # Create different sizes
            sizes = {
                "thumbnail": (150, 150),
                "small": (300, 300),
                "medium": (600, 600),
                "large": (1200, 1200)
            }
            
            for size_name, dimensions in sizes.items():
                size_path = self.images_path / size_name / original_filename
                size_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Calculate dimensions preserving aspect ratio
                img_ratio = image.width / image.height
                target_ratio = dimensions[0] / dimensions[1]
                
                if img_ratio > target_ratio:
                    new_width = dimensions[0]
                    new_height = int(new_width / img_ratio)
                else:
                    new_height = dimensions[1]
                    new_width = int(new_height * img_ratio)
                
                # Resize with high quality
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                resized_image.save(str(size_path), "WEBP", quality=90, method=6)
            
            # Return the relative path for the recipe JSON
            return f"recipes/images/original/{original_filename}"
            
        except Exception as e:
            raise ValueError(f"Failed to process image: {str(e)}")

    async def generate_recipe(self, content: str) -> Dict[str, Any]:
        """Generate a structured recipe from content."""
        try:
            # Use the recipe structurer to generate the recipe
            recipe_json = await self.recipe_structurer.structure_recipe(content)
            
            # Generate a slug if not present
            if not recipe_json.get("metadata", {}).get("slug"):
                title = recipe_json.get("metadata", {}).get("title", "")
                recipe_json["metadata"]["slug"] = generate_slug(title)
            
            return recipe_json
            
        except Exception as e:
            raise ValueError(f"Failed to generate recipe: {str(e)}")

    async def save_recipe(self, recipe: Dict[str, Any]) -> None:
        """Save a recipe to disk."""
        try:
            slug = recipe.get("metadata", {}).get("slug")
            if not slug:
                raise ValueError("Recipe has no slug")
            
            file_path = self.recipes_path / f"{slug}.recipe.json"
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(recipe, indent=2))
                
        except Exception as e:
            raise ValueError(f"Failed to save recipe: {str(e)}")

    async def generate_from_text(
        self,
        text: str,
        image_data: Optional[bytes] = None,
        progress_service: Optional[ProgressUpdater] = None,
        progress_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a recipe from text content with optional image."""
        print("[DEBUG] Starting generate_from_text")
        ctx = GenerationContext(text=text, image_data=image_data, progress_service=progress_service, progress_id=progress_id)
        
        try:
            # Clean up content - no image handling in cleanup for text mode
            print("[DEBUG] Cleaning up content...")
            cleaned_content = await self._clean_content(ctx, text)
            print(f"[DEBUG] Content cleaned successfully")
            
            # Generate structured recipe
            print("[DEBUG] Generating structured recipe...")
            recipe = await self._structure_recipe(ctx, cleaned_content)
            print("[DEBUG] Recipe structured successfully")
            
            # Generate slug from title
            print("[DEBUG] Generating slug...")
            if recipe.get("metadata", {}).get("title"):
                recipe["metadata"]["slug"] = generate_slug(recipe["metadata"]["title"])
                print(f"[DEBUG] Generated slug: {recipe['metadata']['slug']}")
            
            # Ensure sourceImageUrl is empty in text mode
            if "metadata" not in recipe:
                recipe["metadata"] = {}
            recipe["metadata"]["sourceImageUrl"] = ""
            
            # Handle image separately for text mode - direct save of provided image
            if image_data:
                print("[DEBUG] Processing provided image...")
                try:
                    # In text mode, we directly save the provided image without any web fetching
                    image_path = await self.save_image(image_data, recipe["metadata"]["slug"])
                    recipe["metadata"]["imageUrl"] = image_path
                    print(f"[DEBUG] Image saved at: {image_path}")
                except Exception as e:
                    print(f"[ERROR] Failed to process image: {str(e)}")
                    raise
            
            # Save recipe
            print("[DEBUG] Saving recipe...")
            await self._save_recipe(ctx, recipe)
            print("[DEBUG] Recipe saved successfully")
            
            return recipe
            
        except Exception as e:
            print(f"[ERROR] Failed to generate recipe from text: {str(e)}")
            raise