# Processing pipeline

Scripts to transform raw scraped pages into the normalized recipe dataset used by the app.

## Order of execution

```
data/raw/          (produced by scraping/scraper.py)
    │
    ▼  preprocess_recipes.py
data/processed/
    │
    ▼  extract_recipes.py   (calls LLM)
data/extracted/
    │
    ├─▶ build_ingredients_map.py  →  ingredients_map.json   (manual curation step)
    │
    ▼  normalize_ingredients.py
data/recipes_normalized.json
```

## Scripts

### `preprocess_recipes.py`
Cleans raw scraped content per source: removes navigation bars, social buttons, comment sections, and other non-recipe noise. One cleaner function per blog.

```bash
python -m processing.preprocess_recipes
```

### `extract_recipes.py`
Sends cleaned content to an LLM (Ollama or Mistral API) and asks it to return a structured JSON with: title, category, ingredients with quantities, cooking times, difficulty, dietary flags (vegan, gluten-free, etc.), and a normalized ingredient list.

```bash
python -m processing.extract_recipes --backend mistral  # cloud
python -m processing.extract_recipes --backend ollama   # local
python -m processing.extract_recipes --limit 20         # process only 20 files
python -m processing.extract_recipes --filter "Clem"    # filter by filename
```

Results are saved individually in `data/extracted/` so the script is safely resumable.

### `build_ingredients_map.py`
Scans `data/extracted/` and collects every unique ingredient name produced by the LLM. Any name not already in `ingredients_map.json` is appended as a new canonical entry with an empty variants list.

```bash
python -m processing.build_ingredients_map
```

After running, **manually review `ingredients_map.json`** to:
- Merge synonyms (e.g. `"oeuf"` variants: `["oeufs", "oeuf entier"]`)
- Fix LLM inconsistencies (plurals, typos, overly specific names)

### `normalize_ingredients.py`
Flattens `ingredients_map.json` into a variant→canonical lookup and applies it to every recipe in `data/extracted/`, replacing the raw `ingredients_normalises` list with canonical names. Writes the final compiled dataset to `data/recipes_normalized.json`.

```bash
python -m processing.normalize_ingredients
```

## Key data files

| File | Description |
|------|-------------|
| `ingredients_map.json` | Single source of truth for all ingredient metadata. Manually curated. |

`ingredients_display.json` is no longer used — its role has been merged into `ingredients_map.json`.

## `ingredients_map.json` structure

Each entry is a canonical ingredient name (the key shown to users in the UI) mapped to an object with three fields:

```json
"lentille corail": {
  "also retrieved": ["lentilles corail", "lentilles roses"],
  "category": "Légumineuses",
  "weight": "main"
}
```

### `also retrieved`
List of surface variants that should resolve to this canonical name during retrieval (e.g. plurals, common misspellings, LLM inconsistencies). Used by `normalize_ingredients.py` to map raw extracted ingredient names to their canonical form.

### `category`
UI display category, used to group ingredient chips in the web interface. Categories are **manually assigned** — see `app/rag.py` for the full list. When adding a new ingredient, pick the closest existing category.

### `weight`
Retrieval weight for the RAG pipeline. Three values:

| Value | Meaning | Examples |
|-------|---------|---------|
| `"base"` | Structural, neutral — provides the canvas but doesn't define the dish | flour, pasta, butter, eggs, sugar, milk, bouillon |
| `"flavoring"` | Pantry staple that adds character — you likely have it on hand, but it shapes the style rather than naming the dish | garlic, spices, herbs, alcohol, vinegar, cheese, nuts, olive oil, chocolate chips |
| `"main"` | The star — its presence names or defines the dish | meat, fish, vegetables, fresh fruit, legumes, chocolate (as a main component) |

**Rationale:** retrieval ranks recipes by ingredient overlap. Without weighting, a recipe matching on "sel + poivre + farine" scores as high as one matching on "saumon + épinard". `weight` lets the pipeline prioritise matches on `main` ingredients and treat `base`/`flavoring` matches as secondary signals.

**Edge cases to keep in mind:**
- Cheeses are `flavoring` — they add character but the dish is rarely *called* a cheese dish in the same way it's called a salmon dish. Exception: if you add a dedicated "cheese board" category one day, revisit.
- Citrus (lemon, lime) is `flavoring` — it seasons and brightens, but a tarte au citron is defined by the lemon *as flavoring* the cream, not as a raw fruit.
- Specialty flours (sarrasin, châtaigne) are `flavoring` — they carry a distinct regional identity that defines the recipe type (galettes bretonnes, etc.), unlike neutral white flour.
- Onions, shallots, cébette, céleri are `flavoring` — they build the aromatic base but rarely name the dish.
- Lardons, chorizo, anchois are `flavoring` — used to season rather than as the primary protein.
