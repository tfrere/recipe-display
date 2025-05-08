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

# URL d'une recette avec image SVG à tester
SVG_IMAGE_TEST_URL = "https://books.ottolenghi.co.uk/cookbook/recipe/grilled-aubergine-and-lemon-soup-2/"

# Chemin vers le fichier d'authentification
AUTH_FILE = Path("data/auth_presets.json")

# Recette texte exemple pour les tests
TEST_RECIPE_TEXT = """
Salade simple

Ingrédients:
- 1 concombre
- 2 tomates
- 1 oignon
- Huile d'olive
- Sel
- Poivre

Préparation:
1. Coupez tous les légumes en petits dés
2. Mélangez-les dans un bol
3. Ajoutez l'huile, le sel et le poivre
4. Servez immédiatement

Image: https://example.com/salad.jpg
"""

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

@pytest.mark.asyncio
async def test_scrape_from_url_with_svg_image():
    """Teste la fonctionnalité de scraping d'URL pour une recette avec une image au format SVG"""
    # Créer les dossiers de sortie s'ils n'existent pas
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Initialiser le scraper
    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER
    
    # Charger les identifiants d'authentification
    auth_values = None
    if AUTH_FILE.exists():
        try:
            with open(AUTH_FILE, "r") as f:
                auth_presets = json.load(f)
            
            # Trouver les credentials pour ottolenghi.co.uk
            domain = "books.ottolenghi.co.uk"
            if domain in auth_presets:
                auth_values = auth_presets[domain]
                print(f"Authentification trouvée pour: {auth_values.get('domain')}")
        except json.JSONDecodeError:
            print(f"Erreur lors de la lecture du fichier d'authentification: {AUTH_FILE}")
    
    print("\n1. Test direct : Téléchargement d'une image SVG publique")
    public_svg_url = "https://books.ottolenghi.co.uk/wp-content/uploads/2021/05/default-recipe-cover-1.svg"
    public_slug = "test-public-svg-image"
    
    # Télécharger directement l'image SVG
    image_filename = await scraper._download_image(public_svg_url, public_slug)
    
    # Vérifier que l'image a été téléchargée
    assert image_filename is not None, "Échec du téléchargement de l'image SVG publique sans authentification"
    assert image_filename.endswith(".svg"), f"L'extension du fichier n'est pas .svg: {image_filename}"
    
    # Vérifier que le fichier existe et est valide
    image_path = TEST_IMAGE_OUTPUT_FOLDER / f"{public_slug}.svg"
    assert image_path.exists(), f"L'image SVG n'a pas été téléchargée: {image_path}"
    with open(image_path, "r") as f:
        content = f.read()
        assert "<svg" in content.lower(), "Le fichier téléchargé n'est pas un SVG valide"
    
    print("✅ Test direct réussi: Image SVG publique correctement téléchargée")
    
    # Test 2: Process complet d'une recette avec image SVG
    print("\n2. Test complet: Scraping d'une page avec image SVG")
    
    # Scraper la recette avec authentification si disponible
    recipe_data = await scraper.scrape_from_url(
        SVG_IMAGE_TEST_URL,
        auth_values=auth_values,
        progress_callback=mock_progress_callback
    )
    
    # Vérifier que des données ont été récupérées
    assert recipe_data, "Aucune donnée de recette n'a été récupérée"
    assert "metadata" in recipe_data, "Les métadonnées sont manquantes"
    
    # Vérifier que les métadonnées contiennent une URL d'image source
    metadata = recipe_data["metadata"]
    assert "sourceImageUrl" in metadata, "L'URL de l'image source est manquante dans les métadonnées"
    source_image_url = metadata["sourceImageUrl"]
    print(f"URL de l'image source trouvée: {source_image_url}")
    
    # Vérifier si l'URL termine par .svg
    assert source_image_url.lower().endswith(".svg"), f"L'URL de l'image ne correspond pas à un SVG: {source_image_url}"
    
    # Vérifier que l'image a été téléchargée et est présente
    assert "image" in metadata, "Le chemin de l'image téléchargée est manquant dans les métadonnées"
    image_path = metadata["image"]
    print(f"Chemin de l'image téléchargée: {image_path}")
    
    # Vérifier que le fichier existe et est au format SVG
    full_image_path = TEST_IMAGE_OUTPUT_FOLDER / Path(image_path).name
    assert full_image_path.exists(), f"L'image SVG n'a pas été téléchargée: {full_image_path}"
    assert full_image_path.suffix.lower() == ".svg", f"L'image n'est pas au format SVG: {full_image_path}"
    
    # Vérifier le contenu du fichier SVG
    with open(full_image_path, "r") as f:
        content = f.read()
        assert "<svg" in content.lower(), "Le fichier téléchargé n'est pas un SVG valide"
    
    print("✅ Test complet réussi: Recette avec image SVG correctement traitée")
    
    return True 

@pytest.mark.asyncio
async def test_scrape_from_text_duplicate_detection():
    """Teste la détection des doublons via similarité textuelle pour la méthode scrape_from_text."""
    # Créer les dossiers de sortie s'ils n'existent pas
    TEST_RECIPE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEST_IMAGE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Initialiser le scraper
    scraper = RecipeScraper()
    scraper._recipe_output_folder = TEST_RECIPE_OUTPUT_FOLDER
    scraper._image_output_folder = TEST_IMAGE_OUTPUT_FOLDER
    
    print("\n1. Création d'un fichier de recette factice avec le contenu original")
    
    # Créer un fichier de recette factice avec le contenu texte original
    fake_recipe_data = {
        "metadata": {
            "title": "Salade simple",
            "slug": "salade-simple",
            "originalContent": TEST_RECIPE_TEXT  # Le contenu original pour comparaison de similarité
        },
        "ingredients": [
            {"id": "ing1", "name": "cucumber", "category": "produce"},
            {"id": "ing2", "name": "tomatoes", "category": "produce"},
            {"id": "ing3", "name": "onion", "category": "produce"},
            {"id": "ing4", "name": "olive oil", "category": "condiment"},
            {"id": "ing5", "name": "salt", "category": "spice"},
            {"id": "ing6", "name": "pepper", "category": "spice"}
        ],
        "steps": [
            {"id": "step1", "action": "Cut the vegetables", "time": "5min"}
        ]
    }
    
    # Sauvegarder la recette factice
    recipe_file = TEST_RECIPE_OUTPUT_FOLDER / f"{fake_recipe_data['metadata']['slug']}.recipe.json"
    with open(recipe_file, "w") as f:
        json.dump(fake_recipe_data, f, indent=2)
    
    print(f"Recette factice créée: {recipe_file}")
    
    print("\n2. Test de similarité élevée: Tentative d'ajouter une recette avec un contenu très similaire")
    
    # Tenter d'ajouter une recette avec un contenu très similaire (quelques espaces et une majuscule en plus)
    duplicate_text = TEST_RECIPE_TEXT.replace("simple", "Simple").replace("concombre", "concombre ")
    duplicate_result = await scraper.scrape_from_text(
        duplicate_text,
        file_name="test-salad-duplicate.txt",
        progress_callback=mock_progress_callback
    )
    
    # Vérifier que la détection de similarité a fonctionné (retourne None)
    assert duplicate_result is None, "La détection par similarité n'a pas fonctionné, devrait retourner None"
    
    print(f"✅ Test réussi! Doublons par similarité correctement détectés (retourne None)")
    
    print("\n3. Test avec modification importante: Modification significative du texte de la recette")
    
    # Modifier significativement le texte (ajout d'une section complète)
    significantly_modified_text = TEST_RECIPE_TEXT + "\n\nVariation:\nVous pouvez ajouter des olives et du fromage feta pour une version méditerranéenne.\nSaupoudrez de persil frais avant de servir."
    
    # Tenter d'ajouter une recette avec un texte significativement modifié
    modified_result = await scraper.scrape_from_text(
        significantly_modified_text,
        file_name="test-salad-modified.txt",
        progress_callback=mock_progress_callback
    )
    
    # Cette recette devrait être considérée comme différente
    assert modified_result is not None, "La recette significativement modifiée a été incorrectement détectée comme doublon"
    assert "metadata" in modified_result, "Les métadonnées sont manquantes dans la recette modifiée"
    
    print("✅ Test réussi! Recette significativement modifiée correctement traitée comme distincte")
    
    # Nettoyer les fichiers de test
    try:
        recipe_file.unlink()
        print(f"Fichier de test nettoyé: {recipe_file}")
        # Nettoyer également la recette modifiée si elle a été créée
        if modified_result and "metadata" in modified_result and "slug" in modified_result["metadata"]:
            modified_file = TEST_RECIPE_OUTPUT_FOLDER / f"{modified_result['metadata']['slug']}.recipe.json"
            if modified_file.exists():
                modified_file.unlink()
                print(f"Fichier de test nettoyé: {modified_file}")
    except Exception as e:
        print(f"Erreur lors du nettoyage des fichiers de test: {e}")
    
    return True 