"""
Validation tests for the unified nutrition index (OpenNutrition + CIQUAL + MEXT).

Run: python -m pytest tests/test_unified_nutrition_index.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

_DATA_DIR = Path(__file__).parent.parent / "src" / "recipe_scraper" / "data"

_BASELINE_INGREDIENTS = [
    ("butter", 700, 750),
    ("olive oil", 850, 900),
    ("all-purpose flour", 340, 380),
    ("sugar", 380, 410),
    ("lard", 880, 910),
]

_CIQUAL_EXPECTED = ["burrata", "pancetta", "tabbouleh or couscous salad, with vegetables, prepacked"]
_MEXT_EXPECTED = ["sesame seeds, whole, dried", "amaranth, whole grain, raw"]


@pytest.fixture(scope="module")
def unified_index():
    """Load and merge all 3 indexes."""
    with open(_DATA_DIR / "opennutrition_index.json") as f:
        base = json.load(f)
    for e in base:
        e.setdefault("source", "opennutrition")

    seen = {e["name"].lower(): i for i, e in enumerate(base)}
    merged = list(base)

    for fname, source, replace in [
        ("ciqual_index.json", "ciqual", True),
        ("mext_index.json", "mext", False),
    ]:
        p = _DATA_DIR / fname
        if not p.exists():
            continue
        with open(p) as f:
            entries = json.load(f)
        for entry in entries:
            key = entry["name"].lower()
            if key in seen:
                if replace:
                    merged[seen[key]] = entry
            else:
                seen[key] = len(merged)
                merged.append(entry)

    return merged


@pytest.fixture(scope="module")
def exact_lookup(unified_index):
    """Build exact name + alt lookup dict."""
    d = {}
    for entry in unified_index:
        d[entry["name"].lower()] = entry
        for alt in entry.get("alt", []):
            d.setdefault(alt.lower(), entry)
    return d


def test_unified_index_size(unified_index):
    assert len(unified_index) >= 9000, f"Expected >=9000, got {len(unified_index)}"


def test_all_entries_have_required_fields(unified_index):
    required = {"id", "name", "kcal", "source"}
    for i, entry in enumerate(unified_index):
        missing = required - set(entry.keys())
        assert not missing, f"Entry {i} ({entry.get('name', '?')}) missing: {missing}"


def test_no_empty_names(unified_index):
    for entry in unified_index:
        assert entry["name"].strip(), f"Empty name in entry {entry.get('id')}"


def test_kcal_range(unified_index):
    """Pure oils can reach ~921 kcal/100g. Only flag truly impossible values."""
    bad = []
    for entry in unified_index:
        kcal = entry.get("kcal")
        if kcal is not None and (kcal < 0 or kcal > 950):
            bad.append((entry["name"], kcal))
    assert len(bad) <= 3, f"Too many impossible kcal values (>950): {bad}"


@pytest.mark.parametrize("name,low,high", _BASELINE_INGREDIENTS)
def test_baseline_nonregression(exact_lookup, name, low, high):
    """Verify well-known ingredients still match with correct kcal range."""
    entry = exact_lookup.get(name.lower())
    assert entry is not None, f"'{name}' not found in unified index"
    kcal = entry.get("kcal", 0)
    assert low <= kcal <= high, f"'{name}': kcal={kcal}, expected [{low},{high}]"


@pytest.mark.parametrize("name", _CIQUAL_EXPECTED)
def test_ciqual_coverage(exact_lookup, name):
    """Verify CIQUAL adds coverage for these ingredients."""
    assert name.lower() in exact_lookup, f"'{name}' not found (expected from CIQUAL)"


@pytest.mark.parametrize("name", _MEXT_EXPECTED)
def test_mext_coverage(exact_lookup, name):
    """Verify MEXT adds coverage for these ingredients."""
    assert name.lower() in exact_lookup, f"'{name}' not found (expected from MEXT)"


def test_source_field_values(unified_index):
    sources = {e.get("source") for e in unified_index}
    assert "opennutrition" in sources
    assert "ciqual" in sources
    assert "mext" in sources
