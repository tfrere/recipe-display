import asyncio
import os
import json
import pytest
from pathlib import Path

from recipe_scraper.scraper import RecipeScraper

# Chemins vers les dossiers de sortie des tests
TEST_RECIPE_OUTPUT_FOLDER = Path("data/recipes")
TEST_IMAGE_OUTPUT_FOLDER = Path("data/recipes/images")

# URL d'une recette à tester
TEST_URL = "https://books.ottolenghi.co.uk/simple/recipe/chopped-salad-with-tahini-and-zaatar/"

# Chemin vers le fichier d'authentification
AUTH_FILE = Path("data/auth_presets.json")

# Créer un callback pour capturer les messages de progression
async def mock_progress_callback(message):
    """Capture les messages de progression"""
    print(f"PROGRESS: {message}")

@pytest.mark.asyncio
async def test_scrape_from_url_no_auth():
    """
    Teste la fonctionnalité de scraping d'URL pour une recette sans authentification.
    Ce test doit échouer car la page nécessite une authentification.
    """
    # Créer les dossiers de sortie s'ils n'existent pas
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Initialiser le scraper
    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER
    
    # Scraper la recette sans auth
    recipe_data = await scraper.scrape_from_url(
        TEST_URL,
        auth_values=None,
        progress_callback=mock_progress_callback
    )
    
    # Nous nous attendons à ce que recipe_data soit vide ou que le scraping échoue
    # en raison du manque d'authentification
    assert not recipe_data or len(recipe_data) == 0, "Le scraping sans authentification a réussi, ce qui n'était pas attendu"
    
    print("✅ Test réussi! Échec attendu du scraping sans authentification")

@pytest.mark.asyncio
async def test_scrape_from_url_with_auth():
    """Teste la fonctionnalité de scraping d'URL pour une recette avec authentification"""
    # Créer les dossiers de sortie s'ils n'existent pas
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Initialiser le scraper
    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER
    
    # Charger les identifiants d'authentification
    if not AUTH_FILE.exists():
        pytest.skip(f"Fichier d'authentification non trouvé: {AUTH_FILE}")
    
    try:
        with open(AUTH_FILE, "r") as f:
            auth_presets = json.load(f)
    except json.JSONDecodeError:
        pytest.skip(f"Erreur lors de la lecture du fichier d'authentification: {AUTH_FILE}")
    
    # Trouver les credentials pour ottolenghi.co.uk
    domain = "books.ottolenghi.co.uk"
    if domain not in auth_presets:
        pytest.skip(f"Aucun identifiant trouvé pour le domaine {domain}")
    
    auth_values = auth_presets[domain]
    print(f"Utilisation des credentials pour: {auth_values.get('domain')}")
    
    # Scraper la recette avec authentification
    recipe_data = await scraper.scrape_from_url(
        TEST_URL,
        auth_values=auth_values,
        progress_callback=mock_progress_callback
    )
    
    # Vérifier que des données ont été récupérées
    assert recipe_data, "Aucune donnée de recette n'a été récupérée malgré l'authentification"
    
    # Vérifier la structure des données
    assert "metadata" in recipe_data, "Les métadonnées sont manquantes"
    assert "ingredients" in recipe_data, "Les ingrédients sont manquants"
    assert "steps" in recipe_data, "Les étapes sont manquantes"
    
    # Vérifier les champs de métadonnées essentiels
    metadata = recipe_data["metadata"]
    assert "title" in metadata, "Le titre est manquant"
    assert metadata["title"], "Le titre est vide"
    assert "slug" in metadata, "Le slug est manquant"
    assert metadata["slug"], "Le slug est vide"
    
    # Vérifier que le fichier de recette a été enregistré
    expected_recipe_file = TEST_RECIPE_OUTPUT_FOLDER / f"{metadata['slug']}.recipe.json"
    assert expected_recipe_file.exists(), f"Le fichier de recette n'a pas été créé: {expected_recipe_file}"
    
    # Vérifier que l'image a été téléchargée si une URL d'image est présente
    if "sourceImageUrl" in metadata and metadata["sourceImageUrl"]:
        image_path = TEST_IMAGE_OUTPUT_FOLDER / f"{metadata['slug']}.jpg"
        assert image_path.exists() or (TEST_IMAGE_OUTPUT_FOLDER / f"{metadata['slug']}.png").exists() or \
               (TEST_IMAGE_OUTPUT_FOLDER / f"{metadata['slug']}.webp").exists(), \
               "L'image de la recette n'a pas été téléchargée"
    
    # Vérifier les données d'enrichissement
    assert "diets" in metadata, "Les régimes alimentaires sont manquants"
    assert "seasons" in metadata, "Les saisons sont manquantes"
    
    print(f"✅ Test réussi! Recette '{metadata['title']}' correctement scraped avec authentification")
    
    # Retourner les données pour une inspection manuelle si nécessaire
    return recipe_data 