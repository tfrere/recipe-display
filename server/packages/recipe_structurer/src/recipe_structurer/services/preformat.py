"""
Service for preformatting raw recipe text (Pass 1 of 2-pass pipeline).

Takes raw, potentially messy recipe text and outputs a clean structured
text format that Pass 2 (DAG construction) can easily consume.
"""

import logging
from typing import Optional, List

from openai import AsyncOpenAI

from ..prompts.preformat_v2 import PREFORMAT_SYSTEM_PROMPT, get_preformat_user_prompt
from ..exceptions import RecipeRejectedError

logger = logging.getLogger(__name__)


async def preformat_recipe(
    client: AsyncOpenAI,
    model: str,
    recipe_text: str,
    image_urls: Optional[List[str]] = None,
    max_tokens: int = 4096,
) -> str:
    """
    Preformat raw recipe text into a clean structured text format.

    This is Pass 1 of the 2-pass pipeline. It does NOT produce JSON —
    it outputs structured plain text that Pass 2 will convert to RecipeV2.

    Args:
        client: AsyncOpenAI client (raw, not wrapped by Instructor).
        model: Model name to use.
        recipe_text: Raw recipe content (from scraping, user input, etc.).
        image_urls: Optional list of image URLs found with the recipe.
        max_tokens: Maximum tokens for the response.

    Returns:
        Preformatted structured text.

    Raises:
        RecipeRejectedError: If the content is not a valid recipe.
        ValueError: If the LLM returns an empty response.
    """
    logger.info(f"Preformatting recipe ({len(recipe_text)} chars)")

    messages = [
        {"role": "system", "content": PREFORMAT_SYSTEM_PROMPT},
        {"role": "user", "content": get_preformat_user_prompt(recipe_text, image_urls)},
    ]

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,
    )

    result = response.choices[0].message.content
    if not result or not result.strip():
        raise ValueError("Preformat pass returned empty response from LLM")

    result = result.strip()

    # Check for rejection
    if result.startswith("REJECT:"):
        reason = result.replace("REJECT:", "", 1).strip()
        logger.info(f"Recipe rejected during preformat: {reason}")
        raise RecipeRejectedError(reason)

    logger.info(f"Preformat complete ({len(result)} chars output)")
    logger.debug(f"Preformat output preview: {result[:300]}...")

    return result
