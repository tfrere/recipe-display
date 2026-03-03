import pytest
from pathlib import Path
from web_scraper.scraper import WebScraper
from web_scraper.models import AuthPreset

AUTH_PRESETS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "auth_presets.json"


@pytest.mark.asyncio
async def test_scrape_public_recipe():
    """Test scraping a public recipe."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://cookieandkate.com/best-lentil-soup-recipe/"

    content = await scraper.scrape_url(url)

    assert content.title
    assert content.image_urls
    assert all(u.startswith(("http://", "https://")) for u in content.image_urls)


@pytest.mark.asyncio
async def test_scrape_with_explicit_auth():
    """Test scraping with explicit authentication (uses placeholder credentials)."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://cookieandkate.com/best-lentil-soup-recipe/"

    auth_preset = AuthPreset(
        type="cookie",
        domain=".cookieandkate.com",
        values={"test_cookie": "placeholder_value"},
        description="Test Auth",
    )

    content = await scraper.scrape_url(url, auth_preset=auth_preset)
    assert content.title


@pytest.mark.asyncio
async def test_invalid_url():
    """Test scraping an invalid URL."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://nonexistent-recipe-site.com/recipe"

    with pytest.raises(ValueError):
        await scraper.scrape_url(url)


@pytest.mark.asyncio
async def test_image_extraction():
    """Test image URL extraction and normalization."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://cookieandkate.com/best-lentil-soup-recipe/"

    content = await scraper.scrape_url(url)

    assert content.image_urls
    for img_url in content.image_urls:
        assert img_url.startswith(("http://", "https://"))
