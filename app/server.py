"""FastAPI server for ingredient selection and recipe generation."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Annotated

from app.rag import (
    MistralQuotaError,
    MistralUnavailableError,
    generate,
    load_ingredients_data,
    load_recipes,
    retrieve,
)

_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.INFO)
_app_logger.addHandler(logging.StreamHandler())
_app_logger.propagate = False

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI()

recipes = load_recipes()
ingredients_data = load_ingredients_data()


# ---------------------------------------------------------------------------
# API key dependency
# ---------------------------------------------------------------------------

def _check_api_key(x_api_key: str | None = None) -> None:
    """Reject requests that don't carry the correct X-API-Key header.

    If API_KEY env var is not set, the check is skipped (useful for local dev).
    """
    expected = os.environ.get("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    """Serve the UI, injecting the API key so the frontend can authenticate."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    api_key = os.environ.get("API_KEY", "")
    html = html.replace("__API_KEY_PLACEHOLDER__", api_key)
    return HTMLResponse(content=html)


@app.get("/api/ingredients")
def api_ingredients(x_api_key: Annotated[str | None, Header()] = None):
    """Return ingredients grouped by category, sorted alphabetically within each group."""
    _check_api_key(x_api_key)
    grouped: dict[str, list[str]] = {}
    for key, data in ingredients_data.items():
        grouped.setdefault(data["category"], []).append(key)

    for cat in grouped:
        grouped[cat].sort(key=str.lower)

    return JSONResponse(content=grouped)


class GenerateRequest(BaseModel):
    ingredients: list[str]


@app.post("/api/generate")
def api_generate(body: GenerateRequest, x_api_key: Annotated[str | None, Header()] = None):
    """Receive selected ingredient keys, run RAG pipeline, return generated recipe."""
    _check_api_key(x_api_key)

    if not body.ingredients:
        raise HTTPException(status_code=400, detail="Aucun ingrédient sélectionné")

    ingredients = list(dict.fromkeys(body.ingredients))
    logger.info("Selected ingredients: %s", ingredients)

    matched = retrieve(recipes, ingredients, ingredients_data)

    if not matched:
        logger.info("No matching recipes for ingredients: %s", ingredients)
        raise HTTPException(status_code=404, detail="Aucune recette trouvée pour ces ingrédients.")

    titles = [r["extracted"].get("titre", r.get("original_title", "?")) for r in matched]
    logger.info("Matched recipes (%d): %s", len(matched), titles)

    try:
        result = generate(ingredients, matched, ingredients_data)
    except MistralQuotaError as e:
        logger.error("Mistral quota exceeded: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except MistralUnavailableError as e:
        logger.error("Mistral unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))

    return {"recipe": result}


# ---------------------------------------------------------------------------
# Static files — must be mounted after API routes
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
