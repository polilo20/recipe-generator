# CWI — Cook With Ingredients

AI-powered French recipe generator. Pick ingredients from a web UI and get an original recipe generated from a curated dataset of French food blog recipes.

## How it works

```
User selects ingredients
        │
        ▼
Retrieval — find recipes in the dataset that share those ingredients
        │
        ▼
Generation — feed matched recipes as context to an LLM, ask it to create something new
        │
        ▼
New original recipe (in French)
```

The dataset was collected by scraping 3 French food blogs, then processed through an LLM (Mistral) to extract structured data (ingredients, times, tags, etc.).

## Project structure

```
cwi/
├── app/                        # Flask web application
│   ├── server.py               # API routes
│   ├── rag.py                  # Retrieval + generation pipeline
│   └── static/index.html       # Web UI
├── scraping/                   # Web scrapers (one per blog)
│   ├── scraper.py              # Orchestrator
│   ├── base_scraper.py         # Base class
│   ├── sites_config.json       # Which sites to scrape and how many recipes
│   └── scrapers/               # Per-site scraper modules
├── processing/                 # Data pipeline scripts
│   ├── preprocess_recipes.py   # Clean raw scraped content
│   ├── extract_recipes.py      # LLM extraction → structured JSON
│   ├── build_ingredients_map.py# Build canonical ingredient vocabulary
│   ├── normalize_ingredients.py# Map extracted ingredients to canonical names
│   ├── ingredients_map.json    # Canonical ingredient names + variants
│   └── ingredients_display.json# User-facing ingredient display variants
├── data/                       # Generated data (not in git — see pipeline below)
│   ├── raw/                    # Raw scraped pages
│   ├── processed/              # Cleaned content
│   ├── extracted/              # LLM-extracted structured recipes
│   └── recipes_normalized.json # Final dataset loaded by the app
├── requirements.txt            # App dependencies
└── .env                        # API keys (never committed)
```

## Getting started

The app runs entirely on your machine — Flask starts a local web server and serves both the API and the UI. No hosting required.

### Requirements

- Python 3.10+
- A [Mistral API key](https://console.mistral.ai/)

### Install

```bash
pip install -r requirements.txt
```

### Configure

Create a `.env` file at the project root:

```
MISTRAL_API_KEY=your_key_here
```

### Run

```bash
uvicorn app.server:app --reload
```

Then open [http://localhost:5000](http://localhost:5000) in your browser, pick ingredients, and click **Générer**. The recipe is generated on your machine and streamed back to the page — the only external call is to the Mistral API.

---

## Data pipeline

The full pipeline to go from zero to a working dataset:

### 1 — Scrape recipes

```bash
cd scraping
pip install -r requirements.txt
python scraper.py
```

Raw recipe pages are saved to `data/raw/` as JSON files. Configure which sites and how many recipes in `scraping/sites_config.json`.

### 2 — Clean content

```bash
python -m processing.preprocess_recipes
```

Strips navigation, comments, ads, and blog boilerplate. Output goes to `data/processed/`.

### 3 — Extract structured data

```bash
python -m processing.extract_recipes --backend mistral
# or: --backend ollama  (requires Ollama running locally)
```

Sends each recipe to an LLM, which returns structured JSON (title, ingredients with quantities, times, dietary tags, etc.). Results saved individually to `data/extracted/`.

### 4 — Build the ingredient map

```bash
python -m processing.build_ingredients_map
```

Scans extracted recipes to collect all ingredient names and adds new ones to `processing/ingredients_map.json`. Review and curate this file manually to merge synonyms.

### 5 — Normalize and compile

```bash
python -m processing.normalize_ingredients
```

Maps every extracted ingredient to its canonical name and writes the final `data/recipes_normalized.json`, which the Flask app loads on startup.

---

## RAG pipeline (CLI)

You can also run the RAG pipeline directly without the web server:

```bash
python -m app.rag
```

This prompts you to pick ingredients by number and prints the generated recipe to the terminal.

---

## Scraping

Sites are configured in `scraping/sites_config.json`. Each entry controls:
- `enabled` — whether to scrape this site
- `max_recipes` — how many recipes to collect

Currently enabled: clemfoodie, aufilduthym, cestmafournée.

---

## Acknowledgements

The dataset was built from recipes published on these three blogs. All original content belongs to their respective authors — this project uses it solely for personal, non-commercial experimentation.

- [Clemfoodie](https://www.clemfoodie.com/) by Clémence Catz
- [Au fil du Thym](https://aufilduthym.fr/) by Sandrine
- [C'est ma fournée !](https://www.cestmafournee.com/) by Valérie
