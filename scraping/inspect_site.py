"""Utility script to inspect website structure for building scrapers."""
import requests
from bs4 import BeautifulSoup
import json


def inspect_recipe_page(url: str):
    """Fetch and inspect a recipe page to help identify HTML selectors."""
    print(f"Fetching: {url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        print("="*60)
        print("STRUCTURE ANALYSIS")
        print("="*60)

        # Find potential title elements
        print("\n📋 POTENTIAL TITLES:")
        for tag in ['h1', 'h2']:
            elements = soup.find_all(tag)
            for elem in elements[:3]:  # Show first 3
                text = elem.text.strip()[:100]
                classes = elem.get('class', [])
                print(f"  {tag}.{'.'.join(classes)}: {text}")

        # Find potential ingredient lists
        print("\n🥕 POTENTIAL INGREDIENT SECTIONS:")
        for elem in soup.find_all(['ul', 'ol', 'div'], limit=10):
            classes = elem.get('class', [])
            class_str = '.'.join(classes) if classes else 'no-class'

            # Check if might contain ingredients
            text = elem.text.lower()
            if any(keyword in text for keyword in ['ingredient', 'ingrédient', 'g ', 'ml ', 'cuillère']):
                sample = elem.text.strip()[:150].replace('\n', ' ')
                print(f"  {elem.name}.{class_str}: {sample}...")

        # Find potential instruction sections
        print("\n📝 POTENTIAL INSTRUCTION SECTIONS:")
        for elem in soup.find_all(['ol', 'div', 'section'], limit=10):
            classes = elem.get('class', [])
            class_str = '.'.join(classes) if classes else 'no-class'

            text = elem.text.lower()
            if any(keyword in text for keyword in ['instruction', 'préparation', 'étape', 'step', 'recette']):
                if len(text) > 100:  # Likely a substantial section
                    sample = elem.text.strip()[:150].replace('\n', ' ')
                    print(f"  {elem.name}.{class_str}: {sample}...")

        # Find metadata (time, servings)
        print("\n⏱️  POTENTIAL METADATA:")
        for keyword in ['temps', 'time', 'personne', 'serving', 'difficulté', 'difficulty']:
            elements = soup.find_all(string=lambda text: keyword in text.lower() if text else False)
            for elem in elements[:3]:
                text = elem.strip()[:100]
                parent_tag = elem.parent.name if elem.parent else 'unknown'
                parent_class = '.'.join(elem.parent.get('class', [])) if elem.parent else ''
                print(f"  {parent_tag}.{parent_class}: {text}")

        # Find images
        print("\n🖼️  IMAGES:")
        images = soup.find_all('img', limit=5)
        for img in images:
            src = img.get('src', '')
            alt = img.get('alt', '')[:50]
            classes = '.'.join(img.get('class', []))
            if src and ('recipe' in src.lower() or 'recette' in src.lower() or classes):
                print(f"  img.{classes}: alt='{alt}', src='{src[:70]}...'")

        # Check for JSON-LD schema
        print("\n🔍 STRUCTURED DATA (JSON-LD):")
        json_ld = soup.find_all('script', type='application/ld+json')
        for script in json_ld:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Recipe':
                    print("  ✓ Found Recipe schema!")
                    print(f"    Keys: {', '.join(data.keys())}")
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Recipe':
                            print("  ✓ Found Recipe schema in list!")
                            print(f"    Keys: {', '.join(item.keys())}")
            except:
                pass

        print("\n" + "="*60)
        print("TIP: Use browser DevTools to inspect specific elements")
        print("="*60)

    except Exception as e:
        print(f"Error: {e}")


def find_recipe_links(listing_url: str):
    """Find all recipe links on a listing/category page."""
    print(f"Fetching listing page: {listing_url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(listing_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        print("="*60)
        print("FOUND LINKS (first 20):")
        print("="*60)

        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.strip()[:50]

            # Filter for likely recipe links
            if any(keyword in href.lower() for keyword in ['recette', 'recipe', '/20']):
                if not href.startswith('http'):
                    from urllib.parse import urljoin
                    href = urljoin(listing_url, href)
                links.add((href, text))

        for i, (link, text) in enumerate(sorted(links)[:20], 1):
            print(f"{i}. {text}")
            print(f"   {link}\n")

        print(f"Total unique recipe links found: {len(links)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Inspect single recipe: python inspect_site.py <recipe-url>")
        print("  Find recipe links:     python inspect_site.py <category-url> --links")
        print("\nExample:")
        print("  python inspect_site.py https://cuisine-addict.com/some-recipe")
        sys.exit(1)

    url = sys.argv[1]
    if '--links' in sys.argv:
        find_recipe_links(url)
    else:
        inspect_recipe_page(url)
