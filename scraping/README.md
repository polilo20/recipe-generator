# Scraping

Web scrapers for collecting recipes from French food blogs. Each scraper extracts the full page text (no CSS-selector magic) and saves it as raw JSON for later LLM processing.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Scrape all configured sites (see sites_config.json)
python scraper.py --all

# Scrape a single site
python scraper.py --site aufilduthym --url "https://aufilduthym.fr/category/recettes" --max-recipes 50

# List available scrapers
python scraper.py --list-scrapers
```

Must be run from the `scraping/` directory.

## Configured sites

See `sites_config.json`. Currently: **aufilduthym**, **clemfoodie**, **cestmafournee**.

## Adding a new scraper

```bash
python create_scraper.py "https://newsite.com" "Site Name"
```

This generates a scraper in `scrapers/` using the base class defaults. Override `extract_main_content()` or `find_recipe_links()` only if the defaults don't work for a given site.

## Output format

Each recipe is saved as a JSON file in `data/raw/`:

```json
{
  "url": "https://...",
  "source": "Site Name",
  "title": "Recipe Title",
  "raw_content": "Full text content...",
  "scraped_at": "2026-01-29T..."
}
```

These files are the input for `processing/preprocess_recipes.py`.
