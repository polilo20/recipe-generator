"""
Unit tests for app/rag.py — pure functions only (no LLM, no file I/O).

Run with:
  pytest tests/
"""

import pytest

from app.rag import _build_recipes_block, retrieve, score


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# weight_map from rag.py: base=1, flavoring=2, main=3
INGREDIENTS_DATA = {
    "agneau":   {"weight": "main",      "category": "Viandes",          "normalizing": []},  # w=3
    "carotte":  {"weight": "main",      "category": "Légumes",          "normalizing": []},  # w=3
    "parmesan": {"weight": "flavoring", "category": "Fromages",         "normalizing": []},  # w=2
    "oignon":   {"weight": "flavoring", "category": "Épices",           "normalizing": []},  # w=2
    "beurre":   {"weight": "base",      "category": "Matières grasses", "normalizing": []},  # w=1
}

RECIPE_CONTENT_AGNEAU = "Faire revenir l'agneau avec les carottes et l'oignon."
RECIPE_CONTENT_CAROTTES = "Râper les carottes et assaisonner."


def make_recipe(title: str, ingredients: list[str], content: str = "Contenu générique.") -> dict:
    return {
        "extracted": {"titre": title},
        "ingredients_normalises": ingredients,
        "cleaned_content": content,
    }


# ---------------------------------------------------------------------------
# score()
# ---------------------------------------------------------------------------

def test_score_no_overlap_returns_zero():
    recipe = make_recipe("R", ["carotte", "oignon"])
    assert score(recipe, ["agneau"], INGREDIENTS_DATA) == 0.0


def test_score_full_overlap_returns_one():
    recipe = make_recipe("R", ["carotte"])
    assert score(recipe, ["carotte"], INGREDIENTS_DATA) == 1.0


def test_score_partial_overlap():
    # recipe: carotte (main, w=3) + oignon (flavoring, w=2) → total weight 5
    # chosen overlaps on carotte only → 3/5
    recipe = make_recipe("R", ["carotte", "oignon"])
    assert score(recipe, ["carotte"], INGREDIENTS_DATA) == pytest.approx(3 / 5)


def test_score_main_weighs_more_than_flavoring():
    # recipe: agneau (main, w=3) + oignon (flavoring, w=2) → total 5
    # agneau alone → 3/5 > oignon alone → 2/5
    recipe = make_recipe("R", ["agneau", "oignon"])
    assert score(recipe, ["agneau"], INGREDIENTS_DATA) > score(recipe, ["oignon"], INGREDIENTS_DATA)


def test_score_flavoring_weighs_more_than_base():
    # recipe: parmesan (flavoring, w=2) + beurre (base, w=1) → total 3
    # parmesan alone → 2/3 > beurre alone → 1/3
    recipe = make_recipe("R", ["parmesan", "beurre"])
    assert score(recipe, ["parmesan"], INGREDIENTS_DATA) > score(recipe, ["beurre"], INGREDIENTS_DATA)


def test_score_unknown_ingredient_defaults_to_base_weight():
    # "inconnu" is not in INGREDIENTS_DATA → treated as base (w=1)
    # recipe: inconnu only → total 1; chosen = [inconnu] → 1/1 = 1.0
    recipe = {"extracted": {}, "ingredients_normalises": ["inconnu"], "cleaned_content": ""}
    assert score(recipe, ["inconnu"], INGREDIENTS_DATA) == pytest.approx(1.0)


def test_score_empty_recipe_ingredients_returns_zero():
    recipe = make_recipe("R", [])
    assert score(recipe, ["carotte"], INGREDIENTS_DATA) == 0.0


# ---------------------------------------------------------------------------
# retrieve()
# ---------------------------------------------------------------------------

RECIPES = [
    make_recipe("Agneau aux carottes", ["agneau", "carotte", "oignon", "beurre"], RECIPE_CONTENT_AGNEAU),
    make_recipe("Salade de carottes",  ["carotte"],                               RECIPE_CONTENT_CAROTTES),
    make_recipe("Recette sans rapport", ["inconnu_a", "inconnu_b"]),
]


def test_retrieve_excludes_recipes_below_cutoff_0_3():
    results = retrieve(RECIPES, ["carotte"], INGREDIENTS_DATA, cutoff=0.3)
    titles = [r["extracted"]["titre"] for r in results]
    assert "Recette sans rapport" not in titles


def test_retrieve_returns_empty_when_nothing_matches():
    results = retrieve(RECIPES, ["ingredient_inexistant"], INGREDIENTS_DATA, cutoff=0.3)
    assert results == []


def test_retrieve_sorted_best_first_with_cutoff_0_3():
    # "Salade de carottes" has only carotte (main, w=3) → score 1.0
    # "Agneau aux carottes" has carotte among many → lower score
    results = retrieve(RECIPES, ["carotte"], INGREDIENTS_DATA, cutoff=0.3)
    assert results[0]["extracted"]["titre"] == "Salade de carottes"


def test_retrieve_respects_max_results():
    many = [make_recipe(f"Recette {i}", ["carotte"]) for i in range(10)]
    results = retrieve(many, ["carotte"], INGREDIENTS_DATA, cutoff=0.0, max_results=3)
    assert len(results) == 3


def test_retrieve_default_max_results_is_five():
    many = [make_recipe(f"Recette {i}", ["carotte"]) for i in range(10)]
    results = retrieve(many, ["carotte"], INGREDIENTS_DATA, cutoff=0.0)
    assert len(results) == 5


# ---------------------------------------------------------------------------
# _build_recipes_block()
# ---------------------------------------------------------------------------

def test_build_recipes_block_numbers_from_one():
    recipes = [make_recipe("Tarte", ["carotte"], RECIPE_CONTENT_CAROTTES)]
    block = _build_recipes_block(recipes)
    assert "### Recette 1 :" in block


def test_build_recipes_block_includes_content():
    recipes = [make_recipe("Tarte", ["carotte"], RECIPE_CONTENT_CAROTTES)]
    block = _build_recipes_block(recipes)
    assert RECIPE_CONTENT_CAROTTES in block


def test_build_recipes_block_falls_back_to_original_title():
    recipe = {
        "extracted": {},
        "original_title": "Fallback Title",
        "cleaned_content": RECIPE_CONTENT_CAROTTES,
        "ingredients_normalises": [],
    }
    block = _build_recipes_block([recipe])
    assert "Fallback Title" in block


def test_build_recipes_block_falls_back_to_sans_titre():
    recipe = {
        "extracted": {},
        "cleaned_content": RECIPE_CONTENT_CAROTTES,
        "ingredients_normalises": [],
    }
    block = _build_recipes_block([recipe])
    assert "Sans titre" in block


def test_build_recipes_block_multiple_recipes_all_numbered():
    recipes = [
        make_recipe("Soupe",  ["carotte"], RECIPE_CONTENT_CAROTTES),
        make_recipe("Gratin", ["oignon"],  RECIPE_CONTENT_AGNEAU),
    ]
    block = _build_recipes_block(recipes)
    assert "### Recette 1 :" in block
    assert "### Recette 2 :" in block
    assert "Soupe" in block
    assert "Gratin" in block
