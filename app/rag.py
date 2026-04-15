"""
RAG pipeline for recipe generation.

1. Retrieval: select recipes whose normalized ingredients overlap significantly with user-chosen ingredients.
2. Generation: feed matched recipes' cleaned_content to the Mistral API
   and ask it to create a new recipe starring the user's ingredients.
"""

import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
load_dotenv()

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_MODEL = "mistral-small-latest"

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes_normalized.json"
INGREDIENTS_MAP_PATH = Path(__file__).resolve().parent.parent / "processing" / "ingredients_map.json"

GENERATION_PROMPT = """\
Tu es un chef cuisinier.

Tu dois faire une recette contenant ces ingrédients : {star_ingredients}

Première étape : prends connaissance de {star_ingredients} et de {ingredients_map} et comprends quels sont les ingrédients que tu peux utiliser de façon interchangeable. 

Seconde étape : prends connaissance des recettes suivantes. La première recette est la plus pertinente. Comprends leur style et leur intention : 

{matched_recipes}

Troisième étape : combine ce que tu as appris lors des deux dernières étapes, et uniquement cela, pour proposer une nouvelle recette. 
Cette recette doit absolument citer tous ces ingrédients : {star_ingredients}. N'hésite pas à aussi utiliser les autres ingrédients mentionnés dans les recettes fournies, 
ils sont sûrement pertinents pour faire un bon plat, dans l'esprit du corpus. Tu ne dois utiliser aucune connaissance hors de ce qui a déjà été fourni.
Relis simplement ta recette pour vérifier qu'elle est cohérente pour un chef cuisinier qui maîtrise les techniques de base.

Notamment n'oublie pas :
- Donne un titre à ta recette.
- Reprends la liste des ingrédients avec leurs quantités.
- Donne les étapes de réalisation.
- Indique les temps de préparation et de cuisson.
- Réponds UNIQUEMENT en français.
- Ne pas inclure de commentaire ou de justification. La recette seule suffit.

Propose la recette :
"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_recipes(path: Path = DATA_PATH) -> list[dict]:
    """Load recipe data from the normalized JSON.

    In production (GCS_BUCKET env var set), downloads from Google Cloud Storage.
    Locally, reads from the filesystem path (mounted via docker-compose).
    """
    bucket_name = os.environ.get("GCS_BUCKET")
    if bucket_name:
        import google.cloud.storage as storage
        client = storage.Client()
        blob = client.bucket(bucket_name).blob("recipes_normalized.json")
        return json.loads(blob.download_as_text(encoding="utf-8"))

    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_ingredients_data(path: Path = INGREDIENTS_MAP_PATH) -> dict:
    """Load ingredient data from the ingredients map JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def score(recipe: dict, ingredients: list[str], ingredients_data: dict) -> float:
    """Compute a score from 0 to 1 reflecting how significantly the recipe overlaps
    with the chosen ingredients, weighted by ingredient importance (see weight_map).

    Recipes with many ingredients are naturally penalized (larger denominator).
    """
    weight_map = {"base": 1, "flavoring": 2, "main": 3}

    chosen = set(ingredients)
    recipe_ingredients = set(recipe.get("ingredients_normalises", []))

    overlap = recipe_ingredients & chosen

    def ingredient_weight(ing: str) -> int:
        return weight_map.get(ingredients_data.get(ing, {}).get("weight", "base"), 1)

    total_recipe_weight = sum(ingredient_weight(ing) for ing in recipe_ingredients)
    if total_recipe_weight == 0:
        return 0.0

    overlap_weight = sum(ingredient_weight(ing) for ing in overlap)
    return overlap_weight / total_recipe_weight


def retrieve(recipes: list[dict], chosen_ingredients: list[str], ingredients_data: dict, cutoff: float = 0.1) -> list[dict]:
    """Return all recipes with a score above the cutoff.

    Expects recipes with already-normalized ingredients_normalises (normalized names).
    """
    matched = []
    for r in recipes:
        s = score(r, chosen_ingredients, ingredients_data)
        if s >= cutoff:
            matched.append((s, r))

    matched.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in matched]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _build_recipes_block(recipes: list[dict], max_recipes: int = 5) -> str:
    """Format recipe cleaned_content for the prompt (kept for reference/baseline)."""
    # Should ingredients be outlined here ?
    parts = []
    for i, r in enumerate(recipes[:max_recipes], 1):
        title = r["extracted"].get("titre", r.get("original_title", "Sans titre"))
        parts.append(f"### Recette {i} : {title}\n{r['cleaned_content']}\n")
    return "\n".join(parts)


def _call_mistral(prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    """Low-level Mistral API call."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY environment variable not set")

    resp = requests.post(MISTRAL_API_URL, json={
        "model": MISTRAL_API_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate(chosen_ingredients: list[str], matched_recipes: list[dict], ingredients_data: dict) -> str:
    """Generate a recipe grounded in corpus ingredients with LLM-chosen technique."""

    # Only pass synonyms for chosen ingredients — the full map is too noisy for the LLM
    synonyms = {
        ing: ingredients_data[ing]["normalizing"]
        for ing in chosen_ingredients
        if ing in ingredients_data
    }
        
    prompt = GENERATION_PROMPT.format(
        star_ingredients=", ".join(chosen_ingredients),
        matched_recipes=_build_recipes_block(matched_recipes),
        ingredients_map=json.dumps(synonyms, ensure_ascii=False),
    )

    return _call_mistral(prompt, temperature=0.1, max_tokens=2048)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RAG recipe generator")
    parser.parse_args()

    recipes = load_recipes()
    ingredients_data = load_ingredients_data()
    display_list = list(ingredients_data.keys())

    print("=== Ingrédients disponibles ===")
    for i, ing in enumerate(display_list, 1):
        print(f"  {i:3d}. {ing}")

    print(f"\nEntrez les numéros des ingrédients séparés par des virgules (ex: 1,5,12) :")
    raw = input("> ").strip()
    if not raw:
        print("Aucun ingrédient sélectionné.")
        return

    indices = [int(x.strip()) - 1 for x in raw.split(",") if x.strip().isdigit()]
    selected = [display_list[i] for i in indices if 0 <= i < len(display_list)]

    if not selected:
        print("Aucun ingrédient valide.")
        return

    # --- Retrieval ---
    matched = retrieve(recipes, selected, ingredients_data)
    print(f"Recettes trouvées : {len(matched)}")
    for r in matched:
        print(f"  - {r['extracted'].get('titre', r.get('original_title', '?'))}")

    if not matched:
        print(
            "Aucune recette pertinente trouvée pour ces ingrédients. Essayez d'en sélectionner d'autres. \n"
            "Plus vous en sélectionnez, notamment des légumes, plus les chances d'avoir des matchs pertinents augmentent."
        )
        return

    # --- Show all recipes fed to the LLM ---
    print(f"\n{'='*60}")
    print("RECETTES ENVOYÉES AU LLM")
    print(f"{'='*60}")
    print(_build_recipes_block(matched))

    print(f"\n{'='*60}")
    print(f"Génération avec Mistral API...")
    print(f"{'='*60}")
    result = generate(selected, matched, ingredients_data)
    print(f"\n{'='*60}")
    print("RECETTE GÉNÉRÉE")
    print(f"{'='*60}")
    print(result)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
