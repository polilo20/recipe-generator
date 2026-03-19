"""Minimal Flask server for ingredient selection and recipe generation."""

from flask import Flask, jsonify, request, send_from_directory
from app.rag import load_recipes, retrieve, generate, CATEGORIES, get_category

app = Flask(__name__, static_folder="static")
app.json.sort_keys = False


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
        cat = get_category(canonical)
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
