"""Utility to quickly create a new scraper for a site."""
import os
import re


SCRAPER_TEMPLATE = '''"""Scraper for {domain}"""
from base_scraper import BaseScraper
from typing import Dict, List


class {class_name}Scraper(BaseScraper):
    """Scraper for {site_name}."""

    def __init__(self):
        super().__init__(
            base_url="{base_url}",
            name="{site_name}"
        )

    # The base class handles everything by default.
    # Override extract_main_content() or find_recipe_links() only if needed.

    def scrape_category(self, category_url: str, max_recipes: int = 50, max_pages: int = 50) -> List[Dict]:
        """Scrape recipes from a category page with pagination support."""
        all_recipes = []
        visited_urls = set()

        print(f"\\nFinding recipe links with pagination: {{category_url}}")
        print(f"Target: {{max_recipes}} recipes, scanning up to {{max_pages}} pages\\n")

        # Use pagination-aware link finder
        recipe_links = self.find_all_recipe_links_with_pagination(category_url, max_pages=max_pages)

        print(f"\\nTotal recipe links found: {{len(recipe_links)}}")
        print(f"Will scrape up to {{max_recipes}} recipes\\n")

        for i, link in enumerate(recipe_links[:max_recipes], 1):
            if link in visited_urls:
                continue

            visited_urls.add(link)
            print(f"[{{i}}/{{min(max_recipes, len(recipe_links))}}] Scraping: {{link}}")

            recipe = self.extract_recipe(link)
            if recipe:
                all_recipes.append(recipe)
                print(f"  ✓ {{recipe['title'][:60]}}")
            else:
                print(f"  ✗ Failed to scrape")

            if len(all_recipes) >= max_recipes:
                break

        print(f"\\n{{'='*60}}")
        print(f"Successfully scraped {{len(all_recipes)}} recipes")
        print(f"{{'='*60}}")

        return all_recipes
'''


def create_scraper(base_url: str, site_name: str = None):
    """Create a new scraper file for a site."""
    # Extract domain from URL
    domain = base_url.replace('https://', '').replace('http://', '').split('/')[0]
    domain = domain.replace('www.', '')

    # Generate class name from domain
    class_name = ''.join(word.capitalize() for word in re.split(r'[.-]', domain.split('.')[0]))

    # Use domain as site name if not provided
    if not site_name:
        site_name = domain.split('.')[0].replace('-', ' ').title()

    # Generate file content
    content = SCRAPER_TEMPLATE.format(
        domain=domain,
        class_name=class_name,
        site_name=site_name,
        base_url=base_url.rstrip('/')
    )

    # Create filename
    filename = domain.split('.')[0].replace('-', '_') + '.py'
    filepath = os.path.join('scrapers', filename)

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Created scraper: {filepath}")
    print(f"  Class name: {class_name}Scraper")
    print(f"  Site name: {site_name}")
    print(f"\nNext steps:")
    print(f"1. Add to scrapers/__init__.py:")
    print(f"   from .{filename[:-3]} import {class_name}Scraper")
    print(f"   '{domain.split('.')[0]}': {class_name}Scraper,")
    print(f"\n2. Test it:")
    print(f"   python scraper.py --site {domain.split('.')[0]} --url {base_url} --max-recipes 5")


if __name__ == "__main__":
    import sys

    # Your list of sites
    sites = [
        ("https://cuisine-addict.com", "Cuisine Addict"),
        ("https://clemfoodie.com", "Clem Foodie"),
        ("https://lesfillesatable.com", "Les Filles à Table"),
        ("https://www.ladycoquillette.fr", "Lady Coquillette"),
        ("https://aufilduthym.fr", "Au Fil du Thym"),
        ("https://www.lesdelicesdekarinette.fr", "Les Délices de Karinette"),
        ("https://maisoncuilleret.fr", "Maison Cuilleret"),
        ("https://ottolenghi.co.uk", "Ottolenghi"),
        ("https://www.cuisineaz.com", "Cuisine AZ"),
        ("https://cuisine.journaldesfemmes.fr", "Journal des Femmes"),
        ("https://www.julieandrieu.com", "Julie Andrieu"),
        ("https://www.atelierdeschefs.fr", "L'Atelier des Chefs"),
        ("https://lacuisinedethomas.fr", "La Cuisine de Thomas"),
    ]

    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            print("Creating scrapers for all sites...\n")
            for base_url, site_name in sites:
                # Skip if already exists
                domain = base_url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                filename = domain.split('.')[0].replace('-', '_') + '.py'
                filepath = os.path.join('scrapers', filename)

                if os.path.exists(filepath):
                    print(f"⊘ Skipping {site_name} (already exists)")
                    continue

                create_scraper(base_url, site_name)
                print()
        else:
            # Create single scraper from command line
            base_url = sys.argv[1]
            site_name = sys.argv[2] if len(sys.argv) > 2 else None
            create_scraper(base_url, site_name)
    else:
        print("Usage:")
        print("  Create all scrapers:    python create_scraper.py --all")
        print("  Create single scraper:  python create_scraper.py <url> [site_name]")
        print("\nExample:")
        print("  python create_scraper.py https://example.com 'Example Site'")
