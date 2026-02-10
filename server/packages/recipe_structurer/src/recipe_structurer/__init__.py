"""
Recipe Structurer Package
=========================

Converts raw recipe text into structured data using LLMs.

Two versions are available:

V2 (Recommended):
    - Uses Instructor + DeepSeek V3.2
    - 2-pass pipeline: preformat (text cleanup) → DAG construction (JSON graph)
    - Automatic validation and retries via Instructor
    - Simplified graph-based format
    
    Usage:
        from recipe_structurer import RecipeStructurerV2
        
        structurer = RecipeStructurerV2()
        recipe = await structurer.structure(content)

V1 (Legacy):
    - Uses custom providers (DeepSeek, Mistral, HuggingFace)
    - 3 separate LLM calls (cleanup, metadata, graph)
    - Original format
    
    Usage:
        from recipe_structurer import RecipeStructurer
        
        structurer = RecipeStructurer(provider="deepseek")
        recipe = await structurer.structure(content)
"""

import logging
from typing import Optional, Callable, Awaitable

from .exceptions import RecipeRejectedError

logger = logging.getLogger(__name__)


# =============================================================================
# V2 API (Recommended) - Instructor + DeepSeek V3.2
# =============================================================================

from .generator_v2 import RecipeGeneratorV2, generate_recipe_v2
from .models.recipe_v2 import RecipeV2, MetadataV2, IngredientV2, StepV2


class RecipeStructurerV2:
    """
    V2 Recipe Structurer using Instructor + DeepSeek V3.2.
    
    This is the recommended way to structure recipes in 2025+.
    Uses a 2-pass pipeline (preformat → DAG) with automatic Pydantic validation.
    
    Example:
        structurer = RecipeStructurerV2()
        recipe = await structurer.structure(content)
        
        # Access structured data
        print(recipe.metadata.title)
        print(recipe.ingredients)
        print(recipe.steps)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the V2 structurer.
        
        Args:
            api_key: DeepSeek API key. Defaults to DEEPSEEK_API_KEY env var.
        """
        self._generator = RecipeGeneratorV2(api_key=api_key)
    
    async def structure(
        self,
        content,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> RecipeV2:
        """
        Structure recipe content into V2 format.
        
        Args:
            content: Content object with main_content and image_urls attributes
            progress_callback: Optional async callback for progress updates
            
        Returns:
            RecipeV2: Validated and structured recipe
        """
        logger.info("Structuring recipe with V2 pipeline")
        
        recipe = await self._generator.generate(
            recipe_text=content.main_content,
            image_urls=getattr(content, 'image_urls', None),
            progress_callback=progress_callback
        )
        
        logger.info(f"V2 recipe structured: {recipe.metadata.title}")
        return recipe
    
    async def structure_from_text(
        self,
        text: str,
        image_urls: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> RecipeV2:
        """
        Structure recipe from raw text.
        
        Args:
            text: Raw recipe text
            image_urls: Optional list of image URLs
            progress_callback: Optional async callback for progress updates
            
        Returns:
            RecipeV2: Validated and structured recipe
        """
        logger.info("Structuring recipe from text with V2 pipeline")
        
        recipe = await self._generator.generate(
            recipe_text=text,
            image_urls=image_urls,
            progress_callback=progress_callback
        )
        
        logger.info(f"V2 recipe structured from text: {recipe.metadata.title}")
        return recipe
    
    def to_dict(self, recipe: RecipeV2) -> dict:
        """Convert RecipeV2 to dictionary format."""
        return recipe.model_dump()


# =============================================================================
# V1 API (Legacy) - Multi-provider, 3-step pipeline
# =============================================================================

from .generator import generate_recipe
from .constants import DEFAULT_MODEL


class RecipeStructurer:
    """
    V1 Recipe Structurer (Legacy).
    
    Uses the original 3-step pipeline with multiple provider support.
    Kept for backwards compatibility.
    
    For new projects, use RecipeStructurerV2 instead.
    """
    
    def __init__(self, provider: str = DEFAULT_MODEL):
        """Initialize with specified provider."""
        self.provider = provider
        logger.warning(
            "RecipeStructurer V1 is deprecated. "
            "Consider using RecipeStructurerV2 for better performance."
        )
        
    async def structure(self, content, progress_callback: Optional[Callable[[str], Awaitable[None]]] = None):
        """Structure recipe content into a standardized format."""
        logger.info("Starting recipe structuring (V1)")
        logger.debug(f"Using provider: {self.provider}")
        
        try:
            cleaned_text, recipe_base, recipe_graph = await generate_recipe(
                content.main_content,
                image_urls=content.image_urls,
                provider=self.provider,
                progress_callback=progress_callback
            )
            
            recipe = {
                "metadata": {
                    **recipe_base.metadata.model_dump(),
                    "sourceUrl": None,
                    "sourceImageUrl": recipe_base.metadata.sourceImageUrl
                },
                "ingredients": [ing.model_dump() for ing in recipe_base.ingredients],
                "tools": recipe_base.tools,
                "steps": [step.model_dump() for step in recipe_graph.steps],
                "final_state": recipe_graph.final_state.model_dump()
            }
            
            logger.info("Recipe successfully structured (V1)")
            return recipe
            
        except RecipeRejectedError:
            raise
        except Exception as e:
            logger.error(f"Error structuring recipe: {str(e)}")
            raise
    
    async def structure_from_text(self, text, image_data=None, progress_callback: Optional[Callable[[str], Awaitable[None]]] = None):
        """Structure recipe from raw text."""
        logger.info("Starting recipe structuring from text (V1)")
        
        cleaned_text, recipe_base, recipe_graph = await generate_recipe(
            text,
            provider=self.provider,
            progress_callback=progress_callback
        )
        
        recipe = {
            "metadata": recipe_base.metadata.model_dump(),
            "ingredients": [ing.model_dump() for ing in recipe_base.ingredients],
            "tools": recipe_base.tools,
            "steps": [step.model_dump() for step in recipe_graph.steps],
            "final_state": recipe_graph.final_state.model_dump()
        }
        
        logger.info("Recipe successfully structured from text (V1)")
        return recipe


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # V2 (Recommended)
    "RecipeStructurerV2",
    "RecipeGeneratorV2", 
    "generate_recipe_v2",
    "RecipeV2",
    "MetadataV2",
    "IngredientV2",
    "StepV2",
    
    # V1 (Legacy)
    "RecipeStructurer",
    "generate_recipe",
    
    # Shared
    "RecipeRejectedError",
] 