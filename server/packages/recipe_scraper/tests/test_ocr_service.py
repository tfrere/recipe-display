"""
Tests for OCR Service.

Includes:
- Unit tests with mocked API responses (fast, no API key needed)
- Integration test with real API call (requires OPENROUTER_API_KEY, skipped in CI)
"""

import base64
import json
import pytest
import pytest_asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from recipe_scraper.services.ocr_service import OCRService, VISION_MODEL


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def ocr_service():
    """OCR service with a fake API key."""
    return OCRService(api_key="test-api-key")


@pytest.fixture
def sample_base64_image():
    """A minimal valid JPEG as base64 (1x1 white pixel)."""
    # Smallest valid JPEG
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00,
        0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB,
        0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07,
        0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B,
        0x0B, 0x0C, 0x19, 0x12, 0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E,
        0x1D, 0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C,
        0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34,
        0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
        0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01,
        0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01,
        0x03, 0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00,
        0x01, 0x7D, 0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21,
        0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
        0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1,
        0xF0, 0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18,
        0x19, 0x1A, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35, 0x36,
        0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64,
        0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77,
        0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A,
        0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5,
        0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
        0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9,
        0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA,
        0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF,
        0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0x7B, 0x94,
        0x11, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xD9,
    ])
    return base64.b64encode(jpeg_bytes).decode("utf-8")


@pytest.fixture
def mock_api_response():
    """Mock a successful OpenRouter API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": (
                        "Chocolate Chip Cookies\n\n"
                        "Ingredients:\n"
                        "- 2 cups flour\n"
                        "- 1 cup butter\n"
                        "- 1 cup sugar\n"
                        "- 2 eggs\n"
                        "- 1 cup chocolate chips\n\n"
                        "Instructions:\n"
                        "1. Preheat oven to 375°F.\n"
                        "2. Mix flour and butter.\n"
                        "3. Add sugar and eggs.\n"
                        "4. Fold in chocolate chips.\n"
                        "5. Bake for 10 minutes."
                    )
                }
            }
        ],
        "usage": {
            "prompt_tokens": 1400,
            "completion_tokens": 100,
            "total_tokens": 1500,
        },
    }


# ── Unit Tests ────────────────────────────────────────────────────────────────

class TestOCRServiceInit:
    """Test OCR service initialization."""

    def test_init_with_api_key(self):
        service = OCRService(api_key="test-key")
        assert service.api_key == "test-key"

    def test_init_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
        service = OCRService()
        assert service.api_key == "env-key"

    def test_init_fails_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            OCRService()


class TestBuildImageContent:
    """Test _build_image_content method."""

    def test_with_url(self, ocr_service):
        result = ocr_service._build_image_content(None, None, "https://example.com/img.jpg")
        assert result["type"] == "image_url"
        assert result["image_url"]["url"] == "https://example.com/img.jpg"

    def test_with_base64_raw(self, ocr_service, sample_base64_image):
        result = ocr_service._build_image_content(None, sample_base64_image, None)
        assert result["type"] == "image_url"
        assert result["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_with_base64_data_uri(self, ocr_service, sample_base64_image):
        data_uri = f"data:image/png;base64,{sample_base64_image}"
        result = ocr_service._build_image_content(None, data_uri, None)
        assert result["image_url"]["url"] == data_uri

    def test_with_file_path(self, ocr_service, tmp_path):
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        result = ocr_service._build_image_content(str(img_file), None, None)
        assert result["type"] == "image_url"
        assert "data:image/jpeg;base64," in result["image_url"]["url"]

    def test_no_source_raises(self, ocr_service):
        with pytest.raises(ValueError, match="Provide"):
            ocr_service._build_image_content(None, None, None)

    def test_multiple_sources_raises(self, ocr_service, sample_base64_image):
        with pytest.raises(ValueError, match="only one"):
            ocr_service._build_image_content("/path", sample_base64_image, None)

    def test_missing_file_raises(self, ocr_service):
        with pytest.raises(ValueError, match="not found"):
            ocr_service._build_image_content("/nonexistent/image.jpg", None, None)


class TestGuessMime:
    """Test _guess_mime static method."""

    def test_jpg(self):
        assert OCRService._guess_mime(".jpg") == "image/jpeg"

    def test_jpeg(self):
        assert OCRService._guess_mime(".jpeg") == "image/jpeg"

    def test_png(self):
        assert OCRService._guess_mime(".png") == "image/png"

    def test_webp(self):
        assert OCRService._guess_mime(".webp") == "image/webp"

    def test_unknown_defaults_to_jpeg(self):
        assert OCRService._guess_mime(".bmp") == "image/jpeg"


class TestExtractText:
    """Test extract_text_from_image with mocked API."""

    @pytest.mark.asyncio
    async def test_successful_extraction(self, ocr_service, mock_api_response):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response

        with patch("recipe_scraper.services.ocr_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await ocr_service.extract_text_from_image(
                image_url="https://example.com/recipe.jpg"
            )

        assert "Chocolate Chip Cookies" in result
        assert "2 cups flour" in result
        assert "Preheat oven" in result

    @pytest.mark.asyncio
    async def test_api_error_raises(self, ocr_service):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("recipe_scraper.services.ocr_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="OCR API failed"):
                await ocr_service.extract_text_from_image(
                    image_url="https://example.com/recipe.jpg"
                )

    @pytest.mark.asyncio
    async def test_empty_choices_raises(self, ocr_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}

        with patch("recipe_scraper.services.ocr_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="unexpected response"):
                await ocr_service.extract_text_from_image(
                    image_url="https://example.com/recipe.jpg"
                )


# ── Fixtures path ─────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "recipe_images"


# ── Integration Tests (requires API key + fixture images) ─────────────────────

@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set — skipping integration test"
)
class TestOCRIntegration:
    """Integration tests that call the real OpenRouter API with local fixture images."""

    @pytest.mark.asyncio
    async def test_ocr_printed_recipe_mercotte(self):
        """Test OCR on a printed French recipe (Mercotte — Chamonix orange)."""
        image_path = FIXTURES_DIR / "mercotte-chamonix-orange.jpg"
        if not image_path.exists():
            pytest.skip(f"Fixture not found: {image_path}")

        service = OCRService()
        text = await service.extract_text_from_image(image_path=str(image_path))

        assert len(text) > 50, f"OCR returned too little text: {text}"
        text_lower = text.lower()
        # Should detect key recipe elements from the Mercotte recipe
        assert any(w in text_lower for w in ["mercotte", "biscuit", "chocolat", "orange", "marmelade"]), \
            f"OCR didn't extract expected recipe content: {text[:300]}"

    @pytest.mark.asyncio
    async def test_ocr_handwritten_recipe_ardoise(self):
        """Test OCR on a handwritten recipe on a blackboard."""
        image_path = FIXTURES_DIR / "handwritten-recipe-ardoise.jpg"
        if not image_path.exists():
            pytest.skip(f"Fixture not found: {image_path}")

        service = OCRService()
        text = await service.extract_text_from_image(image_path=str(image_path))

        assert len(text) > 30, f"OCR returned too little text: {text}"
        text_lower = text.lower()
        # The blackboard says "Recette d'une vie heureuse" with ingredients like "amour", "tendresse"
        assert any(w in text_lower for w in ["recette", "amour", "tendresse", "vie"]), \
            f"OCR didn't extract expected handwritten content: {text[:300]}"

    @pytest.mark.asyncio
    async def test_ocr_webp_recipe(self):
        """Test OCR on a webp recipe image."""
        image_path = FIXTURES_DIR / "recipe-web.webp"
        if not image_path.exists():
            pytest.skip(f"Fixture not found: {image_path}")

        service = OCRService()
        text = await service.extract_text_from_image(image_path=str(image_path))

        assert len(text) > 20, f"OCR returned too little text: {text}"

    @pytest.mark.asyncio
    async def test_ocr_from_base64(self):
        """Test OCR from base64-encoded image (simulates frontend upload)."""
        image_path = FIXTURES_DIR / "mercotte-chamonix-orange.jpg"
        if not image_path.exists():
            pytest.skip(f"Fixture not found: {image_path}")

        # Simulate what the frontend does: read file → base64 with data URI
        image_bytes = image_path.read_bytes()
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{b64}"

        service = OCRService()
        text = await service.extract_text_from_image(image_base64=data_uri)

        assert len(text) > 50, f"OCR from base64 returned too little text: {text}"
        assert "mercotte" in text.lower() or "chocolat" in text.lower() or "orange" in text.lower()
