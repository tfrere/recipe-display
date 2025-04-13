import pytest
from pathlib import Path
from web_scraper.scraper import WebScraper
from web_scraper.models import AuthPreset

# Chemin vers le fichier de presets d'authentification
AUTH_PRESETS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "auth_presets.json"
print(f"\nAuth presets path: {AUTH_PRESETS_PATH}")
print(f"Auth presets exists: {AUTH_PRESETS_PATH.exists()}")

@pytest.mark.asyncio
async def test_scrape_public_recipe():
    """Test scraping a public recipe."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://nutriciously.com/chili-sin-carne-vegan/"
    
    content = await scraper.scrape_url(url)
    
    assert content.title
    assert "vegan" in content.title.lower()
    assert content.image_urls
    assert all(url.startswith(("http://", "https://")) for url in content.image_urls)

@pytest.mark.asyncio
async def test_scrape_with_explicit_auth():
    """Test scraping a recipe with explicit authentication."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://books.ottolenghi.co.uk/simple/recipe/pea-zaatar-and-feta-fritters/"
    
    auth_preset = AuthPreset(
        type="cookie",
        domain=".books.ottolenghi.co.uk",
        values={
            "SSESSdcfc4c6f51fcab09b2179daf0e4cc999": "1005153519538ddfe6d1c0ef61bbbb5a"
        },
        description="Test Ottolenghi Auth"
    )
    
    content = await scraper.scrape_url(url, auth_preset=auth_preset)
    assert content.title
    assert "fritters" in content.title.lower()

@pytest.mark.asyncio
async def test_scrape_with_preset_auth():
    """Test scraping a recipe using authentication from presets file."""
    scraper = WebScraper(auth_presets_path=AUTH_PRESETS_PATH)
    url = "https://books.ottolenghi.co.uk/simple/recipe/pea-zaatar-and-feta-fritters/"
    
    # Debug info
    print(f"\nTesting URL: {url}")
    print(f"Auth presets path: {AUTH_PRESETS_PATH}")
    print(f"Auth presets exists: {AUTH_PRESETS_PATH.exists()}")
    
    # On n'a pas besoin de passer de preset, il sera chargé depuis auth_presets.json
    content = await scraper.scrape_url(url)
    
    # Debug info
    print(f"Got title: {content.title}")
    print(f"Content length: {len(content.main_content)}")
    
    assert content.title
    assert "fritters" in content.title.lower()
    assert content.main_content  # Vérifie qu'on a bien accès au contenu protégé

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
    url = "https://nutriciously.com/chili-sin-carne-vegan/"
    
    content = await scraper.scrape_url(url)
    
    assert content.image_urls
    for img_url in content.image_urls:
        assert img_url.startswith(("http://", "https://"))
        assert "nutriciously.com" in img_url 