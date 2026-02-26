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
| `ingredients_map.json` | Canonical ingredient names → list of display variants. Manually curated. |
| `ingredients_display.json` | Canonical names → display variants shown in the web UI chips. |
