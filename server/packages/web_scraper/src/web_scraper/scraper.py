from typing import Any, Dict, Optional, List
import json
import logging
import httpx
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urlparse, urljoin
import asyncio
from pathlib import Path

from .models import WebContent, AuthPreset
from .auth import AuthManager

logger = logging.getLogger(__name__)

class WebScraper:
    """Service for scraping recipe content from websites."""
    
    def __init__(self, auth_presets_path: Optional[Path] = None):
        """
        Initialize the web scraper.
        
        Args:
            auth_presets_path: Optional path to the auth presets file
        """
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        self.client = httpx.AsyncClient(
            headers=self.headers,
            follow_redirects=True,
            timeout=30.0
        )
        self.auth_manager = AuthManager(self.client, auth_presets_path)

    @staticmethod
    def _extract_schema_recipe(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract schema.org/Recipe structured data from JSON-LD script tags.

        Most recipe websites include a <script type="application/ld+json"> block
        containing structured recipe data (ingredients, steps, times, servings).
        This data is more reliable than text extraction because it was authored
        by the site developer, not inferred from prose.

        Returns:
            Parsed JSON-LD dict with @type=Recipe, or None if not found.
        """
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                text = script.string
                if not text:
                    continue
                data = json.loads(text)

                # Direct Recipe object
                if isinstance(data, dict) and data.get("@type") == "Recipe":
                    return data

                # Array of objects (some sites emit a list)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            return item

                # @graph array (common with Yoast SEO, WordPress recipe plugins)
                if isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            return item

                # Handle list @type like ["Recipe", "Article"]
                if isinstance(data, dict) and isinstance(data.get("@type"), list):
                    if "Recipe" in data["@type"]:
                        return data

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return None

    async def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from the page."""
        images = []
        tasks = []

        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                # Skip SVG data URIs or invalid URL formats that cause problems
                if src.startswith(("/image/svg+xml", "data:image/svg+xml")):
                    continue
                    
                if not src.startswith(("http://", "https://")):
                    src = urljoin(base_url, src)
                
                async def check_image(url):
                    try:
                        r = await self.client.head(url)
                        if r.status_code == 200:
                            images.append(url)
                    except (httpx.HTTPError, ValueError):
                        # Catch both HTTPError and ValueError (for invalid URLs)
                        pass

                tasks.append(check_image(src))

        # Exécute toutes les vérifications d'images en parallèle
        await asyncio.gather(*tasks)
        return images

    async def scrape_url(
        self,
        url: str,
        auth_preset: Optional[AuthPreset] = None
    ) -> WebContent:
        """
        Scrape recipe content from a URL.
        
        Args:
            url: The URL to scrape
            auth_preset: Optional authentication preset
            
        Returns:
            WebContent object containing the scraped content
            
        Raises:
            ValueError: If the URL cannot be fetched
        """
        # Set up authentication if needed
        await self.auth_manager.setup_authentication(url, auth_preset)
        
        # Fetch the page
        try:
            response = await self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch URL: {str(e)}")
        
        html = response.text

        # Parse with BeautifulSoup (needed for image extraction, JSON-LD, and title fallback)
        soup = BeautifulSoup(html, "html.parser")

        # Extract structured data (schema.org/Recipe JSON-LD) — most reliable source
        structured_data = self._extract_schema_recipe(soup)
        if structured_data:
            logger.info(
                "Found schema.org/Recipe JSON-LD for %s (keys: %s)",
                url, ", ".join(k for k in structured_data if not k.startswith("@"))
            )

        # Extract title (prefer structured data, fallback to <title> tag)
        title = ""
        if structured_data and structured_data.get("name"):
            title = str(structured_data["name"]).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Extract main content with Trafilatura (removes boilerplate: nav, footer, ads, comments)
        main_content = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_links=False,
            favor_recall=True,
        )

        # Fallback to BeautifulSoup if Trafilatura returns nothing
        if not main_content:
            logger.warning("Trafilatura returned empty content for %s, falling back to BeautifulSoup", url)
            texts = [t.strip() for t in soup.stripped_strings if t.strip()]
            main_content = "\n".join(texts)

        # Extract images in parallel (still uses BeautifulSoup)
        image_urls = await self._extract_images(soup, url)
        
        return WebContent(
            title=title,
            main_content=main_content,
            image_urls=image_urls,
            structured_data=structured_data,
        )
    
    async def __aenter__(self):
        """Support for async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        await self.client.aclose() 