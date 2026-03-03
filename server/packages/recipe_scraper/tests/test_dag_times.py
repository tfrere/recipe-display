"""Tests for DAG-based time calculation (enrichment.times module).

These tests validate the critical path algorithm that computes
totalTime, totalActiveTime, and totalPassiveTime from the recipe
step graph.
"""

import pytest

from recipe_scraper.enrichment.times import (
    _parse_time_to_minutes,
    _minutes_to_iso8601,
    calculate_times_from_dag,
)


# ── Fixture recipes ──────────────────────────────────────────────────

LINEAR_RECIPE = {
    "metadata": {"title": "Linear recipe"},
    "ingredients": [
        {"id": "flour", "name": "flour", "quantity": 200, "unit": "g"},
        {"id": "sugar", "name": "sugar", "quantity": 100, "unit": "g"},
    ],
    "steps": [
        {"id": "mix", "action": "Mix flour and sugar", "stepType": "combine",
         "duration": "PT5M", "uses": ["flour", "sugar"], "produces": "batter"},
        {"id": "bake", "action": "Bake", "stepType": "cook",
         "duration": "PT30M", "isPassive": True, "uses": ["batter"], "produces": "cake"},
        {"id": "cool", "action": "Cool", "stepType": "prep",
         "duration": "PT10M", "isPassive": True, "uses": ["cake"], "produces": "cooled_cake"},
    ],
    "finalState": "cooled_cake",
}

PARALLEL_RECIPE = {
    "metadata": {"title": "Parallel recipe"},
    "ingredients": [
        {"id": "chicken", "name": "chicken", "quantity": 500, "unit": "g"},
        {"id": "onion", "name": "onion", "quantity": 2, "unit": "piece"},
        {"id": "cream", "name": "cream", "quantity": 200, "unit": "ml"},
    ],
    "steps": [
        {"id": "season", "action": "Season chicken", "stepType": "prep",
         "duration": "PT5M", "uses": ["chicken"], "produces": "seasoned_chicken"},
        {"id": "cook_chicken", "action": "Cook chicken", "stepType": "cook",
         "duration": "PT20M", "isPassive": True, "uses": ["seasoned_chicken"],
         "produces": "cooked_chicken"},
        {"id": "chop_onion", "action": "Chop onion", "stepType": "prep",
         "duration": "PT10M", "uses": ["onion"], "produces": "chopped_onion"},
        {"id": "make_sauce", "action": "Make sauce", "stepType": "cook",
         "duration": "PT15M", "uses": ["chopped_onion", "cream"],
         "produces": "sauce"},
        {"id": "assemble", "action": "Assemble", "stepType": "serve",
         "duration": "PT5M", "uses": ["cooked_chicken", "sauce"],
         "produces": "plated_dish"},
    ],
    "finalState": "plated_dish",
}

NO_DURATION_RECIPE = {
    "metadata": {"title": "No duration recipe"},
    "ingredients": [
        {"id": "tomato", "name": "tomato", "quantity": 3, "unit": "piece"},
    ],
    "steps": [
        {"id": "chop", "action": "Chop tomatoes", "stepType": "prep",
         "uses": ["tomato"], "produces": "chopped_tomato"},
        {"id": "serve", "action": "Serve", "stepType": "serve",
         "uses": ["chopped_tomato"], "produces": "salad"},
    ],
    "finalState": "salad",
}

PREHEAT_RECIPE = {
    "metadata": {"title": "Preheat recipe"},
    "ingredients": [
        {"id": "dough", "name": "dough", "quantity": 500, "unit": "g"},
    ],
    "steps": [
        {"id": "preheat", "action": "Preheat the oven to 200°C", "stepType": "prep",
         "uses": [], "produces": "preheated_oven"},
        {"id": "shape", "action": "Shape dough", "stepType": "prep",
         "duration": "PT10M", "uses": ["dough"], "produces": "shaped_dough"},
        {"id": "bake", "action": "Bake", "stepType": "cook",
         "duration": "PT25M", "isPassive": True,
         "uses": ["shaped_dough"], "requires": ["preheated_oven"],
         "produces": "bread"},
    ],
    "finalState": "bread",
}

PASSIVE_HEAVY_RECIPE = {
    "metadata": {"title": "Cheesecake (long rest)"},
    "ingredients": [
        {"id": "cream_cheese", "name": "cream cheese", "quantity": 500, "unit": "g"},
        {"id": "sugar", "name": "sugar", "quantity": 100, "unit": "g"},
    ],
    "steps": [
        {"id": "mix", "action": "Mix all", "stepType": "combine",
         "duration": "PT10M", "uses": ["cream_cheese", "sugar"], "produces": "batter"},
        {"id": "bake", "action": "Bake", "stepType": "cook",
         "duration": "PT45M", "isPassive": True, "uses": ["batter"], "produces": "baked"},
        {"id": "cool", "action": "Cool in fridge", "stepType": "prep",
         "duration": "PT24H", "isPassive": True, "uses": ["baked"], "produces": "cheesecake"},
    ],
    "finalState": "cheesecake",
}


# ── Tests ────────────────────────────────────────────────────────────


class TestMinutesToISO8601:

    def test_zero(self):
        assert _minutes_to_iso8601(0) == "PT0M"

    def test_minutes_only(self):
        assert _minutes_to_iso8601(45) == "PT45M"

    def test_hours_only(self):
        assert _minutes_to_iso8601(120) == "PT2H"

    def test_hours_and_minutes(self):
        assert _minutes_to_iso8601(90) == "PT1H30M"

    def test_large_value(self):
        assert _minutes_to_iso8601(1440) == "PT24H"


class TestDAGLinearPath:

    def test_total_time(self):
        result = calculate_times_from_dag(LINEAR_RECIPE)
        assert result["totalTimeMinutes"] == 45.0

    def test_active_time(self):
        result = calculate_times_from_dag(LINEAR_RECIPE)
        assert result["totalActiveTimeMinutes"] == 5.0

    def test_passive_time(self):
        result = calculate_times_from_dag(LINEAR_RECIPE)
        assert result["totalPassiveTimeMinutes"] == 40.0

    def test_active_plus_passive_equals_total(self):
        result = calculate_times_from_dag(LINEAR_RECIPE)
        assert (
            result["totalActiveTimeMinutes"] + result["totalPassiveTimeMinutes"]
            == result["totalTimeMinutes"]
        )

    def test_iso_format(self):
        result = calculate_times_from_dag(LINEAR_RECIPE)
        assert result["totalTime"] == "PT45M"


class TestDAGParallelBranches:

    def test_total_time_is_critical_path(self):
        result = calculate_times_from_dag(PARALLEL_RECIPE)
        assert result["totalTimeMinutes"] == 30.0

    def test_total_is_less_than_linear_sum(self):
        result = calculate_times_from_dag(PARALLEL_RECIPE)
        assert result["totalTimeMinutes"] < 55


class TestDAGFallbackDuration:

    def test_steps_get_5min_fallback(self):
        result = calculate_times_from_dag(NO_DURATION_RECIPE)
        assert result["totalTimeMinutes"] == 10.0

    def test_preheat_gets_zero_fallback(self):
        result = calculate_times_from_dag(PREHEAT_RECIPE)
        assert result["totalTimeMinutes"] == 35.0


class TestDAGPassiveHeavy:

    def test_long_passive_dominates(self):
        result = calculate_times_from_dag(PASSIVE_HEAVY_RECIPE)
        assert result["totalTimeMinutes"] == 1495.0

    def test_active_time_is_small(self):
        result = calculate_times_from_dag(PASSIVE_HEAVY_RECIPE)
        assert result["totalActiveTimeMinutes"] == 10.0

    def test_passive_time_is_large(self):
        result = calculate_times_from_dag(PASSIVE_HEAVY_RECIPE)
        assert result["totalPassiveTimeMinutes"] == 1485.0


class TestDAGEdgeCases:

    def test_empty_steps_returns_fallback(self):
        recipe = {"metadata": {"title": "Empty"}, "steps": []}
        result = calculate_times_from_dag(recipe)
        assert result["totalTimeMinutes"] == 0.0

    def test_no_steps_key_returns_fallback(self):
        recipe = {"metadata": {"title": "No steps"}}
        result = calculate_times_from_dag(recipe)
        assert result["totalTimeMinutes"] == 0.0

    def test_single_step(self):
        recipe = {
            "metadata": {"title": "Single step"},
            "ingredients": [{"id": "egg", "name": "egg"}],
            "steps": [
                {"id": "boil", "action": "Boil egg", "stepType": "cook",
                 "duration": "PT10M", "uses": ["egg"], "produces": "boiled_egg"}
            ],
            "finalState": "boiled_egg",
        }
        result = calculate_times_from_dag(recipe)
        assert result["totalTimeMinutes"] == 10.0


class TestParseTimeFormats:

    @pytest.mark.parametrize("input_str, expected", [
        ("PT30M", 30.0),
        ("PT1H", 60.0),
        ("PT1H30M", 90.0),
        ("PT24H", 1440.0),
        ("5min", 5.0),
        ("1h30min", 90.0),
        ("45 minutes", 45.0),
        ("1 hour 15 minutes", 75.0),
        ("", 0.0),
        (None, 0.0),
    ])
    def test_parse_formats(self, input_str, expected):
        assert _parse_time_to_minutes(input_str) == expected
