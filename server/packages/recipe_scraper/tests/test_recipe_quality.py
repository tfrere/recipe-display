"""Post-import recipe quality tests.

Run after an import batch to validate every .recipe.json in the output
directory. These are deterministic checks — no LLM calls, no network.

Usage:
    cd server/packages/recipe_scraper
    poetry run pytest tests/test_recipe_quality.py -v

The tests load all recipes from the default data directory and validate
schema integrity, DAG correctness, ingredient completeness, and time
coherence. If no recipes exist, the entire module is skipped.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ── Configuration ────────────────────────────────────────────────────

RECIPES_DIR = Path(__file__).resolve().parents[4] / "server" / "data" / "recipes"
ISO_8601_DURATION_RE = re.compile(r"^PT(\d+H)?(\d+M)?$")

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_RECIPE_TYPES = {"appetizer", "starter", "main_course", "dessert", "drink", "base"}
VALID_STEP_TYPES = {"prep", "combine", "cook", "rest", "serve"}
VALID_CATEGORIES = {
    "meat", "poultry", "seafood", "produce", "dairy", "egg",
    "grain", "legume", "nuts_seeds", "oil", "herb",
    "pantry", "spice", "condiment", "beverage", "other",
}
VALID_DIETS = {"vegan", "vegetarian", "pescatarian", "omnivorous", "gluten-free"}
VALID_SEASONS = {"spring", "summer", "autumn", "winter", "all"}


# ── Helpers ──────────────────────────────────────────────────────────


def _load_recipes() -> List[Dict[str, Any]]:
    """Load all .recipe.json files from the recipes directory."""
    if not RECIPES_DIR.exists():
        return []
    files = sorted(RECIPES_DIR.glob("*.recipe.json"))
    recipes = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
            data["_filepath"] = str(f)
            recipes.append(data)
    return recipes


ALL_RECIPES = _load_recipes()

if not ALL_RECIPES:
    pytest.skip("No recipes found — skipping quality tests", allow_module_level=True)


def recipe_ids():
    """Generate readable test IDs from recipe titles."""
    return [r.get("metadata", {}).get("title", "?")[:50] for r in ALL_RECIPES]


# ── Test classes ─────────────────────────────────────────────────────


class TestSchemaIntegrity:
    """Validate that every recipe has the required top-level structure."""

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_metadata(self, recipe):
        assert "metadata" in recipe, "Missing 'metadata' key"
        meta = recipe["metadata"]
        assert isinstance(meta.get("title"), str) and meta["title"], "metadata.title must be a non-empty string"
        assert isinstance(meta.get("description"), str), "metadata.description must be a string"
        assert isinstance(meta.get("servings"), int) and meta["servings"] > 0, "metadata.servings must be > 0"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_ingredients(self, recipe):
        ingredients = recipe.get("ingredients", [])
        assert isinstance(ingredients, list) and len(ingredients) >= 1, "Must have at least 1 ingredient"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_steps(self, recipe):
        steps = recipe.get("steps", [])
        assert isinstance(steps, list) and len(steps) >= 2, "Must have at least 2 steps"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_final_state(self, recipe):
        assert isinstance(recipe.get("finalState"), str) and recipe["finalState"], \
            "Must have a non-empty finalState"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_difficulty_is_valid(self, recipe):
        diff = recipe.get("metadata", {}).get("difficulty")
        if diff is not None:
            assert diff in VALID_DIFFICULTIES, f"Invalid difficulty: {diff}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_recipe_type_is_valid(self, recipe):
        rt = recipe.get("metadata", {}).get("recipeType")
        if rt is not None:
            assert rt in VALID_RECIPE_TYPES, f"Invalid recipeType: {rt}"


class TestIngredientQuality:
    """Validate ingredient completeness and correctness."""

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_unique_ids(self, recipe):
        ids = [ing.get("id") for ing in recipe.get("ingredients", [])]
        assert len(ids) == len(set(ids)), f"Duplicate ingredient IDs: {[x for x in ids if ids.count(x) > 1]}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_name(self, recipe):
        for ing in recipe.get("ingredients", []):
            assert isinstance(ing.get("name"), str) and ing["name"], \
                f"Ingredient {ing.get('id')} missing name"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_name_en(self, recipe):
        """Every ingredient should have an English translation after enrichment."""
        missing = []
        for ing in recipe.get("ingredients", []):
            if not ing.get("name_en"):
                missing.append(ing.get("id", "?"))
        # Allow up to 20% missing (salt/pepper might not get translated)
        threshold = max(1, len(recipe.get("ingredients", [])) * 0.2)
        assert len(missing) <= threshold, \
            f"{len(missing)} ingredients missing name_en (threshold {threshold:.0f}): {missing}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_valid_category(self, recipe):
        for ing in recipe.get("ingredients", []):
            cat = ing.get("category")
            if cat is not None:
                assert cat in VALID_CATEGORIES, \
                    f"Ingredient '{ing.get('id')}' has invalid category: {cat}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_quantity_is_positive_when_present(self, recipe):
        for ing in recipe.get("ingredients", []):
            qty = ing.get("quantity")
            if qty is not None:
                assert isinstance(qty, (int, float)) and qty > 0, \
                    f"Ingredient '{ing.get('id')}' quantity must be > 0, got {qty}"


class TestDAGIntegrity:
    """Validate that the step graph is a valid DAG."""

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_unique_step_ids(self, recipe):
        ids = [s.get("id") for s in recipe.get("steps", [])]
        assert len(ids) == len(set(ids)), f"Duplicate step IDs: {[x for x in ids if ids.count(x) > 1]}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_valid_step_types(self, recipe):
        for step in recipe.get("steps", []):
            st = step.get("stepType")
            if st is not None:
                assert st in VALID_STEP_TYPES, \
                    f"Step '{step.get('id')}' has invalid stepType: {st}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_unique_produces(self, recipe):
        """No two steps should produce the same state."""
        produced = [s.get("produces") for s in recipe.get("steps", []) if s.get("produces")]
        assert len(produced) == len(set(produced)), \
            f"Duplicate produces: {[x for x in produced if produced.count(x) > 1]}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_uses_references_exist(self, recipe):
        """Every ref in uses must be either an ingredient ID or a produced state."""
        ingredient_ids = {ing.get("id") for ing in recipe.get("ingredients", [])}
        produced_states = set()
        errors = []
        for step in recipe.get("steps", []):
            for ref in step.get("uses", []):
                if ref not in ingredient_ids and ref not in produced_states:
                    errors.append(f"Step '{step.get('id')}' uses unknown ref '{ref}'")
            prod = step.get("produces")
            if prod:
                produced_states.add(prod)
        assert not errors, "\n".join(errors)

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_requires_references_exist(self, recipe):
        """Every ref in requires must be a produced state."""
        produced_states = set()
        errors = []
        for step in recipe.get("steps", []):
            for ref in step.get("requires", []):
                if ref not in produced_states:
                    errors.append(f"Step '{step.get('id')}' requires unknown state '{ref}'")
            prod = step.get("produces")
            if prod:
                produced_states.add(prod)
        assert not errors, "\n".join(errors)

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_final_state_is_produced(self, recipe):
        """finalState must be produced by some step."""
        produced = {s.get("produces") for s in recipe.get("steps", []) if s.get("produces")}
        fs = recipe.get("finalState", "")
        assert fs in produced, f"finalState '{fs}' not produced by any step"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_no_orphan_states(self, recipe):
        """Every produced state should be consumed by another step or be the finalState."""
        produced_states = {}
        for step in recipe.get("steps", []):
            prod = step.get("produces")
            if prod:
                produced_states[prod] = step.get("id")

        consumed = set()
        for step in recipe.get("steps", []):
            for ref in step.get("uses", []) + step.get("requires", []):
                if ref in produced_states:
                    consumed.add(ref)

        final_state = recipe.get("finalState", "")
        orphans = set(produced_states.keys()) - consumed - {final_state}
        assert not orphans, f"Orphan states (produced but never consumed): {orphans}"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_dag_is_acyclic(self, recipe):
        """Verify the step graph has no cycles (topological sort)."""
        steps = recipe.get("steps", [])
        ingredient_ids = {ing.get("id") for ing in recipe.get("ingredients", [])}

        # Build state → producer step mapping
        state_producer = {}
        for step in steps:
            prod = step.get("produces", "")
            if prod:
                state_producer[prod] = step.get("id")

        # Build adjacency (predecessors for each step)
        predecessors = {s.get("id"): set() for s in steps}
        for step in steps:
            sid = step.get("id")
            refs = list(step.get("uses", [])) + list(step.get("requires", []))
            for ref in refs:
                if ref in ingredient_ids:
                    continue
                if ref in state_producer:
                    pred_id = state_producer[ref]
                    if pred_id != sid:
                        predecessors[sid].add(pred_id)

        # Kahn's algorithm
        in_degree = {sid: len(preds) for sid, preds in predecessors.items()}
        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for sid, preds in predecessors.items():
                if node in preds:
                    in_degree[sid] -= 1
                    if in_degree[sid] == 0:
                        queue.append(sid)

        assert visited == len(steps), \
            f"Cycle detected in step graph! Only {visited}/{len(steps)} steps are reachable."

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_all_ingredients_used(self, recipe):
        """Every non-optional ingredient should be referenced in at least one step's uses."""
        used = set()
        for step in recipe.get("steps", []):
            for ref in step.get("uses", []):
                used.add(ref)

        unused = []
        for ing in recipe.get("ingredients", []):
            if not ing.get("optional", False) and ing.get("id") not in used:
                unused.append(ing.get("id"))

        assert not unused, f"Unused ingredients: {unused}"


class TestTimeCoherence:
    """Validate that DAG-computed times are present and coherent."""

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_total_time_exists(self, recipe):
        meta = recipe.get("metadata", {})
        assert meta.get("totalTimeMinutes", 0) > 0, \
            "totalTimeMinutes must be > 0"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_active_time_exists(self, recipe):
        meta = recipe.get("metadata", {})
        assert meta.get("totalActiveTimeMinutes", 0) > 0, \
            "totalActiveTimeMinutes must be > 0"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_active_lte_total(self, recipe):
        meta = recipe.get("metadata", {})
        active = meta.get("totalActiveTimeMinutes", 0)
        total = meta.get("totalTimeMinutes", 0)
        assert active <= total + 0.1, \
            f"Active time ({active}) > total time ({total})"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_passive_lte_total(self, recipe):
        meta = recipe.get("metadata", {})
        passive = meta.get("totalPassiveTimeMinutes", 0)
        total = meta.get("totalTimeMinutes", 0)
        assert passive <= total + 0.1, \
            f"Passive time ({passive}) > total time ({total})"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_active_plus_passive_equals_total(self, recipe):
        meta = recipe.get("metadata", {})
        active = meta.get("totalActiveTimeMinutes", 0)
        passive = meta.get("totalPassiveTimeMinutes", 0)
        total = meta.get("totalTimeMinutes", 0)
        assert abs((active + passive) - total) <= 1.0, \
            f"active({active}) + passive({passive}) = {active + passive} != total({total})"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_iso_format_valid(self, recipe):
        meta = recipe.get("metadata", {})
        for field in ("totalTime", "totalActiveTime", "totalPassiveTime"):
            val = meta.get(field)
            if val is not None:
                assert val.startswith("PT"), \
                    f"{field}='{val}' is not valid ISO 8601 (must start with 'PT')"


class TestEnrichmentMetadata:
    """Validate enrichment-added metadata (diets, seasons, etc.)."""

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_diets(self, recipe):
        meta = recipe.get("metadata", {})
        diets = meta.get("diets", [])
        assert isinstance(diets, list) and len(diets) >= 1, "Must have at least 1 diet"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_valid_diets(self, recipe):
        meta = recipe.get("metadata", {})
        for d in meta.get("diets", []):
            assert d in VALID_DIETS, f"Invalid diet: '{d}'"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_has_seasons(self, recipe):
        meta = recipe.get("metadata", {})
        seasons = meta.get("seasons", [])
        assert isinstance(seasons, list) and len(seasons) >= 1, "Must have at least 1 season"

    @pytest.mark.parametrize("recipe", ALL_RECIPES, ids=recipe_ids())
    def test_valid_seasons(self, recipe):
        meta = recipe.get("metadata", {})
        for s in meta.get("seasons", []):
            assert s in VALID_SEASONS, f"Invalid season: '{s}'"
