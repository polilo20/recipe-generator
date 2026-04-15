"""FastAPI server for ingredient selection and recipe generation."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag import load_recipes, load_ingredients_data, retrieve, generate

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI()

recipes = load_recipes()
ingredients_data = load_ingredients_data()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/ingredients")
def api_ingredients():
    """Return ingredients grouped by category, sorted alphabetically within each group."""
    grouped: dict[str, list[str]] = {}
    for key, data in ingredients_data.items():
        grouped.setdefault(data["category"], []).append(key)

    for cat in grouped:
        grouped[cat].sort(key=str.lower)

    return JSONResponse(content=grouped)


class GenerateRequest(BaseModel):
    ingredients: list[str]


@app.post("/api/generate")
def api_generate(body: GenerateRequest):
    """Receive selected ingredient keys, run RAG pipeline, return generated recipe."""
    if not body.ingredients:
        raise HTTPException(status_code=400, detail="Aucun ingrédient sélectionné")

    ingredients = list(dict.fromkeys(body.ingredients))
    matched = retrieve(recipes, ingredients, ingredients_data)

    if not matched:
        raise HTTPException(status_code=404, detail="Aucune recette trouvée pour ces ingrédients.")

    result = generate(ingredients, matched, ingredients_data)
    return {"recipe": result}


# ---------------------------------------------------------------------------
# Static files — must be mounted after API routes
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
