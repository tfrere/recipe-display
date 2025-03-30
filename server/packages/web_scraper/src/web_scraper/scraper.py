from typing import Optional, List
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import asyncio
from pathlib import Path

from .models import WebContent, AuthPreset
from .auth import AuthManager

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

    async def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from the page."""
        images = []
        tasks = []

        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                if not src.startswith(("http://", "https://")):
                    src = urljoin(base_url, src)
                
                async def check_image(url):
                    try:
                        r = await self.client.head(url)
                        if r.status_code == 200:
                            images.append(url)
                    except httpx.HTTPError:
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
        
        # Parse the page
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract title
        title = soup.title.string if soup.title else ""
        title = title.strip()
        
        # Extract ALL text content from the page, preserving structure
        main_content = []
        for text in soup.stripped_strings:
            if text.strip():  # Only add non-empty strings
                main_content.append(text.strip())
        
        # Join all text with newlines to preserve some structure
        main_content = "\n".join(main_content)
        
        # Extract images en parallèle
        image_urls = await self._extract_images(soup, url)
        
        return WebContent(
            title=title,
            main_content=main_content,
            image_urls=image_urls
        )
    
    async def __aenter__(self):
        """Support for async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        await self.client.aclose() 