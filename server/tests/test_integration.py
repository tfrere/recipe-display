import pytest
import os
from recipe_generator import RecipeGenerator, WebContent
from dotenv import load_dotenv
import aiohttp
import tempfile
import shutil
from pathlib import Path

# Charger les variables d'environnement
load_dotenv()

@pytest.fixture
def generator():
    """Fixture pour créer un générateur avec une clé API mock."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY non définie")
    return RecipeGenerator(api_key=api_key)

@pytest.fixture
async def temp_dir():
    """Fixture pour créer un dossier temporaire."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_validation_error(generator, test_server):
    """Test la détection d'erreur avec un vrai appel à GPT."""
    url = f"http://localhost:{test_server.port}/recipes/blog"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
    
    web_content = WebContent(
        title="Blog de cuisine",
        main_content=content,
        image_urls=[]
    )
    
    with pytest.raises(ValueError) as exc_info:
        await generator._cleanup_recipe_content(web_content)
    
    assert "VALIDATION_ERROR" in str(exc_info.value)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_recipe_cleaning(generator, test_server):
    """Test le nettoyage d'une vraie recette avec GPT."""
    url = f"http://localhost:{test_server.port}/recipes/carbonara"
    image_urls = [
        f"http://localhost:{test_server.port}/images/carbonara1.jpg",
        f"http://localhost:{test_server.port}/images/carbonara2.jpg"
    ]
    
    # Vérifier que les images sont accessibles
    async with aiohttp.ClientSession() as session:
        # Récupérer le HTML
        async with session.get(url) as response:
            content = await response.text()
        
        # Vérifier les images
        for img_url in image_urls:
            async with session.head(img_url) as response:
                assert response.status == 200, f"L'image {img_url} n'est pas accessible"
    
    web_content = WebContent(
        title="Spaghetti Carbonara",
        main_content=content,
        image_urls=image_urls
    )
    
    result = await generator._cleanup_recipe_content(web_content)
    
    # Vérifier la structure de la réponse
    assert "INGREDIENTS:" in result.main_content
    assert "INSTRUCTIONS:" in result.main_content
    assert "spaghetti" in result.main_content.lower()
    assert "pancetta" in result.main_content.lower()
    
    # Vérifier que l'URL de l'image sélectionnée est valide
    assert result.selected_image_url in image_urls
    async with aiohttp.ClientSession() as session:
        async with session.head(result.selected_image_url) as response:
            assert response.status == 200

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_recipe_with_sub_recipes(generator, test_server):
    """Test le traitement d'une recette avec sous-recettes."""
    url = f"http://localhost:{test_server.port}/recipes/burger"
    image_url = f"http://localhost:{test_server.port}/images/burger.jpg"
    
    async with aiohttp.ClientSession() as session:
        # Récupérer le HTML
        async with session.get(url) as response:
            content = await response.text()
        
        # Vérifier l'image
        async with session.head(image_url) as response:
            assert response.status == 200
    
    web_content = WebContent(
        title="Burger maison et sa sauce",
        main_content=content,
        image_urls=[image_url]
    )
    
    result = await generator._cleanup_recipe_content(web_content)
    
    # Vérifier la structure avec sous-recettes
    assert "**For the sauce" in result.main_content
    assert "**For the burgers" in result.main_content
    assert "mayonnaise" in result.main_content.lower()
    assert "steak" in result.main_content.lower()
    
    # Vérifier que l'URL de l'image sélectionnée est valide
    assert result.selected_image_url == image_url

@pytest.mark.integration
@pytest.mark.asyncio
async def test_image_download_and_save(generator, test_server, temp_dir):
    """Test le téléchargement et la sauvegarde d'images."""
    svg_url = f"http://localhost:{test_server.port}/images/test-recipe.svg"
    jpg_url = f"http://localhost:{test_server.port}/images/test-recipe.jpg"
    
    # Configurer le générateur pour utiliser le dossier temporaire
    generator.storage.base_path = Path(temp_dir)
    generator.storage.recipes_path = generator.storage.base_path / "recipes"
    generator.storage.images_path = generator.storage.recipes_path / "images"
    generator.storage._ensure_directories()
    
    # Créer un slug de test
    test_slug = "test-recipe"
    
    # Tester le téléchargement des deux types d'images
    for url in [svg_url, jpg_url]:
        # Vérifier que l'image est accessible
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                assert response.status == 200
                content_type = response.headers.get('content-type', '')
                content = await response.read()
                print(f"\nRéponse du serveur :")
                print(f"Status : {response.status}")
                print(f"Content-Type : {content_type}")
                print(f"Taille du contenu : {len(content)} bytes")
        
        # Télécharger et sauvegarder l'image
        relative_path = await generator.storage._download_image(url, test_slug)
        print(f"\nChemin relatif retourné : {relative_path}")
        
        # Construire le chemin complet en utilisant le chemin relatif retourné
        full_path = os.path.join(temp_dir, "recipes", relative_path)
        print(f"Chemin complet attendu : {full_path}")
        print(f"Le fichier existe ? {os.path.exists(full_path)}")
        
        # Lister le contenu du dossier temporaire
        print("\nContenu du dossier temporaire :")
        for root, dirs, files in os.walk(temp_dir):
            print(f"\nDossier : {root}")
            for d in dirs:
                print(f"  Dir: {d}")
            for f in files:
                print(f"  File: {f}")
        
        # Vérifier que le fichier existe et n'est pas vide
        assert os.path.exists(full_path)
        assert os.path.getsize(full_path) > 0