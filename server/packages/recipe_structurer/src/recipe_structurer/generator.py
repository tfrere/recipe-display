"""
Recipe Generator — 3-pass pipeline using Instructor + DeepSeek V3.2 + NER

Pass 1   (Preformat):  Raw text → clean structured text with [english_name] {category} annotations
Pass 1.5 (NER):        Ingredient lines → Ingredient objects via NER model + unit normalization
Pass 2   (DAG):        Structured text + pre-parsed ingredients → Recipe JSON with validated graph

Pass 1 uses the raw OpenAI client (text output).
Pass 1.5 uses strangetom/ingredient-parser (CRF v2.5.0, deterministic parsing).
Pass 2 uses Instructor (structured JSON output with Pydantic validation).
"""

import os
import re
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
from .shared import clean_title

logger = logging.getLogger(__name__)

_LANG_RE = re.compile(r"^LANGUAGE:\s*(\w+)", re.MULTILINE)


def _extract_language(preformatted: str) -> str:
    """Extract ISO 639-1 language code from Pass 1 preformatted output."""
    match = _LANG_RE.search(preformatted)
    if match:
        return match.group(1).strip().lower()[:2]
    return "en"

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
PIPELINE_VERSION = "3.0.0"
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
    - CRF parser (strangetom/ingredient-parser v2.5.0) for deterministic ingredient extraction
    - Deterministic ID resolution (suffix strip + name lookup) for robust reference correction
    - Automatic Pydantic validation with retries on Pass 2
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
        Generate a structured recipe from raw text using the 3-pass pipeline.

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

        preformat_max_tokens = MAX_TOKENS_PREFORMAT
        if len(recipe_text) > 30_000:
            preformat_max_tokens = 8192
        elif len(recipe_text) > 15_000:
            preformat_max_tokens = 6144

        preformatted = await preformat_recipe(
            client=self._base_client,
            model=self.model,
            recipe_text=recipe_text,
            image_urls=image_urls,
            max_tokens=preformat_max_tokens,
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
                recipe.metadata.ingredientSource = "ner"

                # Correct step references using deterministic resolution
                ingredient_ids = {ing.id for ing in ner_ingredients}
                produced_states = {step.produces for step in recipe.steps}
                correct_step_references(
                    recipe.steps, ingredient_ids, produced_states,
                    ingredients=ner_ingredients,
                )

                # Re-validate graph integrity after post-processing
                try:
                    Recipe.model_validate(recipe.model_dump())
                except ValidationError as e:
                    logger.error(f"[Post-processing] Graph invalid after corrections: {e}")
                    raise
            else:
                recipe.metadata.ingredientSource = "llm"
                logger.warning("[Post-processing] Using LLM ingredients (CRF was empty)")

            # Store original text, preformatted text, and detected language
            recipe.originalText = recipe_text.strip()
            recipe.preformattedText = preformatted
            recipe.metadata.language = _extract_language(preformatted)

            # Strip trailing parentheticals from title (e.g. "(Vegan + GF)")
            recipe.metadata.title = clean_title(recipe.metadata.title)

            logger.info(f"[Pass 2] Recipe generated: {recipe.metadata.title} (lang={recipe.metadata.language})")

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
