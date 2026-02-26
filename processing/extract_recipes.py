"""
Extract structured recipe data from cleaned content using an LLM.

Supports two backends:
  --backend ollama   (default) local Mistral via Ollama
  --backend mistral  Mistral API (requires MISTRAL_API_KEY env var)

Results are saved individually in data/extracted/ (one JSON per recipe).

Usage:
  python -m processing.extract_recipes                          # process all (Ollama)
  python -m processing.extract_recipes --backend mistral        # process all (API)
  python -m processing.extract_recipes --limit 50               # process up to 50
  python -m processing.extract_recipes --filter "Clem"          # only files matching substring
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_MODEL = "mistral-small-latest"

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
EXTRACTED_DIR = Path(__file__).resolve().parent.parent / "data" / "extracted"

PROMPT_TEMPLATE = """\
Tu es un assistant spécialisé dans l'analyse de recettes de cuisine. \
Analyse le texte suivant et extrais les informations structurées.

Si le texte n'est pas une recette de cuisine, réponds uniquement avec le JSON :
{{"est_une_recette": false, "raison": "explication courte"}}

Si c'est une recette, réponds UNIQUEMENT avec un JSON valide (sans commentaire, sans explication) \
contenant les champs suivants.

IMPORTANT : dans "ingredients" et "ingredients_normalises", inclure TOUS les ingrédients, \
y compris l'ingrédient principal de la recette même s'il n'est pas listé explicitement \
dans la section ingrédients du texte (ex: le magret dans "magret de canard aux cerises", \
le saumon dans "pavé de saumon à l'aneth"). Les blogs omettent souvent l'ingrédient \
principal car il est évident depuis le titre.

{{
  "est_une_recette": true,
  "titre": "nom de la recette",
  "categorie": "entrée | plat | dessert | apéritif | accompagnement | boisson | autre",
  "ingredients": [
    {{"nom": "nom de l'ingrédient", "quantite": "quantité avec unité ou null si non précisé"}},
  ],
  "ingredients_normalises": ["liste d'ingrédients simplifiés sans quantité, au singulier, en minuscule"],
  "ustensiles": ["liste des ustensiles nécessaires déduits de la recette"],
  "temps_preparation": "durée ou null",
  "temps_cuisson": "durée ou null",
  "nombre_portions": "nombre de portions ou null",
  "difficulte": "facile | moyen | difficile",
  "saison": "printemps | été | automne | hiver | toute saison",
  "vegetarien": true/false,
  "vegan": true/false,
  "sans_gluten": true/false,
  "proteine": true/false,
  "astuces": ["liste de conseils ou variantes mentionnés"],
  "tags": ["mots-clés pertinents pour la recette"]
}}

Texte à analyser :
---
{content}
---

Réponds uniquement avec le JSON, sans aucun texte avant ou après.
"""


def _parse_llm_response(raw_response: str) -> dict:
    """Parse JSON from an LLM response, handling common formatting issues."""
    text = raw_response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]  # remove ```json line
        text = text.rsplit("```", 1)[0]  # remove closing ```
        text = text.strip()

    # Fix trailing commas before ] or } (common LLM mistake)
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return json.loads(text)


def extract_recipe_ollama(cleaned_content: str) -> dict:
    """Send cleaned content to Ollama and parse the structured response."""
    prompt = PROMPT_TEMPLATE.format(content=cleaned_content)

    resp = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2048,
        },
    }, timeout=600)
    resp.raise_for_status()

    return _parse_llm_response(resp.json()["response"])


def extract_recipe_mistral(cleaned_content: str) -> dict:
    """Send cleaned content to the Mistral API and parse the structured response."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY non définie. "
            "Exporte la variable : export MISTRAL_API_KEY=your_key"
        )

    prompt = PROMPT_TEMPLATE.format(content=cleaned_content)

    resp = requests.post(MISTRAL_API_URL, json={
        "model": MISTRAL_API_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2048,
    }, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, timeout=120)
    resp.raise_for_status()

    return _parse_llm_response(resp.json()["choices"][0]["message"]["content"])


def process_file(filepath: Path, output_dir: Path, backend: str) -> dict | None:
    """Process a single recipe file and save the result."""
    with open(filepath, "r", encoding="utf-8") as f:
        recipe = json.load(f)

    print(f"\n{'='*60}")
    print(f"Source: {recipe['source']}")
    print(f"Titre:  {recipe['title']}")
    print(f"URL:    {recipe['url']}")
    print(f"{'='*60}")

    if backend == "mistral":
        extracted = extract_recipe_mistral(recipe["cleaned_content"])
    else:
        extracted = extract_recipe_ollama(recipe["cleaned_content"])

    result = {
        "source_file": filepath.name,
        "url": recipe["url"],
        "source": recipe["source"],
        "original_title": recipe["title"],
        "cleaned_content": recipe["cleaned_content"],
        "extracted": extracted,
    }

    # Save individual result
    output_path = output_dir / filepath.name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    is_recipe = extracted.get("est_une_recette", False)
    titre = extracted.get("titre", "-")
    print(f"  -> {'Recette' if is_recipe else 'Pas une recette'}: {titre}")
    print(f"  -> Sauvegardé: {output_path.name}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Extract recipes with Ollama/Mistral")
    parser.add_argument("--backend", choices=["ollama", "mistral"], default="ollama",
                        help="LLM backend: 'ollama' (local) or 'mistral' (API)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max number of recipes to process (0 = all remaining)")
    parser.add_argument("--filter", type=str, default="",
                        help="Only process files matching this substring")
    args = parser.parse_args()

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Backend: {args.backend}")
    if args.backend == "mistral":
        print(f"Modèle API: {MISTRAL_API_MODEL}")
    else:
        print(f"Modèle local: {OLLAMA_MODEL}")

    # Find files to process
    all_files = sorted(PROCESSED_DIR.glob("*.json"))

    todo = [f for f in all_files if not (EXTRACTED_DIR / f.name).exists()]
    if args.filter:
        todo = [f for f in todo if args.filter.lower() in f.name.lower()]

    if args.limit > 0:
        todo = todo[:args.limit]

    already_done = len(all_files) - len([f for f in all_files if not (EXTRACTED_DIR / f.name).exists()])
    print(f"Total fichiers: {len(all_files)}")
    print(f"Déjà extraits: {already_done}")
    print(f"À traiter: {len(todo)}")

    if not todo:
        print("Rien à faire !")
        return

    success = 0
    errors = 0
    for i, filepath in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}]", end="")
        try:
            process_file(filepath, EXTRACTED_DIR, args.backend)
            success += 1
        except json.JSONDecodeError as e:
            print(f"  ERREUR JSON: {e}")
            errors += 1
        except requests.RequestException as e:
            print(f"  ERREUR requête: {e}")
            errors += 1
            if args.backend == "ollama" and "Connection refused" in str(e):
                print("Ollama semble arrêté. Arrêt du traitement.")
                break
        except RuntimeError as e:
            print(f"  ERREUR: {e}")
            errors += 1
            break

    print(f"\n{'='*60}")
    print(f"Terminé: {success} réussites, {errors} erreurs")
    print(f"Total extraits: {success}/{len(all_files)}")


if __name__ == "__main__":
    main()
