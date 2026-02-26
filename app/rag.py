"""
RAG pipeline for recipe generation.

1. Retrieval: select recipes whose normalized ingredients overlap with user-chosen ingredients.
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
INGREDIENTS_DISPLAY_PATH = Path(__file__).resolve().parent.parent / "processing" / "ingredients_display.json"

GENERATION_PROMPT = """\
Tu es un chef créatif. L'utilisateur souhaite cuisiner avec les ingrédients suivants \
(ce sont les ingrédients « stars » de la recette) :

{star_ingredients}

Voici des recettes existantes qui utilisent un ou plusieurs de ces ingrédients. \
Inspire-toi de ces recettes pour créer une NOUVELLE recette originale. Tu ne dois surtout pas en reproduire une. Tu dois simplement t'inspirer du style de cuisine et des autres ingrédients utilisés.

--- RECETTES DE RÉFÉRENCE ---
{recipes_block}
--- FIN DES RECETTES ---

Consignes :
- Les ingrédients stars doivent être au cœur de ta recette.
- Tu peux ajouter d'autres ingrédients complémentaires si nécessaire.
- Donne un titre accrocheur, la liste des ingrédients avec quantités, \
et les étapes de réalisation.
- Indique le temps de préparation et de cuisson estimés.
- Ne reproduis AUCUNE des recettes ci-dessus. Crée quelque chose de nouveau.
- Réponds UNIQUEMENT en français.
- Ne pas inclure de section "Pourquoi cette recette", commentaire ou justification. La recette seule suffit.

Propose ta nouvelle recette :
"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_recipes(path: Path = DATA_PATH) -> list[dict]:
    """Load recipe data from the normalized JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_ingredient_list(path: Path = INGREDIENTS_MAP_PATH) -> list[str]:
    """Return sorted list of canonical ingredient names from the map."""
    with open(path, encoding="utf-8") as f:
        grouped = json.load(f)
    return sorted(grouped.keys())


def load_display_ingredients(path: Path = INGREDIENTS_DISPLAY_PATH) -> tuple[list[str], dict[str, str]]:
    """Load the display dict and build a flat list + reverse mapping.

    Returns:
        display_list: sorted flat list of all user-visible ingredient names
            (canonical keys + their display variants)
        display_to_canonical: maps every display name to its canonical key
    """
    with open(path, encoding="utf-8") as f:
        display_map = json.load(f)

    display_to_canonical: dict[str, str] = {}
    for canonical, variants in display_map.items():
        display_to_canonical[canonical] = canonical
        for v in variants:
            display_to_canonical[v] = canonical
    display_list = sorted(display_to_canonical.keys())
    return display_list, display_to_canonical


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(recipes: list[dict], chosen_ingredients: list[str]) -> list[dict]:
    """Return recipes that contain at least one of the chosen ingredients,
    sorted by number of shared ingredients (most relevant first).

    Expects recipes with already-normalized ingredients_normalises (canonical names).
    """
    chosen = set(chosen_ingredients)

    matched = []
    for r in recipes:
        recipe_ingredients = set(r["extracted"].get("ingredients_normalises", []))
        overlap = len(recipe_ingredients & chosen)
        if overlap > 0:
            matched.append((overlap, r))

    matched.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in matched]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _build_recipes_block(recipes: list[dict], max_recipes: int = 10) -> str:
    """Format recipe cleaned_content for the prompt."""
    parts = []
    for i, r in enumerate(recipes[:max_recipes], 1):
        title = r["extracted"].get("titre", r.get("original_title", "Sans titre"))
        parts.append(f"### Recette {i} : {title}\n{r['cleaned_content']}\n")
    return "\n".join(parts)


def _generate_mistral_api(prompt: str) -> str:
    """Generate via Mistral API."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY environment variable not set")

    resp = requests.post(MISTRAL_API_URL, json={
        "model": MISTRAL_API_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048,
    }, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate(chosen_ingredients: list[str], matched_recipes: list[dict]) -> str:
    """Generate a new recipe using the Mistral API."""
    prompt = GENERATION_PROMPT.format(
        star_ingredients=", ".join(chosen_ingredients),
        recipes_block=_build_recipes_block(matched_recipes),
    )
    return _generate_mistral_api(prompt)


def generate_without_context(chosen_ingredients: list[str]) -> str:
    """Generate a recipe with NO reference recipes (baseline)."""
    prompt = GENERATION_PROMPT.format(
        star_ingredients=", ".join(chosen_ingredients),
        recipes_block="Aucune recette de référence.",
    )
    return _generate_mistral_api(prompt)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RAG recipe generator")
    parser.parse_args()

    recipes = load_recipes()
    display_list, display_to_canonical = load_display_ingredients()

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

    # Map user choices to canonical names for retrieval
    chosen = list({display_to_canonical[s] for s in selected})
    print(f"\nIngrédients choisis : {', '.join(selected)}")
    if selected != chosen:
        print(f"  -> normalisés pour la recherche : {', '.join(chosen)}")

    # --- Retrieval ---
    matched = retrieve(recipes, chosen)
    print(f"Recettes trouvées : {len(matched)}")
    for r in matched:
        print(f"  - {r['extracted'].get('titre', r.get('original_title', '?'))}")

    if not matched:
        print("Aucune recette trouvée pour ces ingrédients.")
        return

    # --- Show reference recipes fed to the LLM ---
    recipes_block = _build_recipes_block(matched)
    print(f"\n{'='*60}")
    print("RECETTES DE RÉFÉRENCE ENVOYÉES AU LLM")
    print(f"{'='*60}")
    print(recipes_block)

    # --- Generation ---
    print(f"{'='*60}")
    print(f"Génération d'une nouvelle recette avec Mistral API...")
    print(f"{'='*60}")
    result = generate(chosen, matched)
    print(f"\n{'='*60}")
    print("RECETTE GÉNÉRÉE")
    print(f"{'='*60}")
    print(result)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
