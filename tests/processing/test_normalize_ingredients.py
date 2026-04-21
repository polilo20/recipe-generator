"""
Tests for processing/normalize_ingredients.py

Run with:
  pytest tests/
"""

import json
from pathlib import Path

import pytest

from processing.normalize_ingredients import (
    load_extracted_recipes,
    load_ingredients_map,
    normalize_recipe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# load_ingredients_map
# ---------------------------------------------------------------------------

# The map file groups normalized names to lists of variants, e.g.:
#   { "tomate": {"normalizing": ["tomates", "tomate pelée"], ...} }
# After loading, every variant AND the normalized name itself should map to the normalized name.


def test_load_ingredients_map_normalized_maps_to_itself():
    # Given a grouped map with one normalized key,
    # the normalized name should map to itself.
    pass


def test_load_ingredients_map_variant_maps_to_normalized():
    # Given a grouped map where "tomates" is a variant of "tomate",
    # loading the map should return {"tomate": "tomate", "tomates": "tomate"}.
    pass


def test_load_ingredients_map_multiple_variants():
    # A normalized name with several variants should produce one entry per variant,
    # all pointing to the same normalized name.
    pass


# ---------------------------------------------------------------------------
# normalize_recipe
# ---------------------------------------------------------------------------

# normalize_recipe takes a recipe dict and a variant_to_normalized mapping,
# and returns a new recipe dict with ingredients_normalises at the top level
# containing their normalized forms.


def test_normalize_recipe_replaces_known_variant():
    # If a recipe contains a known variant (e.g. "tomates"),
    # the result should contain the normalized form ("tomate") instead.
    pass


def test_normalize_recipe_keeps_unknown_ingredient_unchanged():
    # If an ingredient is not in the map, it should be kept as-is.
    pass


def test_normalize_recipe_deduplicates():
    # If two variants in a recipe map to the same normalized name,
    # the normalized name should appear only once in the result.
    pass


def test_normalize_recipe_does_not_mutate_input():
    # The original recipe dict should not be modified.
    pass


def test_normalize_recipe_strips_and_lowercases():
    # Ingredients with leading/trailing spaces or mixed case
    # should still be matched against the map.
    pass


# ---------------------------------------------------------------------------
# load_extracted_recipes
# ---------------------------------------------------------------------------

# load_extracted_recipes reads all *.json files from a directory
# and returns them as a list of dicts.


def test_load_extracted_recipes_reads_fixture(tmp_path):
    # Copy the sample fixture into a tmp_path directory,
    # then check that load_extracted_recipes returns a list with one item
    # whose keys match what the fixture contains.
    pass


def test_load_extracted_recipes_empty_dir(tmp_path):
    # An empty directory should return an empty list.
    pass


def test_load_extracted_recipes_ignores_non_json(tmp_path):
    # Non-JSON files in the directory should be ignored.
    pass
