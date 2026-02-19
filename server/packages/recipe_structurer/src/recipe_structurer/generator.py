"""
Recipe Generator — 3-pass pipeline using Instructor + DeepSeek V3.2 + NER

Pass 1   (Preformat):  Raw text → clean structured text with [english_name] {category} annotations
Pass 1.5 (NER):        Ingredient lines → Ingredient objects via NER model + unit normalization
Pass 2   (DAG):        Structured text + pre-parsed ingredients → Recipe JSON with validated graph

Pass 1 uses the raw OpenAI client (text output).
Pass 1.5 uses edwardjross/xlm-roberta-base-finetuned-recipe-all (token classification).
Pass 2 uses Instructor (structured JSON output with Pydantic validation).
"""

import os
import logging
from typing import Optional, Callable, Awaitable, Literal

import instructor
from pydantic import ValidationError

# Use Langfuse-instrumented OpenAI client if available (auto-captures LLM generations)
try:
    from recipe_scraper.observability import get_async_openai_class
    AsyncOpenAI = get_async_openai_class()
except ImportError:
    from openai import AsyncOpenAI

from .models.recipe import Recipe
from .prompts.unified import SYSTEM_PROMPT, get_user_prompt
from .services.preformat import preformat_recipe
from .services.ingredient_parser import (
    parse_ingredients_from_preformat,
    correct_step_references,
)
from .exceptions import RecipeRejectedError

logger = logging.getLogger(__name__)

# Provider configurations
PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-v3.2",
        "env_key": "OPENROUTER_API_KEY",
    },
}

DEFAULT_PROVIDER = "openrouter"  # OpenRouter by default for convenience
MAX_RETRIES = 3
MAX_TOKENS_PREFORMAT = 4096
MAX_TOKENS_DAG = 8192


class RecipeGenerator:
    """
    Recipe Generator — 3-pass pipeline.

    Pass 1   (Preformat): Cleans and structures raw recipe text with English annotations.
    Pass 1.5 (NER):       Parses ingredient lines into Ingredient objects via NER model.
    Pass 2   (DAG):       Builds the Recipe JSON graph from structured text + pre-parsed ingredients.

    Features:
    - 3-pass architecture: LLM preformat → NER ingredient parsing → LLM DAG construction
    - NER model (edwardjross/xlm-roberta-base-finetuned-recipe-all) for deterministic ingredient extraction
    - Unit normalization and fuzzy matching for robust ID correction
    - Automatic Pydantic validation with retries on Pass 2
    - Streaming progress updates
    - Robust error handling
    - Supports DeepSeek direct or OpenRouter
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Literal["deepseek", "openrouter"] = DEFAULT_PROVIDER
    ):
        """
        Initialize the generator.

        Args:
            api_key: API key. If not provided, reads from env var based on provider.
            provider: "deepseek" for direct API or "openrouter" for OpenRouter (default).
        """
        self.provider = provider
        config = PROVIDERS[provider]

        # Get API key from param or environment
        self.api_key = api_key or os.getenv(config["env_key"])
        if not self.api_key:
            raise ValueError(
                f"{provider.upper()} API key is required. "
                f"Set {config['env_key']} env var or pass api_key."
            )

        self.model = config["model"]
        self.base_url = config["base_url"]

        # Build headers and provider routing for OpenRouter
        extra_headers = {}
        self._provider_routing = {}
        if provider == "openrouter":
            extra_headers = {
                "HTTP-Referer": "https://github.com/recipe-display",
                "X-Title": "Recipe Structurer",
            }
            # Route to DeepSeek provider with throughput optimization
            self._provider_routing = {
                "provider": {
                    "order": ["DeepSeek"],
                    "sort": "throughput",
                    "allow_fallbacks": True,
                    "require_parameters": True,
                }
            }

        # Initialize async OpenAI client (raw — for Pass 1)
        self._base_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=extra_headers if extra_headers else None
        )

        # Wrap with Instructor for structured outputs (for Pass 2)
        self.client = instructor.from_openai(self._base_client)

        logger.info(f"RecipeGenerator initialized with {provider}: {self.model}")

    async def generate(
        self,
        recipe_text: str,
        image_urls: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Recipe:
        """
        Generate a structured recipe from raw text using the 2-pass pipeline.

        Pass 1: Preformat raw text into clean structured text.
        Pass 2: Build Recipe JSON graph from structured text.

        Args:
            recipe_text: Raw recipe content (from web scraping or user input)
            image_urls: Optional list of image URLs found with the recipe
            progress_callback: Optional async callback for progress updates

        Returns:
            Recipe: Validated and structured recipe

        Raises:
            RecipeRejectedError: If content is not a valid recipe
            ValidationError: If LLM output doesn't match schema after retries
        """
        # ── Pass 1: Preformat ─────────────────────────────────────────────
        if progress_callback:
            await progress_callback("Cleaning and preformatting recipe...")

        logger.info(f"[Pass 1] Preformatting recipe ({len(recipe_text)} chars)")

        preformatted = await preformat_recipe(
            client=self._base_client,
            model=self.model,
            recipe_text=recipe_text,
            image_urls=image_urls,
            max_tokens=MAX_TOKENS_PREFORMAT,
            extra_body=self._provider_routing or None,
        )

        logger.info(f"[Pass 1] Complete — {len(preformatted)} chars output")
        logger.debug(f"[Pass 1] Preview:\n{preformatted[:500]}")

        # ── Pass 1.5: CRF ingredient parsing ──────────────────────────────
        if progress_callback:
            await progress_callback("Parsing ingredients...")

        logger.info("[Pass 1.5] Parsing ingredients from preformatted text")

        try:
            ner_ingredients = parse_ingredients_from_preformat(preformatted)
        except Exception as e:
            logger.error(f"[Pass 1.5] CRF parsing failed: {e}", exc_info=True)
            ner_ingredients = []

        # Track whether CRF produced usable ingredients
        use_ner_ingredients = len(ner_ingredients) > 0
        if not use_ner_ingredients:
            logger.warning(
                "[Pass 1.5] No CRF ingredients parsed — "
                "LLM ingredients will be kept after Pass 2"
            )
        else:
            logger.info(
                f"[Pass 1.5] Parsed {len(ner_ingredients)} ingredients "
                f"({sum(1 for i in ner_ingredients if i.quantity is not None)} with quantities)"
            )

        # Build ingredients JSON for the Pass 2 prompt
        import json
        ingredients_json = json.dumps(
            [ing.model_dump(exclude_none=True) for ing in ner_ingredients],
            indent=2,
            ensure_ascii=False,
        )

        # ── Pass 2: DAG construction ──────────────────────────────────────
        if progress_callback:
            await progress_callback("Building recipe graph...")

        logger.info("[Pass 2] Building DAG from preformatted text + NER ingredients")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": get_user_prompt(preformatted, ingredients_json)},
        ]

        try:
            recipe = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=Recipe,
                max_tokens=MAX_TOKENS_DAG,
                max_retries=MAX_RETRIES,
                temperature=0.1,
                **({"extra_body": self._provider_routing} if self._provider_routing else {}),
            )

            # Replace LLM-generated ingredients with CRF-parsed ones
            # (only if CRF produced results; otherwise keep LLM ingredients)
            if use_ner_ingredients:
                recipe.ingredients = ner_ingredients

                # Correct step references using fuzzy matching
                ingredient_ids = {ing.id for ing in ner_ingredients}
                produced_states = {step.produces for step in recipe.steps}
                correct_step_references(recipe.steps, ingredient_ids, produced_states)

                # Re-validate graph integrity after post-processing
                try:
                    Recipe.model_validate(recipe.model_dump())
                except ValidationError as e:
                    logger.error(f"[Post-processing] Graph invalid after corrections: {e}")
                    raise
            else:
                logger.warning("[Post-processing] Using LLM ingredients (CRF was empty)")

            # Store original text and preformatted text for debugging
            recipe.originalText = recipe_text.strip()
            recipe.preformattedText = preformatted

            logger.info(f"[Pass 2] Recipe generated: {recipe.metadata.title}")

            if progress_callback:
                await progress_callback("Recipe structured successfully!")

            return recipe

        except ValidationError as e:
            logger.error(f"[Pass 2] Validation failed after {MAX_RETRIES} retries: {e}")
            raise
        except Exception as e:
            # Check if it's a rejection response
            error_msg = str(e).lower()
            if "not_a_recipe" in error_msg or "not a valid recipe" in error_msg:
                raise RecipeRejectedError("Content is not a valid recipe") from e

            logger.error(f"[Pass 2] DAG generation failed: {e}")
            raise

    async def generate_with_streaming(
        self,
        recipe_text: str,
        image_urls: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Recipe:
        """
        Generate recipe with streaming partial results on Pass 2.

        Pass 1 runs fully first, then Pass 2 streams partial results
        for more granular progress updates.

        Args:
            recipe_text: Raw recipe content
            image_urls: Optional list of image URLs
            progress_callback: Optional async callback for progress updates

        Returns:
            Recipe: Validated and structured recipe
        """
        # ── Pass 1: Preformat (non-streaming) ─────────────────────────────
        if progress_callback:
            await progress_callback("Cleaning and preformatting recipe...")

        logger.info(f"[Pass 1] Preformatting recipe ({len(recipe_text)} chars)")

        preformatted = await preformat_recipe(
            client=self._base_client,
            model=self.model,
            recipe_text=recipe_text,
            image_urls=image_urls,
            max_tokens=MAX_TOKENS_PREFORMAT,
            extra_body=self._provider_routing or None,
        )

        logger.info(f"[Pass 1] Complete — {len(preformatted)} chars output")

        # ── Pass 1.5: NER ingredient parsing ──────────────────────────────
        if progress_callback:
            await progress_callback("Parsing ingredients...")

        logger.info("[Pass 1.5] Parsing ingredients from preformatted text (streaming)")

        try:
            ner_ingredients = parse_ingredients_from_preformat(preformatted)
        except Exception as e:
            logger.error(f"[Pass 1.5] CRF parsing failed: {e}", exc_info=True)
            ner_ingredients = []

        use_ner_ingredients = len(ner_ingredients) > 0
        if not use_ner_ingredients:
            logger.warning(
                "[Pass 1.5] No CRF ingredients parsed — "
                "LLM ingredients will be kept after Pass 2"
            )
        else:
            logger.info(f"[Pass 1.5] Parsed {len(ner_ingredients)} ingredients")

        import json
        ingredients_json = json.dumps(
            [ing.model_dump(exclude_none=True) for ing in ner_ingredients],
            indent=2,
            ensure_ascii=False,
        )

        # ── Pass 2: DAG construction (streaming) ──────────────────────────
        if progress_callback:
            await progress_callback("Building recipe graph...")

        logger.info("[Pass 2] Streaming DAG construction")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": get_user_prompt(preformatted, ingredients_json)},
        ]

        partial_recipe = None
        current_section = ""

        try:
            async for partial in self.client.chat.completions.create_partial(
                model=self.model,
                messages=messages,
                response_model=Recipe,
                max_tokens=MAX_TOKENS_DAG,
                temperature=0.1,
                **({"extra_body": self._provider_routing} if self._provider_routing else {}),
            ):
                partial_recipe = partial

                # Progress updates based on streaming sections
                if partial.metadata and partial.metadata.title and current_section != "metadata":
                    current_section = "metadata"
                    if progress_callback:
                        await progress_callback(f"Processing: {partial.metadata.title}")

                elif partial.ingredients and len(partial.ingredients) > 0 and current_section != "ingredients":
                    current_section = "ingredients"
                    if progress_callback:
                        await progress_callback(f"Found {len(partial.ingredients)} ingredients...")

                elif partial.steps and len(partial.steps) > 0 and current_section != "steps":
                    current_section = "steps"
                    if progress_callback:
                        await progress_callback(f"Generating steps ({len(partial.steps)})...")

            if partial_recipe is None:
                raise ValueError("No recipe generated")

            # Replace LLM-generated ingredients with CRF-parsed ones
            # (only if CRF produced results; otherwise keep LLM ingredients)
            if use_ner_ingredients:
                partial_recipe.ingredients = ner_ingredients

                # Correct step references using fuzzy matching
                ingredient_ids = {ing.id for ing in ner_ingredients}
                produced_states = {step.produces for step in partial_recipe.steps}
                correct_step_references(partial_recipe.steps, ingredient_ids, produced_states)

                # Re-validate graph integrity after post-processing
                try:
                    Recipe.model_validate(partial_recipe.model_dump())
                except ValidationError as e:
                    logger.error(f"[Post-processing] Graph invalid after corrections: {e}")
                    raise
            else:
                logger.warning("[Post-processing] Using LLM ingredients (CRF was empty)")

            partial_recipe.originalText = recipe_text.strip()
            partial_recipe.preformattedText = preformatted

            logger.info(f"[Pass 2] Recipe streamed: {partial_recipe.metadata.title}")

            if progress_callback:
                await progress_callback("Recipe completed!")

            return partial_recipe

        except Exception as e:
            logger.error(f"[Pass 2] Streaming generation failed: {e}")
            raise


# Convenience function for backwards compatibility
async def generate_recipe(
    recipe_text: str,
    image_urls: Optional[list[str]] = None,
    progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    api_key: Optional[str] = None,
    provider: Literal["deepseek", "openrouter"] = DEFAULT_PROVIDER
) -> Recipe:
    """
    Generate a structured recipe using the 3-pass pipeline.

    Convenience function that creates a generator instance
    and calls generate() in one step.
    """
    generator = RecipeGenerator(api_key=api_key, provider=provider)
    return await generator.generate(recipe_text, image_urls, progress_callback)


# Test function
async def test_generator():
    """Test the generator with a sample recipe."""
    import sys
    from dotenv import load_dotenv

    # Load env from parent server folder
    load_dotenv()
    load_dotenv('../../.env')

    # Check which provider to use
    provider = "openrouter"  # Default
    if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your-deepseek-api-key-here":
        provider = "deepseek"
    elif os.getenv("OPENROUTER_API_KEY"):
        provider = "openrouter"
    else:
        print("No API key found!")
        print("   Set OPENROUTER_API_KEY or DEEPSEEK_API_KEY in your .env file")
        sys.exit(1)

    print(f"Using provider: {provider}")
    print(f"   Model: {PROVIDERS[provider]['model']}")
    print()

    sample_recipe = """
    Classic Chocolate Chip Cookies

    Prep time: 15 minutes
    Cook time: 10-12 minutes
    Makes: 24 cookies

    Ingredients:
    - 2 1/4 cups all-purpose flour
    - 1 tsp baking soda
    - 1 tsp salt
    - 1 cup (2 sticks) butter, softened
    - 3/4 cup granulated sugar
    - 3/4 cup packed brown sugar
    - 2 large eggs
    - 1 tsp vanilla extract
    - 2 cups chocolate chips

    Instructions:
    1. Preheat oven to 375°F (190°C).
    2. Combine flour, baking soda and salt in small bowl.
    3. Beat butter, granulated sugar, brown sugar and vanilla extract in large mixer bowl until creamy.
    4. Add eggs, one at a time, beating well after each addition.
    5. Gradually beat in flour mixture.
    6. Stir in chocolate chips.
    7. Drop rounded tablespoon of dough onto ungreased baking sheets.
    8. Bake for 9 to 11 minutes or until golden brown.
    9. Cool on baking sheets for 2 minutes; remove to wire racks to cool completely.
    """

    async def progress(msg: str):
        print(f"   {msg}")

    try:
        generator = RecipeGenerator(provider=provider)
        recipe = await generator.generate(sample_recipe, progress_callback=progress)

        print(f"\nRecipe generated successfully!")
        print(f"Title: {recipe.metadata.title}")
        print(f"Servings: {recipe.metadata.servings}")
        print(f"Difficulty: {recipe.metadata.difficulty}")
        print(f"Ingredients: {len(recipe.ingredients)}")
        print(f"Steps: {len(recipe.steps)}")
        print(f"Final state: {recipe.finalState}")

        # Print full JSON
        import json
        print(f"\nFull recipe JSON:")
        print(json.dumps(recipe.model_dump(), indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_generator())
