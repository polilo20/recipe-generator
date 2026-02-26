"""Main scraper orchestrator for recipe collection."""
import argparse
import json
import os
from datetime import datetime
from typing import List, Dict
from scrapers import AVAILABLE_SCRAPERS


class RecipeScraper:
    """Main scraper class that orchestrates all individual scrapers."""

    def __init__(self, output_dir: str = "data/recipes"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def scrape_site(self, site_name: str, url: str, max_recipes: int = 1000) -> List[Dict]:
        """Scrape recipes from a specific site."""
        if site_name not in AVAILABLE_SCRAPERS:
            print(f"Error: No scraper available for '{site_name}'")
            print(f"Available scrapers: {', '.join(AVAILABLE_SCRAPERS.keys())}")
            return []

        scraper_class = AVAILABLE_SCRAPERS[site_name]
        scraper = scraper_class()

        print(f"\n{'='*60}")
        print(f"Starting to scrape: {scraper.name}")
        print(f"URL: {url}")
        print(f"{'='*60}\n")

        recipes = scraper.scrape_category(url, max_recipes=max_recipes)

        print(f"\nSaving {len(recipes)} recipes...")
        for recipe in recipes:
            recipe['scraped_at'] = datetime.now().isoformat()
            scraper.save_recipe(recipe, self.output_dir)

        print(f"✓ Saved {len(recipes)} recipes to {self.output_dir}")
        return recipes

    def scrape_all_configured_sites(self, config_file: str = "sites_config.json"):
        """Scrape all sites defined in a config file."""
        if not os.path.exists(config_file):
            print(f"Config file {config_file} not found.")
            return

        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        all_recipes = []
        for site in config.get('sites', []):
            if not site.get('enabled', True):
                continue
            site_name = site.get('name')
            url = site.get('url')
            max_recipes = site.get('max_recipes', 50)
            recipes = self.scrape_site(site_name, url, max_recipes)
            all_recipes.extend(recipes)

        return all_recipes


def main():
    parser = argparse.ArgumentParser(description='Scrape recipes from cooking blogs')
    parser.add_argument('--site', type=str, help='Site name (e.g., aufilduthym)')
    parser.add_argument('--url', type=str, help='URL to scrape')
    parser.add_argument('--max-recipes', type=int, default=50, help='Maximum recipes to scrape')
    parser.add_argument('--all', action='store_true', help='Scrape all sites from sites_config.json')
    parser.add_argument('--list-scrapers', action='store_true', help='List available scrapers')

    args = parser.parse_args()

    scraper = RecipeScraper()

    if args.list_scrapers:
        print("Available scrapers:")
        for name in AVAILABLE_SCRAPERS.keys():
            print(f"  - {name}")
        return

    if args.all:
        scraper.scrape_all_configured_sites()
    elif args.site and args.url:
        scraper.scrape_site(args.site, args.url, args.max_recipes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
