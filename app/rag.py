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

# ---------------------------------------------------------------------------
# Ingredient categories
# ---------------------------------------------------------------------------

CATEGORIES: dict[str, list[str]] = {
    "Légumes": [
        "artichaut", "asperge", "aubergine", "betterave", "betterave jaune",
        "blette", "brocoli", "butternut", "carotte", "chou", "chou blanc",
        "chou chinois", "chou de bruxelles", "chou kale", "chou rouge",
        "chou-fleur", "concombre", "courgette", "courge", "céleri",
        "céleri rave", "endive", "fenouil", "haricot vert", "navet",
        "oignon", "oignon blanc", "oignon doux", "oignon jaune",
        "oignon nouveau", "oignon rouge", "petit pois", "poireau",
        "poivron", "pomme de terre", "patate douce", "potimarron",
        "potiron", "radis", "radis noir", "tomate", "tomate cerise",
        "tomate séchée", "épinard", "chicorée rouge", "cébette",
        "échalote", "fanes de légumes", "mâche", "mesclun", "roquette",
        "salade",
        "champignon", "champignon de paris", "champignon des bois",
    ],
    "Fruits": [
        "abricot", "ananas", "avocat", "banane", "cerise", "clémentine",
        "coing", "datte", "figue", "fraise", "framboise", "fruit de la passion",
        "fruits rouges", "grenade", "groseille", "kaki", "kiwi", "mangue",
        "melon", "mirabelle", "nectarine", "orange", "orange sanguine",
        "pamplemousse", "pastèque", "poire", "pomme", "prune", "pêche",
        "raisin", "rhubarbe", "citron", "citron confit", "citron vert",
        "baies noires",
    ],
    "Viandes & Poissons": [
        "agneau", "anchois", "boeuf", "boeuf hâché", "cabillaud", "chorizo",
        "crevette", "gambas", "jambon cru", "jambon cuit", "langoustine",
        "lard fumé", "noix de saint-jacques", "oeuf de saumon/truite",
        "saucisse", "saumon", "saumon fumé", "thon", "volaille",
    ],
    "Produits laitiers": [
        "beaufort", "bleu", "beurre", "beurre clarifié", "beurre demi-sel",
        "burrata", "crème fleurette", "crème fraîche", "crème liquide",
        "emmental", "faisselle", "feta", "fromage blanc", "fromage de brebis",
        "fromage de chèvre", "fromage de vache", "fromage frais",
        "fromage râpé", "gorgonzola", "gruyère", "halloumi", "mascarpone",
        "mozzarella", "parmesan", "pecorino", "petit suisse", "ricotta",
        "roquefort", "skyr", "yaourt", "yaourt de brebis", "yaourt grec",
        "lait", "lait concentré sucré", "lait en poudre", "lait fermenté",
    ],
    "Féculents & Céréales": [
        "boulghour", "cannelloni", "flocon de céréale", "linguine",
        "macaroni", "nouilles", "pain", "pain de mie", "pain pita",
        "petit épeautre", "petites pâtes de blé/sarrasin dur", "polenta",
        "pâtes", "quinoa", "riz", "riz basmati", "riz risotto", "sarrasin",
        "semoule", "spaghetti",
    ],
    "Légumineuses": [
        "flageolet", "fève", "haricot blanc", "haricot rouge",
        "lentille beluga", "lentille corail", "lentille verte",
        "légumineuses anciennes", "pois cassé", "pois chiche",
    ],
    "Herbes": [
        "ail des ours", "aneth", "basilic", "bouquet garni", "cerfeuil",
        "ciboulette", "coriandre", "estragon", "herbes de provence",
        "lavande", "menthe", "origan", "persil", "romarin", "sauge",
        "thym", "verveine",
    ],
    "Épices & Condiments": [
        "ail", "ail en poudre", "badiane", "baies roses", "cannelle",
        "cardamome", "citronnelle", "clou de girofle", "concentré de tomate",
        "coriandre en poudre", "cornichon", "cumin", "curcuma", "curry",
        "câpre", "fleur de sel", "gingembre", "gingembre en poudre",
        "graine de moutarde", "harissa", "miso", "moutarde",
        "moutarde à l'ancienne", "muscade", "olive noire", "olive verte",
        "paprika", "paprika fumé", "piment", "piment d'espelette",
        "piment de cayenne", "poivre", "purée de tomates", "quatre-épices",
        "ras el hanout", "safran", "sauce soja", "sel", "tabasco",
        "tahini", "tomate concassée", "tomate pelée", "zaatar",
        "épices pour pain d'épices",
    ],
    "Huiles & Matières grasses": [
        "huile d'olive", "huile de coco", "huile de noix", "huile de sésame",
        "huile neutre", "margarine", "mayonnaise",
    ],
    "Fruits secs & Graines": [
        "amande", "amande effilée", "amande en poudre", "beurre de cacahuète",
        "cacahuète", "graine de courge", "graine de lin", "graine de pavot",
        "graine de sésame", "graine de tournesol", "noisette",
        "noisette en poudre", "noix", "noix de cajou", "noix de coco",
        "noix de pécan", "pignon de pin", "pistache", "pistache en poudre",
        "raisin sec", "éclat de pistache",
    ],
    "Sucres & Pâtisserie": [
        "agar-agar", "arôme amande amère", "arôme fleur d'oranger",
        "arôme vanille", "beurre de cacao", "bicarbonate", "biscuit à la cuillère",
        "cacao en poudre", "café", "caramel", "cassonade", "chapelure",
        "chocolat au lait", "chocolat blanc", "chocolat noir", "colorant alimentaire",
        "confiture", "crème de marrons", "crêpes dentelles",
        "farine", "farine d'amande", "farine de blé t45", "farine de blé t55",
        "farine de blé t65", "farine de blé t80", "farine de châtaigne",
        "farine de coco", "farine de petit épeautre", "farine de pois chiche",
        "farine de sarrasin", "farine de seigle", "farine de teff",
        "feuille de gélatine", "fève tonka", "fécule de pomme de terre",
        "gousse de vanille", "lait de coco", "lait végétal",
        "levure boulangère", "levure chimique", "maizena",
        "marmelade d'orange", "miel", "mélasse", "pâte brisée",
        "pâte d'amande", "pâte de pistache", "pâte feuilletée", "pâte filo",
        "pâte à tartiner", "pectine", "poudre à crème", "praliné",
        "psyllium", "pépites de chocolat", "sablé", "sirop d'érable",
        "sirop sucrant", "sucre", "sucre complet", "sucre de coco",
        "sucre glace", "sucre inverti", "sucre vanillé", "vanille",
        "éclat de fève de cacao",
    ],
    "Alcools & Vinaigres": [
        "bière", "crémant", "eau de vie", "kirsch", "rhum", "vin blanc",
        "crème de balsamique", "vinaigre balsamique", "vinaigre blanc",
        "vinaigre de cidre", "vinaigre de riz", "vinaigre de vin",
        "vinaigre de xérès",
    ],
    "Autres": [
        "bouillon de légumes", "bouillon de volaille", "eau",
        "feuille de laurier", "tofu",
    ],
}

# Build reverse lookup: canonical ingredient → category
_INGREDIENT_TO_CATEGORY: dict[str, str] = {
    ing: cat
    for cat, ingredients in CATEGORIES.items()
    for ing in ingredients
}


def get_category(canonical: str) -> str:
    return _INGREDIENT_TO_CATEGORY.get(canonical, "Autres")

GENERATION_PROMPT = """\
Tu es un chef cuisinier.

Tu dois faire une recette contenant ces ingrédients : {star_ingredients}

Première étape : prends connaissance de {star_ingredients} et de {ingredients_map} et comprends quels sont les ingrédients que tu peux utiliser de façon interchangeable. 

Seconde étape : prends connaissance des recettes suivantes. Comprends leur style et leur intention : 

{matched_recipes}

Troisième étape : combine ce que tu as appris lors des deux dernières étapes, et uniquement cela, pour proposer une nouvelle recette. 
Cette recette doit absolument citer tous ces ingrédients : {star_ingredients}. Tu ne dois utiliser aucune connaissance hors de ce qui a déjà été fourni.
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
    """Format recipe cleaned_content for the prompt (kept for reference/baseline)."""
    # Should ingredients be outlined here ?
    parts = []
    for i, r in enumerate(recipes[:max_recipes], 1):
        title = r["extracted"].get("titre", r.get("original_title", "Sans titre"))
        parts.append(f"### Recette {i} : {title}\n{r['cleaned_content']}\n")
    return "\n".join(parts)


def _call_mistral(prompt: str, temperature: float = 0.4, max_tokens: int = 2048) -> str:
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


def generate(chosen_ingredients: list[str], matched_recipes: list[dict], ingredients_map: dict | None = None) -> str:
    """Generate a recipe grounded in corpus ingredients with LLM-chosen technique."""
    if ingredients_map is None:
        with open(INGREDIENTS_MAP_PATH, encoding="utf-8") as f:
            ingredients_map = json.load(f)

    prompt = GENERATION_PROMPT.format(
        star_ingredients=", ".join(chosen_ingredients),
        matched_recipes=_build_recipes_block(matched_recipes),
        ingredients_map=json.dumps(ingredients_map, ensure_ascii=False),
    )
    return _call_mistral(prompt, temperature=0.1, max_tokens=2048)


def generate_without_context(chosen_ingredients: list[str]) -> str:
    """Generate a recipe with NO reference recipes (baseline)."""
    prompt = GENERATION_PROMPT.format(
        star_ingredients=", ".join(chosen_ingredients),
        matched_recipes="",
        ingredients_map="",
    )
    return _call_mistral(prompt, temperature=0.1, max_tokens=2048)


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

    # --- Show all recipes fed to the LLM ---
    print(f"\n{'='*60}")
    print("RECETTES ENVOYÉES AU LLM")
    print(f"{'='*60}")
    print(_build_recipes_block(matched))

    print(f"\n{'='*60}")
    print(f"Génération avec Mistral API...")
    print(f"{'='*60}")
    result = generate(selected, matched)
    print(f"\n{'='*60}")
    print("RECETTE GÉNÉRÉE")
    print(f"{'='*60}")
    print(result)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
