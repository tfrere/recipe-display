import json
import pytest
from pathlib import Path

from recipe_scraper.recipe_enricher import RecipeEnricher

# Sample recipe with DAG-format steps (action, duration, uses, produces)
SAMPLE_RECIPE = {
    "metadata": {
        "title": "Salade de légumes avec temps de préparation",
        "slug": "salade-legumes-temps-preparation"
    },
    "ingredients": [
        {"id": "cucumber", "name": "cucumber", "category": "produce", "quantity": "1", "unit": "piece"},
        {"id": "tomato", "name": "tomato", "category": "produce", "quantity": "2", "unit": "pieces"},
        {"id": "onion", "name": "onion", "category": "produce", "quantity": "1", "unit": "piece"},
        {"id": "olive_oil", "name": "olive oil", "category": "oils", "quantity": "2", "unit": "tbsp"},
        {"id": "salt", "name": "salt", "category": "spices", "quantity": "1", "unit": "tsp"},
        {"id": "pepper", "name": "pepper", "category": "spices", "quantity": "0.5", "unit": "tsp"},
    ],
    "steps": [
        {
            "id": "s1",
            "action": "Chop all vegetables into small cubes",
            "duration": "PT5M",
            "uses": ["cucumber", "tomato", "onion"],
            "produces": "chopped_vegetables",
        },
        {
            "id": "s2",
            "action": "Mix them in a bowl",
            "duration": "PT2M",
            "uses": ["chopped_vegetables"],
            "produces": "mixed_salad",
        },
        {
            "id": "s3",
            "action": "Add oil, salt and pepper",
            "duration": "PT1M",
            "uses": ["mixed_salad", "olive_oil", "salt", "pepper"],
            "produces": "dressed_salad",
        },
        {
            "id": "s4",
            "action": "Serve immediately",
            "duration": "PT1M",
            "uses": ["dressed_salad"],
            "produces": "final_salad",
        },
    ],
    "finalState": "final_salad",
}

# Recipe with passive steps to test active/passive split
SAMPLE_RECIPE_WITH_PASSIVE = {
    "metadata": {
        "title": "Plat complexe avec repos",
        "slug": "plat-complexe-repos"
    },
    "ingredients": [
        {"id": "chicken", "name": "chicken", "category": "meat", "quantity": "500", "unit": "g"},
        {"id": "marinade_spices", "name": "spices", "category": "spices", "quantity": "2", "unit": "tbsp"},
    ],
    "steps": [
        {
            "id": "s1",
            "action": "Mélanger les ingrédients de la marinade",
            "duration": "PT5M",
            "uses": ["chicken", "marinade_spices"],
            "produces": "marinated_chicken",
        },
        {
            "id": "s2",
            "action": "Laisser reposer au frigo",
            "duration": "PT1H",
            "isPassive": True,
            "uses": ["marinated_chicken"],
            "produces": "rested_chicken",
        },
        {
            "id": "s3",
            "action": "Préchauffer le four",
            "duration": "PT10M",
            "isPassive": True,
            "uses": [],
            "produces": "hot_oven",
        },
        {
            "id": "s4",
            "action": "Cuire au four",
            "duration": "PT30M",
            "isPassive": True,
            "uses": ["rested_chicken", "hot_oven"],
            "produces": "cooked_chicken",
        },
    ],
    "finalState": "cooked_chicken",
}


def test_recipe_enricher_initialization():
    """Test l'initialisation de l'enrichisseur de recettes."""
    enricher = RecipeEnricher()
    assert enricher is not None

    assert enricher._seasonal_data is not None
    assert "produce" in enricher._seasonal_data
    assert "vegetables" in enricher._seasonal_data["produce"]
    assert "fruits" in enricher._seasonal_data["produce"]


def test_parse_time_to_minutes():
    """Test la conversion des chaînes de temps en minutes."""
    enricher = RecipeEnricher()

    assert enricher._parse_time_to_minutes("5min") == 5.0
    assert enricher._parse_time_to_minutes("1h") == 60.0
    assert enricher._parse_time_to_minutes("1h30min") == 90.0
    assert enricher._parse_time_to_minutes("45 minutes") == 45.0
    assert enricher._parse_time_to_minutes("1 hour 15 minutes") == 75.0
    assert enricher._parse_time_to_minutes("") == 0.0
    assert enricher._parse_time_to_minutes(None) == 0.0


def test_parse_iso8601_duration():
    """Test le parsing de durées ISO 8601."""
    enricher = RecipeEnricher()

    assert enricher._parse_iso8601_duration("PT5M") == 5.0
    assert enricher._parse_iso8601_duration("PT1H") == 60.0
    assert enricher._parse_iso8601_duration("PT1H30M") == 90.0
    assert enricher._parse_iso8601_duration("PT45M") == 45.0
    assert enricher._parse_iso8601_duration("PT30S") == 0.5


def test_minutes_to_iso8601():
    """Test la conversion minutes vers ISO 8601."""
    enricher = RecipeEnricher()

    assert enricher._minutes_to_iso8601(0) == "PT0M"
    assert enricher._minutes_to_iso8601(5) == "PT5M"
    assert enricher._minutes_to_iso8601(60) == "PT1H"
    assert enricher._minutes_to_iso8601(90) == "PT1H30M"
    assert enricher._minutes_to_iso8601(125) == "PT2H5M"


def test_calculate_times_from_dag_linear():
    """Test le calcul des temps via DAG pour une recette linéaire."""
    enricher = RecipeEnricher()

    time_info = enricher._calculate_times_from_dag(SAMPLE_RECIPE)

    # Linear chain: 5 + 2 + 1 + 1 = 9 minutes
    assert time_info["totalTimeMinutes"] == 9.0
    # All steps are active (no isPassive)
    assert time_info["totalActiveTimeMinutes"] == 9.0
    assert time_info["totalPassiveTimeMinutes"] == 0.0
    # ISO 8601 format
    assert time_info["totalTime"] == "PT9M"
    assert time_info["totalActiveTime"] == "PT9M"
    assert time_info["totalPassiveTime"] == "PT0M"


def test_calculate_times_from_dag_with_passive():
    """Test le calcul des temps avec étapes passives et branches parallèles."""
    enricher = RecipeEnricher()

    time_info = enricher._calculate_times_from_dag(SAMPLE_RECIPE_WITH_PASSIVE)

    # Critical path: s1 (5min) -> s2 (60min) -> s4 (30min) = 95 min
    # s3 (10min, preheat) runs in parallel, finishes before s4 starts
    assert time_info["totalTimeMinutes"] == 95.0

    # Active on critical path: s1 (5min, active)
    # Passive on critical path: s2 (60min) + s4 (30min) = 90min
    assert time_info["totalActiveTimeMinutes"] == 5.0
    assert time_info["totalPassiveTimeMinutes"] == 90.0


def test_calculate_times_linear_fallback():
    """Test le fallback linéaire quand pas de DAG."""
    enricher = RecipeEnricher()

    recipe_no_dag = {
        "metadata": {"title": "Simple"},
        "steps": [
            {"id": "1", "duration": "PT10M"},
            {"id": "2", "duration": "PT20M", "isPassive": True},
            {"id": "3", "duration": "PT5M"},
        ],
    }
    time_info = enricher._calculate_times_linear_fallback(recipe_no_dag)

    assert time_info["totalTimeMinutes"] == 35.0
    assert time_info["totalActiveTimeMinutes"] == 15.0
    assert time_info["totalPassiveTimeMinutes"] == 20.0


def test_determine_seasons():
    """Test la détermination des saisons pour une recette."""
    enricher = RecipeEnricher()

    seasons, peak_months = enricher._determine_seasons(SAMPLE_RECIPE)

    assert seasons is not None
    assert len(seasons) > 0
    assert "summer" in seasons
    assert peak_months is not None
    assert len(peak_months) > 0


def test_determine_diets():
    """Test la détermination des régimes alimentaires."""
    enricher = RecipeEnricher()

    # Vegetable salad => vegan + vegetarian + omnivorous
    diets = enricher._determine_diets(SAMPLE_RECIPE)
    assert "vegan" in diets
    assert "vegetarian" in diets
    assert "omnivorous" in diets

    # Chicken recipe => omnivorous only
    diets_meat = enricher._determine_diets(SAMPLE_RECIPE_WITH_PASSIVE)
    assert "omnivorous" in diets_meat
    assert "vegan" not in diets_meat
    assert "vegetarian" not in diets_meat


def test_enrich_recipe():
    """Test l'enrichissement complet d'une recette (synchrone, sans nutrition)."""
    enricher = RecipeEnricher()

    enriched = enricher.enrich_recipe(SAMPLE_RECIPE)

    assert enriched is not None
    metadata = enriched["metadata"]

    # Diet and season enrichment
    assert "diets" in metadata
    assert "seasons" in metadata

    # DAG-computed times (ISO 8601)
    assert "totalTime" in metadata
    assert "totalActiveTime" in metadata
    assert "totalPassiveTime" in metadata
    assert metadata["totalTime"] == "PT9M"

    # Float minutes for frontend
    assert "totalTimeMinutes" in metadata
    assert metadata["totalTimeMinutes"] == 9.0

    # Legacy field removed
    assert "totalCookingTime" not in metadata

    # Original data preserved
    assert enriched["ingredients"] == SAMPLE_RECIPE["ingredients"]
    assert enriched["steps"] == SAMPLE_RECIPE["steps"]
