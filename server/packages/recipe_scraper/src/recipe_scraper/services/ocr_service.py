"""
OCR Service — Extract recipe text from images using OpenRouter Vision API.

Uses google/gemini-2.0-flash-001 for fast, cheap, and accurate OCR.
Cost: ~$0.0002 per image (~0.02 cents).
"""

import base64
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Vision model config
VISION_MODEL = "google/gemini-2.0-flash-001"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 4096

OCR_SYSTEM_PROMPT = """You are a precise OCR assistant specialized in extracting recipe text from images.
Extract ALL text from the image exactly as written. Include:
- Recipe title
- Description/introduction if present
- Ingredients list with exact quantities
- Instructions/steps
- Cooking times, temperatures, servings
- Any notes or tips

Return the raw text faithfully. Do not add formatting, comments, or interpretation.
If the image contains text in a language other than English, keep it in the original language."""

OCR_USER_PROMPT = "Extract all recipe text from this image. Return the complete text exactly as written."


class OCRService:
    """Extract recipe text from images using OpenRouter Vision API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required for OCR. "
                "Set the env var or pass api_key."
            )

    async def extract_text_from_image(
        self,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """
        Extract recipe text from an image.

        Provide exactly one of: image_path, image_base64, or image_url.

        Args:
            image_path: Path to a local image file.
            image_base64: Base64-encoded image data (with or without data URI prefix).
            image_url: Public URL of the image.

        Returns:
            Extracted recipe text.

        Raises:
            ValueError: If no image source is provided or image can't be read.
            RuntimeError: If the API call fails.
        """
        image_content = self._build_image_content(image_path, image_base64, image_url)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/recipe-display",
            "X-Title": "Recipe OCR",
            "Content-Type": "application/json",
        }

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {"role": "system", "content": OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OCR_USER_PROMPT},
                        image_content,
                    ],
                },
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.1,
        }

        logger.info(f"Calling OCR API ({VISION_MODEL})...")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"OCR API error {response.status_code}: {error_detail}")
            raise RuntimeError(f"OCR API failed ({response.status_code}): {error_detail}")

        data = response.json()

        if "choices" not in data or not data["choices"]:
            raise RuntimeError(f"OCR API returned unexpected response: {data}")

        extracted_text = data["choices"][0]["message"]["content"]

        # Log usage stats
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        logger.info(
            f"OCR complete: {len(extracted_text)} chars extracted "
            f"({prompt_tokens} input + {completion_tokens} output tokens)"
        )

        return extracted_text

    def _build_image_content(
        self,
        image_path: Optional[str],
        image_base64: Optional[str],
        image_url: Optional[str],
    ) -> dict:
        """Build the image content block for the API request."""
        sources = sum(x is not None for x in [image_path, image_base64, image_url])
        if sources == 0:
            raise ValueError("Provide image_path, image_base64, or image_url.")
        if sources > 1:
            raise ValueError("Provide only one image source.")

        if image_url:
            return {
                "type": "image_url",
                "image_url": {"url": image_url},
            }

        if image_path:
            path = Path(image_path)
            if not path.exists():
                raise ValueError(f"Image file not found: {image_path}")

            image_data = path.read_bytes()
            b64 = base64.b64encode(image_data).decode("utf-8")
            mime = self._guess_mime(path.suffix)
            return {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }

        # image_base64
        if image_base64.startswith("data:"):
            # Already has data URI prefix
            url = image_base64
        else:
            # Raw base64 — assume JPEG
            url = f"data:image/jpeg;base64,{image_base64}"

        return {
            "type": "image_url",
            "image_url": {"url": url},
        }

    @staticmethod
    def _guess_mime(suffix: str) -> str:
        """Guess MIME type from file extension."""
        mapping = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mapping.get(suffix.lower(), "image/jpeg")
