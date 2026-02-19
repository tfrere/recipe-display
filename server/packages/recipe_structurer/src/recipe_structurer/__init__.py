"""
Recipe Structurer Package
=========================

Converts raw recipe text into structured data using LLMs.

Uses Instructor + DeepSeek V3.2 with a 3-pass pipeline:
  - Pass 1 (Preformat): Raw text → clean structured text with annotations
  - Pass 1.5 (NER): Ingredient lines → Ingredient objects via NER model
  - Pass 2 (DAG): Structured text + ingredients → Recipe JSON with validated graph

Usage:
    from recipe_structurer import RecipeStructurer

    structurer = RecipeStructurer()
    recipe = await structurer.structure(content)
"""

import logging
from typing import Optional, Callable, Awaitable

from .exceptions import RecipeRejectedError
from .generator import RecipeGenerator, generate_recipe
from .models.recipe import Recipe, Metadata, Ingredient, Step

logger = logging.getLogger(__name__)


class RecipeStructurer:
    """
    Recipe Structurer using Instructor + DeepSeek V3.2.

    Uses a 3-pass pipeline (preformat → NER → DAG) with automatic Pydantic validation.

    Example:
        structurer = RecipeStructurer()
        recipe = await structurer.structure(content)

        # Access structured data
        print(recipe.metadata.title)
        print(recipe.ingredients)
        print(recipe.steps)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the structurer.

        Args:
            api_key: DeepSeek API key. Defaults to DEEPSEEK_API_KEY env var.
        """
        self._generator = RecipeGenerator(api_key=api_key)

    async def structure(
        self,
        content,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Recipe:
        """
        Structure recipe content.

        When content.structured_data (schema.org/Recipe JSON-LD) is available,
        a cleaner recipe text is built from it before sending to the LLM pipeline.
        This significantly improves structuring accuracy.

        Args:
            content: Content object with main_content, image_urls, and
                     optional structured_data attributes
            progress_callback: Optional async callback for progress updates

        Returns:
            Recipe: Validated and structured recipe
        """
        logger.info("Structuring recipe")

        structured_data = getattr(content, "structured_data", None)
        recipe_text = content.main_content

        # When schema.org/Recipe data is available, build a clean recipe text from it
        if structured_data:
            clean_text = self._build_text_from_schema(structured_data)
            if clean_text:
                logger.info(
                    "Using schema.org/Recipe data as primary input "
                    f"({len(clean_text)} chars vs {len(recipe_text)} chars raw)"
                )
                recipe_text = clean_text

        recipe = await self._generator.generate(
            recipe_text=recipe_text,
            image_urls=getattr(content, "image_urls", None),
            progress_callback=progress_callback,
        )

        # Store the schema.org data in the recipe for downstream use (times, servings)
        if structured_data:
            recipe._schema_data = structured_data

        logger.info(f"Recipe structured: {recipe.metadata.title}")
        return recipe

    @staticmethod
    def _build_text_from_schema(data: dict) -> Optional[str]:
        """
        Convert schema.org/Recipe JSON-LD into clean recipe text.

        The output format matches what the preformat LLM expects as input,
        making its job much easier (just add annotations).

        Returns:
            Clean text, or None if the data is too incomplete.
        """
        parts = []

        # Title
        name = data.get("name", "")
        if name:
            parts.append(name)
            parts.append("")

        # Description
        desc = data.get("description", "")
        if desc:
            parts.append(desc)
            parts.append("")

        # Metadata line
        meta_parts = []
        yield_val = data.get("recipeYield")
        if yield_val:
            if isinstance(yield_val, list):
                yield_val = yield_val[0]
            meta_parts.append(f"Servings: {yield_val}")
        for time_field, label in [
            ("prepTime", "Prep time"),
            ("cookTime", "Cook time"),
            ("totalTime", "Total time"),
        ]:
            val = data.get(time_field)
            if val:
                meta_parts.append(f"{label}: {val}")
        if meta_parts:
            parts.append(" | ".join(meta_parts))
            parts.append("")

        # Ingredients
        ingredients = data.get("recipeIngredient", [])
        if not ingredients:
            return None  # Not enough data to be useful
        parts.append("Ingredients:")
        for ing in ingredients:
            parts.append(f"- {ing}")
        parts.append("")

        # Instructions
        instructions = data.get("recipeInstructions", [])
        if instructions:
            parts.append("Instructions:")
            for i, step in enumerate(instructions, 1):
                if isinstance(step, dict):
                    text = step.get("text", "")
                elif isinstance(step, str):
                    text = step
                else:
                    continue
                if text:
                    parts.append(f"{i}. {text}")
            parts.append("")

        # Notes
        notes = data.get("recipeNotes") or data.get("notes")
        if notes:
            if isinstance(notes, str):
                parts.append(f"Notes: {notes}")
            elif isinstance(notes, list):
                parts.append("Notes:")
                for note in notes:
                    parts.append(f"- {note}")

        # Author
        author = data.get("author")
        if author:
            if isinstance(author, dict):
                author = author.get("name", "")
            if isinstance(author, list) and author:
                author = author[0].get("name", "") if isinstance(author[0], dict) else str(author[0])
            if author:
                parts.append(f"\nAuthor: {author}")

        return "\n".join(parts)

    async def structure_from_text(
        self,
        text: str,
        image_urls: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Recipe:
        """
        Structure recipe from raw text.

        Args:
            text: Raw recipe text
            image_urls: Optional list of image URLs
            progress_callback: Optional async callback for progress updates

        Returns:
            Recipe: Validated and structured recipe
        """
        logger.info("Structuring recipe from text")

        recipe = await self._generator.generate(
            recipe_text=text,
            image_urls=image_urls,
            progress_callback=progress_callback,
        )

        logger.info(f"Recipe structured from text: {recipe.metadata.title}")
        return recipe

    def to_dict(self, recipe: Recipe) -> dict:
        """Convert Recipe to dictionary format."""
        return recipe.model_dump()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "RecipeStructurer",
    "RecipeGenerator",
    "generate_recipe",
    "Recipe",
    "Metadata",
    "Ingredient",
    "Step",
    "RecipeRejectedError",
]
