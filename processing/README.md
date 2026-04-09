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
Flattens `ingredients_map.json` into a variant→canonical lookup and applies it to every recipe in `data/extracted/`, adding a new key storing
the new normalized names for raw `ingredients_normalises`. Writes the final compiled dataset to `data/recipes_normalized.json`.

```bash
python -m processing.normalize_ingredients
```

## `ingredients_map.json` structure

Each entry is a normalized ingredient name (the key shown to users in the UI) mapped to an object with three fields:

```json
"lentille corail": {
  "normalizing": ["lentilles corail", "lentilles roses"],
  "category": "Légumineuses",
  "weight": "main"
}
```

### `normalizing`
List of surface variants that should resolve to this normalized name during retrieval (e.g. plurals, common misspellings, LLM inconsistencies, but also
other ingredients that can be used interchangeably). Used by `normalize_ingredients.py` to map raw extracted ingredient names to their canonical form.

### `category`
UI display category, used to group ingredient chips in the web interface. Categories are **manually assigned**. 

### `weight`
Retrieval weight for the RAG pipeline. Three values:

| Value | Meaning | Examples |
|-------|---------|---------|
| `"base"` | Structural, neutral — provides the canvas but doesn't define the dish | flour, pasta, butter, eggs, sugar, milk, bouillon |
| `"flavoring"` | Pantry staple that adds character — you likely have it on hand, but it shapes the style rather than naming the dish | garlic, spices, herbs, alcohol, vinegar, cheese, nuts, olive oil |
| `"main"` | The star — its presence names or defines the dish | meat, fish, vegetables, fresh fruit, legumes, chocolate |

**Rationale:** retrieval ranks recipes by ingredient overlap. Without weighting, a recipe matching on "sel + poivre + farine" scores as high as one matching on "saumon + épinard". `weight` lets the pipeline prioritise matches on `main` ingredients and treat `base`/`flavoring` matches as secondary signals.

