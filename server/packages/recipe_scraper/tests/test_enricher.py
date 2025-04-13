import json
import pytest
from pathlib import Path

from recipe_scraper.recipe_enricher import RecipeEnricher

# Exemple de recette pour tester l'enrichissement
SAMPLE_RECIPE = {
    "metadata": {
        "title": "Salade de légumes avec temps de préparation",
        "slug": "salade-legumes-temps-preparation"
    },
    "ingredients": [
        {"name": "cucumber", "category": "produce", "quantity": "1", "unit": "piece"},
        {"name": "tomato", "category": "produce", "quantity": "2", "unit": "pieces"},
        {"name": "onion", "category": "produce", "quantity": "1", "unit": "piece"},
        {"name": "olive oil", "category": "oils", "quantity": "2", "unit": "tbsp"},
        {"name": "salt", "category": "spices", "quantity": "1", "unit": "tsp"},
        {"name": "pepper", "category": "spices", "quantity": "1/2", "unit": "tsp"}
    ],
    "steps": [
        {"id": "1", "text": "Chop all vegetables into small cubes", "time": "5min"},
        {"id": "2", "text": "Mix them in a bowl", "time": "2min"},
        {"id": "3", "text": "Add oil, salt and pepper", "time": "1min"},
        {"id": "4", "text": "Serve immediately", "time": "1min"}
    ]
}

# Exemple de recette avec sous-recettes
SAMPLE_RECIPE_WITH_SUBRECIPES = {
    "metadata": {
        "title": "Plat complexe avec sous-recettes",
        "slug": "plat-complexe-sous-recettes"
    },
    "ingredients": [
        {"name": "chicken", "category": "meat", "quantity": "500", "unit": "g"}
    ],
    "subRecipes": [
        {
            "name": "Marinade",
            "steps": [
                {"id": "1", "text": "Mélanger tous les ingrédients", "time": "5min"},
                {"id": "2", "text": "Laisser reposer", "time": "1h"}
            ]
        },
        {
            "name": "Cuisson",
            "steps": [
                {"id": "1", "text": "Préchauffer le four", "time": "10min"},
                {"id": "2", "text": "Cuire au four", "time": "30min"}
            ]
        }
    ]
}

def test_recipe_enricher_initialization():
    """Teste l'initialisation de l'enrichisseur de recettes"""
    enricher = RecipeEnricher()
    assert enricher is not None, "L'enrichisseur n'a pas été correctement initialisé"
    
    # Vérifier que les données saisonnières sont chargées
    assert enricher._seasonal_data is not None, "Les données saisonnières n'ont pas été chargées"
    assert "produce" in enricher._seasonal_data, "Les données de 'produce' sont manquantes"
    assert "vegetables" in enricher._seasonal_data["produce"], "Les données de légumes sont manquantes"
    assert "fruits" in enricher._seasonal_data["produce"], "Les données de fruits sont manquantes"

def test_parse_time_to_minutes():
    """Teste la conversion des chaînes de temps en minutes"""
    enricher = RecipeEnricher()
    
    # Tester différents formats de temps
    assert enricher._parse_time_to_minutes("5min") == 5.0
    assert enricher._parse_time_to_minutes("1h") == 60.0
    assert enricher._parse_time_to_minutes("1h30min") == 90.0
    assert enricher._parse_time_to_minutes("45 minutes") == 45.0
    assert enricher._parse_time_to_minutes("1 hour 15 minutes") == 75.0
    assert enricher._parse_time_to_minutes("") == 0.0
    assert enricher._parse_time_to_minutes(None) == 0.0

def test_calculate_total_time():
    """Teste le calcul du temps total d'une recette simple"""
    enricher = RecipeEnricher()
    
    # Calculer le temps total de la recette d'exemple
    total_time = enricher._calculate_total_time(SAMPLE_RECIPE)
    
    # Vérifier que le temps total est correct (5 + 2 + 1 + 1 = 9 minutes)
    assert total_time == 9.0, f"Le temps total calculé est incorrect: {total_time} (attendu: 9.0)"

def test_calculate_total_time_with_subrecipes():
    """Teste le calcul du temps total d'une recette avec sous-recettes"""
    enricher = RecipeEnricher()
    
    # Calculer le temps total de la recette avec sous-recettes
    total_time = enricher._calculate_total_time(SAMPLE_RECIPE_WITH_SUBRECIPES)
    
    # Vérifier que le temps total est correct (5 + 60 + 10 + 30 = 105 minutes)
    assert total_time == 105.0, f"Le temps total calculé est incorrect: {total_time} (attendu: 105.0)"

def test_determine_seasons():
    """Teste la détermination des saisons pour une recette"""
    enricher = RecipeEnricher()
    
    # Déterminer les saisons pour la recette d'exemple
    seasons, peak_months = enricher._determine_seasons(SAMPLE_RECIPE)
    
    # Vérifier que les saisons ont été déterminées
    assert seasons is not None, "Aucune saison n'a été déterminée"
    assert len(seasons) > 0, "La liste des saisons est vide"
    
    # Les concombres, tomates et oignons sont présents, donc la saison devrait être l'été
    assert "summer" in seasons, "La saison 'summer' n'a pas été identifiée alors que les légumes sont de saison en été"
    
    # Vérifier les mois de pic
    assert peak_months is not None, "Aucun mois de pic n'a été déterminé"
    assert len(peak_months) > 0, "La liste des mois de pic est vide"
    assert "July" in peak_months, "Le mois de Juillet n'a pas été identifié comme mois de pic"
    assert "August" in peak_months, "Le mois d'Août n'a pas été identifié comme mois de pic"

def test_determine_diets():
    """Teste la détermination des régimes alimentaires pour une recette"""
    enricher = RecipeEnricher()
    
    # Déterminer les régimes pour la recette d'exemple (végétarienne)
    diets = enricher._determine_diets(SAMPLE_RECIPE)
    
    # Vérifier que les régimes ont été déterminés correctement
    assert diets is not None, "Aucun régime alimentaire n'a été déterminé"
    assert len(diets) > 0, "La liste des régimes est vide"
    assert "vegan" in diets, "La recette devrait être identifiée comme végétalienne"
    assert "vegetarian" in diets, "La recette devrait être identifiée comme végétarienne"
    assert "omnivorous" in diets, "La recette devrait être identifiée comme omnivore"
    
    # Déterminer les régimes pour la recette avec viande
    diets_meat = enricher._determine_diets(SAMPLE_RECIPE_WITH_SUBRECIPES)
    
    # Vérifier que la recette avec viande est identifiée comme non végétarienne
    assert "omnivorous" in diets_meat, "La recette avec viande devrait être identifiée comme omnivore"
    assert "vegan" not in diets_meat, "La recette avec viande ne devrait pas être identifiée comme végétalienne"
    assert "vegetarian" not in diets_meat, "La recette avec viande ne devrait pas être identifiée comme végétarienne"

def test_enrich_recipe():
    """Teste l'enrichissement complet d'une recette"""
    enricher = RecipeEnricher()
    
    # Enrichir la recette d'exemple
    enriched_recipe = enricher.enrich_recipe(SAMPLE_RECIPE)
    
    # Vérifier que la recette a été enrichie
    assert enriched_recipe is not None, "La recette n'a pas été enrichie"
    assert "metadata" in enriched_recipe, "Les métadonnées sont manquantes dans la recette enrichie"
    
    # Vérifier les métadonnées ajoutées
    metadata = enriched_recipe["metadata"]
    assert "diets" in metadata, "Les régimes alimentaires sont manquants"
    assert "seasons" in metadata, "Les saisons sont manquantes"
    assert "totalTime" in metadata, "Le temps total est manquant"
    assert "totalCookingTime" in metadata, "Le temps de cuisson est manquant"
    
    # Vérifier que le temps total est correct
    assert metadata["totalTime"] == 9.0, f"Le temps total est incorrect: {metadata['totalTime']} (attendu: 9.0)"
    
    # Vérifier le temps de cuisson (qui pourrait être différent du temps total)
    assert isinstance(metadata["totalCookingTime"], (int, float)), "Le temps de cuisson n'est pas un nombre"
    
    # Vérifier que les données originales ont été préservées
    assert enriched_recipe["ingredients"] == SAMPLE_RECIPE["ingredients"], "Les ingrédients ont été modifiés"
    assert enriched_recipe["steps"] == SAMPLE_RECIPE["steps"], "Les étapes ont été modifiées"
    
    print(f"✅ Test réussi! Recette '{metadata['title']}' correctement enrichie")
    print(f"Temps total: {metadata['totalTime']} minutes")
    print(f"Temps de cuisson: {metadata['totalCookingTime']} minutes")
    print(f"Régimes: {', '.join(metadata['diets'])}")
    print(f"Saisons: {', '.join(metadata['seasons'])}")

if __name__ == "__main__":
    # Exécuter les tests manuellement si le script est lancé directement
    print("Exécution des tests de l'enrichisseur de recettes...\n")
    
    test_recipe_enricher_initialization()
    print("✓ Test d'initialisation réussi")
    
    test_parse_time_to_minutes()
    print("✓ Test de conversion de temps réussi")
    
    test_calculate_total_time()
    print("✓ Test de calcul du temps total réussi")
    
    test_calculate_total_time_with_subrecipes()
    print("✓ Test de calcul du temps total avec sous-recettes réussi")
    
    test_determine_seasons()
    print("✓ Test de détermination des saisons réussi")
    
    test_determine_diets()
    print("✓ Test de détermination des régimes alimentaires réussi")
    
    test_enrich_recipe() 