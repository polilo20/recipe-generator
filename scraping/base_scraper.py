"""Base scraper class with common functionality for recipe scraping."""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import time
import json
from datetime import datetime


class BaseScraper:
    """Base class for all recipe scrapers."""

    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_page(self, url: str, delay: float = 1.0) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object."""
        try:
            time.sleep(delay)  # Be respectful to servers
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content text from a page. Override for site-specific logic."""
        # Try to find main content area with common selectors
        content_selectors = [
            'article',
            '[class*="content"]',
            '[class*="post"]',
            '[class*="recipe"]',
            '[class*="entry"]',
            'main',
        ]

        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                # Remove script, style, and nav elements
                for tag in content.find_all(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                return content.get_text(separator='\n', strip=True)

        # Fallback: get body text
        return soup.get_text(separator='\n', strip=True)

    def extract_recipe(self, url: str) -> Optional[Dict]:
        """Extract recipe from a single recipe page."""
        soup = self.fetch_page(url)
        if not soup:
            return None

        try:
            # Extract title (common across most sites)
            title_elem = soup.find('h1')
            title = title_elem.text.strip() if title_elem else url.split('/')[-1]

            # Extract all main content
            content = self.extract_main_content(soup)

            # Get meta description if available
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''

            # Get og:image if available
            og_image = soup.find('meta', property='og:image')
            image_url = og_image.get('content', '') if og_image else ''

            return {
                'url': url,
                'source': self.name,
                'title': title,
                'raw_content': content,
                'description': description,
                'image_url': image_url,
                'scraped_at': datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error extracting recipe from {url}: {e}")
            return None

    def find_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Find the next page URL for pagination. Override for site-specific logic."""
        # Common pagination patterns
        next_patterns = [
            ('a', {'class': 'next'}),
            ('a', {'class': 'next-page'}),
            ('a', {'rel': 'next'}),
            ('a', {'class': 'pagination__next'}),
            ('link', {'rel': 'next'}),
        ]

        for tag, attrs in next_patterns:
            next_link = soup.find(tag, attrs)
            if next_link and next_link.get('href'):
                href = next_link['href']
                # Convert relative to absolute URL
                if href.startswith('/'):
                    return self.base_url.rstrip('/') + href
                elif href.startswith('http'):
                    return href

        # Try finding links with "next" or "suivant" text
        for link in soup.find_all('a', href=True):
            text = link.text.lower().strip()
            if text in ['next', 'suivant', 'suivante', '→', '»', 'older']:
                href = link['href']
                if href.startswith('/'):
                    return self.base_url.rstrip('/') + href
                elif href.startswith('http'):
                    return href

        return None

    def find_recipe_links(self, page_url: str) -> List[str]:
        """Find all recipe links on a page. Override in subclasses if needed."""
        soup = self.fetch_page(page_url)
        if not soup:
            return []

        links = []
        base_domain = self.base_url.replace('https://', '').replace('http://', '').split('/')[0]

        for link in soup.find_all('a', href=True):
            href = link['href']

            # Skip anchors/fragments (like #comment-123)
            if href.startswith('#'):
                continue

            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = self.base_url.rstrip('/') + href
            elif not href.startswith('http'):
                continue

            # Remove fragment identifier (everything after #) to avoid duplicates
            if '#' in href:
                href = href.split('#')[0]

            # Skip if empty after removing fragment
            if not href:
                continue

            # Only keep links from the same domain
            if base_domain in href and href not in links:
                # Filter out obvious non-recipe pages
                skip_keywords = [
                    'category', 'tag', 'author', 'page', 'search', 'contact',
                    'about', 'mentions-legales', 'comment', 'respond', 'reply',
                    'feed', 'rss', 'trackback', 'wp-login', 'wp-admin',
                    'pinterest', 'facebook', 'twitter', 'instagram', 'whatsapp',
                    'share', 'print', 'email'
                ]
                if not any(keyword in href.lower() for keyword in skip_keywords):
                    links.append(href)

        return links

    def find_all_recipe_links_with_pagination(self, start_url: str, max_pages: int = 100) -> List[str]:
        """Find all recipe links across multiple pages following pagination."""
        all_links = []
        visited_pages = set()
        current_url = start_url
        page_num = 1

        while current_url and page_num <= max_pages:
            if current_url in visited_pages:
                break

            print(f"  Scanning page {page_num}: {current_url}")
            visited_pages.add(current_url)

            soup = self.fetch_page(current_url)
            if not soup:
                break

            # Get recipe links from current page
            page_links = self.find_recipe_links(current_url)
            new_links = [link for link in page_links if link not in all_links]
            all_links.extend(new_links)
            print(f"    Found {len(new_links)} new recipe links (total: {len(all_links)})")

            # Find next page
            next_url = self.find_next_page(soup, current_url)
            if not next_url or next_url == current_url:
                print(f"    No more pages found")
                break

            current_url = next_url
            page_num += 1

        return all_links

    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        return " ".join(text.strip().split())

    def save_recipe(self, recipe: Dict, output_dir: str = "data/recipes"):
        """Save recipe to JSON file."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Create filename from title and timestamp with microseconds
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_title = "".join(c for c in recipe.get('title', 'recipe')[:20]
                            if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{self.name} {safe_title}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)

        return filepath
