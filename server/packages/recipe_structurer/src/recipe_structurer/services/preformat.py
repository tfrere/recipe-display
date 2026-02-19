"""
Service for preformatting raw recipe text (Pass 1 of 2-pass pipeline).

Takes raw, potentially messy recipe text and outputs a clean structured
text format that Pass 2 (DAG construction) can easily consume.
"""

import asyncio
import logging
from typing import Optional, List

from openai import AsyncOpenAI

from ..prompts.preformat import PREFORMAT_SYSTEM_PROMPT, get_preformat_user_prompt
from ..exceptions import RecipeRejectedError

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY_S = 3
LLM_TIMEOUT_S = 120


async def preformat_recipe(
    client: AsyncOpenAI,
    model: str,
    recipe_text: str,
    image_urls: Optional[List[str]] = None,
    max_tokens: int = 4096,
    extra_body: Optional[dict] = None,
) -> str:
    """
    Preformat raw recipe text into a clean structured text format.

    This is Pass 1 of the 2-pass pipeline. It does NOT produce JSON —
    it outputs structured plain text that Pass 2 will convert to Recipe.

    Retries up to MAX_RETRIES times on transient errors (network, 5xx).
    Each LLM call is bounded by LLM_TIMEOUT_S.

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
        ValueError: If the LLM returns an empty response after retries.
    """
    logger.info(f"Preformatting recipe ({len(recipe_text)} chars)")

    messages = [
        {"role": "system", "content": PREFORMAT_SYSTEM_PROMPT},
        {"role": "user", "content": get_preformat_user_prompt(recipe_text, image_urls)},
    ]

    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    **({"extra_body": extra_body} if extra_body else {}),
                ),
                timeout=LLM_TIMEOUT_S,
            )

            result = response.choices[0].message.content
            if not result or not result.strip():
                raise ValueError("Preformat pass returned empty response from LLM")

            result = result.strip()

            if result.startswith("REJECT:"):
                reason = result.replace("REJECT:", "", 1).strip()
                logger.info(f"Recipe rejected during preformat: {reason}")
                raise RecipeRejectedError(reason)

            logger.info(f"Preformat complete ({len(result)} chars output)")
            logger.debug(f"Preformat output preview: {result[:300]}...")
            return result

        except RecipeRejectedError:
            raise
        except (asyncio.TimeoutError, Exception) as exc:
            last_error = exc
            is_timeout = isinstance(exc, asyncio.TimeoutError)
            label = "timeout" if is_timeout else type(exc).__name__

            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_S * attempt
                logger.warning(
                    f"[Pass 1] Attempt {attempt}/{MAX_RETRIES} failed ({label}: {exc}), "
                    f"retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"[Pass 1] All {MAX_RETRIES} attempts failed. Last error: {label}: {exc}"
                )

    raise last_error  # type: ignore[misc]
