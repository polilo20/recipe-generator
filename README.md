# CWI — Cook With Intention

AI-powered French recipe generator. Pick ingredients from a web UI and get an original recipe generated from a curated dataset of French food blog recipes, mostly vegetarian and mediterranean style.

**Live app:** https://cwi-app-1039654689601.europe-west1.run.app

## How it works

```
User selects ingredients
        │
        ▼
Retrieval — recipes are retrieved based on how many ingredients they have in common with user choices
        │
        ▼
Generation — feed matched recipes and ingredients chosen by the user as context to an LLM, ask it to create something new
        │
        ▼
New original recipe (in French)
```

The dataset was collected by scraping 3 French food blogs, then processed through an LLM (Mistral) to extract structured data (ingredients, times, tags, etc.).

## Project structure

```
cwi/
├── app/                        # FastAPI web application
│   ├── server.py               # API routes
│   ├── rag.py                  # Retrieval + generation pipeline
│   ├── eval.py                 # Basic evaluation of RAG pipeline
│   └── static/index.html       # Web UI
├── scraping/                   # Web scrapers (one per blog)
│   ├── scraper.py              # Orchestrator
│   ├── base_scraper.py         # Base class
│   ├── sites_config.json       # Which sites to scrape and how many recipes
│   └── scrapers/               # Per-site scraper modules
├── processing/                 # Data pipeline scripts
│   ├── preprocess_recipes.py   # Clean raw scraped content
│   ├── extract_recipes.py      # LLM extraction → structured JSON
│   ├── build_ingredients_map.py# Help to build canonical ingredient vocabulary
│   ├── normalize_ingredients.py# Map extracted ingredients to canonical names
│   └── ingredients_map.json    # Canonical ingredient names + variants
├── data/                       # Generated data (not in git — see pipeline below)
│   ├── raw/                    # Raw scraped pages
│   ├── processed/              # Cleaned content
│   ├── extracted/              # LLM-extracted structured recipes
│   └── recipes_normalized.json # Final dataset loaded by the app
├── requirements.txt            # App dependencies
└── .env                        # API keys (never committed)
```

## Run locally

### Requirements

- A [Mistral API key](https://console.mistral.ai/)

### Configure

Create a `.env` file at the project root:

```
MISTRAL_API_KEY=your_key_here
API_KEY=your_api_key_here        # any string you choose — protects the /api routes from bot abuse
```

### Run with Docker (recommended)

- [Docker](https://www.docker.com/) installed and running

```bash
docker compose up --build
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### Run locally (without Docker)

- Python 3.10+

```bash
pip install -r requirements.txt
uvicorn app.server:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

Pick ingredients and click **Générer**. The only external call is to the Mistral API.

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
