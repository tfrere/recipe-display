import pytest
from recipe_generator import RecipeGenerator, WebContent
from unittest.mock import Mock, patch

@pytest.fixture
def generator():
    """Fixture pour créer un générateur avec une clé API mock."""
    return RecipeGenerator(api_key="fake-api-key")

@pytest.fixture
def mock_web_content():
    """Fixture pour créer un contenu web de test."""
    return WebContent(
        title="Aubergines farcies à l'agneau",
        main_content="""
        Ingredients:
        - 4 aubergines
        - 500g d'agneau haché
        - 2 oignons
        
        Instructions:
        1. Couper les aubergines
        2. Faire revenir l'agneau
        """,
        image_urls=["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
    )

@pytest.mark.asyncio
async def test_validation_error_detection(generator):
    """Test que le générateur détecte correctement une page non-recette."""
    web_content = WebContent(
        title="Login Required",
        main_content="Please log in to view this content",
        image_urls=[]
    )
    
    with patch.object(generator, '_stream_completion') as mock_completion:
        # Simuler une réponse de validation d'erreur
        mock_completion.return_value = "VALIDATION_ERROR\nThis appears to be a login page"
        
        with pytest.raises(ValueError) as exc_info:
            await generator._cleanup_recipe_content(web_content)
        
        assert "VALIDATION_ERROR" in str(exc_info.value)

@pytest.mark.asyncio
async def test_recipe_without_ingredients(generator):
    """Test qu'une recette sans ingrédients est rejetée."""
    web_content = WebContent(
        title="Recipe Without Ingredients",
        main_content="""
        Instructions:
        1. Mix everything together
        2. Cook until done
        """,
        image_urls=[]
    )
    
    with patch.object(generator, '_stream_completion') as mock_completion:
        mock_completion.return_value = "VALIDATION_ERROR\nNo ingredients list found in the recipe"
        
        with pytest.raises(ValueError) as exc_info:
            await generator._cleanup_recipe_content(web_content)
        
        assert "No ingredients" in str(exc_info.value)

@pytest.mark.asyncio
async def test_recipe_without_instructions(generator):
    """Test qu'une recette sans instructions est rejetée."""
    web_content = WebContent(
        title="Recipe Without Steps",
        main_content="""
        Ingredients:
        - 200g flour
        - 100g butter
        - 2 eggs
        """,
        image_urls=[]
    )
    
    with patch.object(generator, '_stream_completion') as mock_completion:
        mock_completion.return_value = "VALIDATION_ERROR\nNo cooking instructions or preparation steps found"
        
        with pytest.raises(ValueError) as exc_info:
            await generator._cleanup_recipe_content(web_content)
        
        assert "No cooking instructions" in str(exc_info.value)

@pytest.mark.asyncio
async def test_recipe_with_empty_sections(generator):
    """Test qu'une recette avec des sections vides est rejetée."""
    web_content = WebContent(
        title="Recipe With Empty Sections",
        main_content="""
        Ingredients:

        Instructions:
        """,
        image_urls=[]
    )
    
    with patch.object(generator, '_stream_completion') as mock_completion:
        mock_completion.return_value = "VALIDATION_ERROR\nRecipe sections are empty"
        
        with pytest.raises(ValueError) as exc_info:
            await generator._cleanup_recipe_content(web_content)
        
        assert "sections are empty" in str(exc_info.value)

@pytest.mark.asyncio
async def test_recipe_already_exists(generator):
    """Test que le générateur vérifie si une recette existe déjà."""
    url = "https://example.com/recipe"
    
    async def mock_exists_by_source_url(url):
        return True
    
    with patch('recipe_generator.storage.recipe_storage.RecipeStorage') as MockStorage:
        # Configurer le mock pour retourner une instance avec la méthode asynchrone
        mock_storage = Mock()
        mock_storage.exists_by_source_url = mock_exists_by_source_url
        MockStorage.return_value = mock_storage
        
        with pytest.raises(ValueError) as exc_info:
            await generator.generate_from_url(url)
        
        assert "existe déjà" in str(exc_info.value)

@pytest.mark.asyncio
async def test_successful_cleanup(generator, mock_web_content):
    """Test le nettoyage réussi d'une recette."""
    cleaned_response = """TITLE:
Aubergines farcies à l'agneau

INGREDIENTS:
- 4 aubergines
- 500g agneau haché
- 2 oignons

INSTRUCTIONS:
1. Couper les aubergines
2. Faire revenir l'agneau

SELECTED IMAGE URL:
https://example.com/image1.jpg"""

    with patch.object(generator, '_stream_completion') as mock_completion:
        mock_completion.return_value = cleaned_response
        
        result = await generator._cleanup_recipe_content(mock_web_content)
        
        assert result.title == mock_web_content.title
        assert result.selected_image_url == "https://example.com/image1.jpg"
        assert "INGREDIENTS" in result.main_content
        assert "INSTRUCTIONS" in result.main_content 