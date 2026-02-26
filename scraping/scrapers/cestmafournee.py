"""Scraper for chttps://www.cestmafournee.com"""
from base_scraper import BaseScraper
from typing import Dict, List


class CestmaFourneeScraper(BaseScraper):
    """Scraper for Cuisine AZ."""

    def __init__(self):
        super().__init__(
            base_url="https://www.cestmafournee.com/2011/10/le-sale.html",
            name="Cest ma fournee"
        )

    # The base class handles everything by default.
    # Override extract_main_content() or find_recipe_links() only if needed.

    def scrape_category(self, category_url: str, max_recipes: int = 50, max_pages: int = 50) -> List[Dict]:
        """Scrape recipes from a category page with pagination support."""
        all_recipes = []
        visited_urls = set()

        print(f"\nFinding recipe links with pagination: {category_url}")
        print(f"Target: {max_recipes} recipes, scanning up to {max_pages} pages\n")

        # Use pagination-aware link finder
        recipe_links = self.find_all_recipe_links_with_pagination(category_url, max_pages=max_pages)

        print(f"\nTotal recipe links found: {len(recipe_links)}")
        print(f"Will scrape up to {max_recipes} recipes\n")

        for i, link in enumerate(recipe_links[:max_recipes], 1):
            if link in visited_urls:
                continue

            visited_urls.add(link)
            print(f"[{i}/{min(max_recipes, len(recipe_links))}] Scraping: {link}")

            recipe = self.extract_recipe(link)
            if recipe:
                all_recipes.append(recipe)
                print(f"  ✓ {recipe['title'][:60]}")
            else:
                print(f"  ✗ Failed to scrape")

            if len(all_recipes) >= max_recipes:
                break

        print(f"\n{'='*60}")
        print(f"Successfully scraped {len(all_recipes)} recipes")
        print(f"{'='*60}")

        return all_recipes
