import pytest
import os
from web_scraper import WebContent
from web_scraper.scraper import WebScraper
from recipe_structurer.generator import generate_recipe
from dotenv import load_dotenv
import aiohttp
import tempfile
import shutil
from pathlib import Path

# Charger les variables d'environnement
load_dotenv()

@pytest.fixture
async def scraper():
    """Fixture pour créer un scraper."""
    return WebScraper()

@pytest.fixture
async def temp_dir():
    """Fixture pour créer un dossier temporaire."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_validation_error(scraper, test_server):
    """Test la détection d'erreur avec un vrai appel à GPT."""
    url = f"http://localhost:{test_server.port}/recipes/blog"
    
    with pytest.raises(ValueError) as exc_info:
        await scraper.scrape(url)
    
    assert "VALIDATION_ERROR" in str(exc_info.value)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_recipe_cleaning(scraper, test_server):
    """Test le nettoyage d'une vraie recette avec GPT."""
    url = f"http://localhost:{test_server.port}/recipes/carbonara"
    
    # Scraper la recette
    content = await scraper.scrape(url)
    
    # Vérifier la structure de base
    assert content.title
    assert "carbonara" in content.title.lower()
    assert content.main_content
    assert content.image_urls
    
    # Structurer la recette
    cleaned_text, recipe_base, recipe_graph = await generate_recipe(content.main_content)
    
    # Vérifier la structure de la recette
    assert recipe_base.metadata.title
    assert recipe_base.ingredients
    assert "spaghetti" in [ing.name.lower() for ing in recipe_base.ingredients]
    assert "pancetta" in [ing.name.lower() for ing in recipe_base.ingredients]
    assert recipe_graph.steps
    assert recipe_graph.final_state

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_recipe_with_sub_recipes(scraper, test_server):
    """Test le traitement d'une recette avec sous-recettes."""
    url = f"http://localhost:{test_server.port}/recipes/burger"
    
    # Scraper la recette
    content = await scraper.scrape(url)
    
    # Vérifier la structure de base
    assert content.title
    assert "burger" in content.title.lower()
    assert content.main_content
    assert content.image_urls
    
    # Structurer la recette
    cleaned_text, recipe_base, recipe_graph = await generate_recipe(content.main_content)
    
    # Vérifier la structure de la recette
    assert recipe_base.metadata.title
    assert recipe_base.ingredients
    assert "steak" in [ing.name.lower() for ing in recipe_base.ingredients]
    assert recipe_graph.steps
    assert recipe_graph.final_state
    
    # Vérifier les sous-recettes dans le texte nettoyé
    assert "**For the sauce" in cleaned_text
    assert "**For the burgers" in cleaned_text
    assert "mayonnaise" in cleaned_text.lower()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_image_download_and_save(scraper, test_server, temp_dir):
    """Test le téléchargement et la sauvegarde d'images."""
    url = f"http://localhost:{test_server.port}/recipes/carbonara"
    
    # Scraper la recette
    content = await scraper.scrape(url)
    
    # Vérifier que nous avons des images
    assert content.image_urls
    
    # Vérifier que les images sont accessibles
    async with aiohttp.ClientSession() as session:
        for img_url in content.image_urls:
            async with session.head(img_url) as response:
                assert response.status == 200
                assert response.headers.get('content-type', '').startswith('image/')