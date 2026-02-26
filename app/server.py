"""Minimal Flask server for ingredient selection and recipe generation."""

from flask import Flask, jsonify, request, send_from_directory
from app.rag import load_recipes, retrieve, generate

app = Flask(__name__, static_folder="static")
app.json.sort_keys = False

# ---------------------------------------------------------------------------
# Category mapping — each canonical ingredient → category
# ---------------------------------------------------------------------------

CATEGORIES = {
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

# Build reverse lookup: canonical → category
_INGREDIENT_TO_CATEGORY: dict[str, str] = {}
for _cat, _ingredients in CATEGORIES.items():
    for _ing in _ingredients:
        _INGREDIENT_TO_CATEGORY[_ing] = _cat


def _get_category(canonical: str) -> str:
    return _INGREDIENT_TO_CATEGORY.get(canonical, "Autres")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/ingredients")
def api_ingredients():
    """Return ingredients grouped by category.

    Each entry is a single clickable term with its canonical key:
    { "Légumes": [{"display": "...", "canonical": "..."}], ... }
    """
    from app.rag import INGREDIENTS_DISPLAY_PATH
    import json as _json
    with open(INGREDIENTS_DISPLAY_PATH, encoding="utf-8") as f:
        display_map = _json.load(f)

    grouped: dict[str, list] = {}
    for canonical, variants in sorted(display_map.items()):
        cat = _get_category(canonical)
        entries = grouped.setdefault(cat, [])
        # Canonical term first, then each variant — one button per term
        entries.append({"display": canonical, "canonical": canonical})
        for v in variants:
            entries.append({"display": v, "canonical": canonical})

    for cat in grouped:
        grouped[cat].sort(key=lambda x: x["display"].lower())

    # Sort categories in the predefined order
    cat_order = list(CATEGORIES.keys())
    ordered = {}
    for cat in cat_order:
        if cat in grouped:
            ordered[cat] = grouped[cat]
    for cat in grouped:
        if cat not in ordered:
            ordered[cat] = grouped[cat]

    return jsonify(ordered)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Receive selected ingredients as {display, canonical} objects, run RAG, return recipe.

    Body: {"ingredients": [{"display": "...", "canonical": "..."}, ...], "backend": "mistral"}
    - canonical (deduplicated) → used for retrieve()
    - display terms → used for generate() (star ingredients in the prompt)
    """
    data = request.get_json(force=True)
    ingredients = data.get("ingredients", [])

    if not ingredients:
        return jsonify({"error": "Aucun ingrédient sélectionné"}), 400

    display_terms = [ing["display"] for ing in ingredients]
    canonical_terms = list(dict.fromkeys(ing["canonical"] for ing in ingredients))

    recipes = load_recipes()
    matched = retrieve(recipes, canonical_terms)

    if not matched:
        return jsonify({"error": "Aucune recette trouvée pour ces ingrédients."}), 404

    result = generate(display_terms, matched)
    return jsonify({"recipe": result})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
