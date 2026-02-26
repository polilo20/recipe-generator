"""Quick test script to verify pagination works."""
from scrapers.clemfoodie import ClemfoodieScraper

def test_pagination():
    """Test pagination on clemfoodie."""
    scraper = ClemfoodieScraper()

    # Test URL from user
    test_url = "https://clemfoodie.com/category/recettes/"

    print("="*60)
    print("TESTING PAGINATION")
    print("="*60)
    print(f"\nTesting pagination on: {test_url}")
    print("This should find recipes across multiple pages...\n")

    # Find all links with pagination (limit to 3 pages for testing)
    recipe_links = scraper.find_all_recipe_links_with_pagination(test_url, max_pages=3)

    print("\n" + "="*60)
    print(f"RESULTS: Found {len(recipe_links)} total recipe links")
    print("="*60)

    if len(recipe_links) > 24:
        print("✓ SUCCESS! Found more than 24 recipes (pagination is working)")
        print(f"\nFirst 10 links:")
        for i, link in enumerate(recipe_links[:10], 1):
            print(f"  {i}. {link}")
    else:
        print("✗ Only found 24 or fewer recipes - pagination may not be working")

    return recipe_links

if __name__ == "__main__":
    links = test_pagination()

    print("\n" + "="*60)
    print("NEXT STEP: Scrape a few recipes to test")
    print("="*60)

    response = input("\nScrape 3 recipes as a test? (y/n): ")
    if response.lower() == 'y':
        scraper = ClemfoodieScraper()
        for i, link in enumerate(links[:3], 1):
            print(f"\n[{i}/3] Scraping: {link}")
            recipe = scraper.extract_recipe(link)
            if recipe:
                print(f"  ✓ {recipe['title']}")
            else:
                print(f"  ✗ Failed")
