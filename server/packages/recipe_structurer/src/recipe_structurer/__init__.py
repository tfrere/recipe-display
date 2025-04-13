"""Recipe structurer package for converting raw recipe text into structured data."""

import logging
from typing import Optional, Callable, Awaitable, Dict, Any, List

from .generator import generate_recipe
from .providers.deepseek_model import StreamingDeepseekModel
from .providers.mistral_model import StreamingMistralModel
from .providers.huggingface_model import StreamingHuggingFaceModel
from .exceptions import RecipeRejectedError
from .constants import DEFAULT_MODEL

logger = logging.getLogger(__name__)

class RecipeStructurer:
    """Main class for structuring recipes."""
    
    def __init__(self, provider: str = DEFAULT_MODEL):
        """Initialize with specified provider."""
        self.provider = provider
        
    async def structure(self, content, progress_callback: Optional[Callable[[str], Awaitable[None]]] = None):
        """
        Structure recipe content into a standardized format.
        
        Args:
            content: The content object containing recipe text and images
            progress_callback: Optional callback for streaming progress updates
            
        Returns:
            A structured recipe dictionary
        """
        logger.info("Starting recipe structuring")
        logger.debug(f"Using provider: {self.provider}")
        
        try:
            cleaned_text, recipe_base, recipe_graph = await generate_recipe(
                content.main_content,
                image_urls=content.image_urls,
                provider=self.provider,
                progress_callback=progress_callback
            )
            logger.debug("Recipe generation completed successfully")
            
            # Combine data into final recipe format
            recipe = {
                "metadata": {
                    **recipe_base.metadata.model_dump(),
                    "sourceUrl": None,  # On initialise à None par défaut
                    "sourceImageUrl": recipe_base.metadata.sourceImageUrl  # On utilise l'image choisie par le LLM
                },
                "ingredients": [ing.model_dump() for ing in recipe_base.ingredients],
                "tools": recipe_base.tools,
                "steps": [step.model_dump() for step in recipe_graph.steps],
                "final_state": recipe_graph.final_state.model_dump()
            }
            logger.info("Recipe successfully structured")
            
            return recipe
        except RecipeRejectedError as e:
            logger.warning(f"Recipe was rejected: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error structuring recipe: {str(e)}")
            logger.debug(f"Error type: {type(e).__name__}")
            import traceback
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            raise
    
    async def structure_from_text(self, text, image_data=None, progress_callback: Optional[Callable[[str], Awaitable[None]]] = None):
        """
        Structure recipe from raw text.
        
        Args:
            text: The raw recipe text
            image_data: Optional image data
            progress_callback: Optional callback for streaming progress updates
            
        Returns:
            A structured recipe dictionary
        """
        logger.info("Starting recipe structuring from text")
        
        cleaned_text, recipe_base, recipe_graph = await generate_recipe(
            text,
            provider=self.provider,
            progress_callback=progress_callback
        )
        
        # TODO: Handle image_data if provided
        
        recipe = {
            "metadata": recipe_base.metadata.model_dump(),
            "ingredients": [ing.model_dump() for ing in recipe_base.ingredients],
            "tools": recipe_base.tools,
            "steps": [step.model_dump() for step in recipe_graph.steps],
            "final_state": recipe_graph.final_state.model_dump()
        }
        
        logger.info("Recipe successfully structured from text")
        return recipe

__all__ = ["RecipeStructurer", "generate_recipe", "RecipeRejectedError"] 