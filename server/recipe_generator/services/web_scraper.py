from typing import Dict, Any, Optional
import mechanicalsoup
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from http.cookiejar import Cookie
from pathlib import Path
import json
from ..models.web_content import WebContent

class WebScraper:
    """Service for scraping recipe content from websites."""
    
    def __init__(self):
        self.browser = mechanicalsoup.StatefulBrowser(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.auth_presets = self._load_auth_presets()

    def _load_auth_presets(self) -> Dict[str, Any]:
        """Load authentication presets from file."""
        auth_presets_path = Path(__file__).parent.parent.parent / "data" / "auth_presets.json"
        try:
            with open(auth_presets_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Note: Could not load auth presets: {e}")
            return {}

    def _create_cookie(self, domain: str, name: str, value: str) -> Cookie:
        """Create a cookie object."""
        return Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=True,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False
        )

    def _setup_authentication(self, url: str, credentials: Optional[Dict[str, Any]] = None) -> None:
        """Set up authentication for the browser."""
        domain = urlparse(url).netloc
        
        # Try to get credentials from presets if not provided
        if not credentials and domain in self.auth_presets:
            credentials = self.auth_presets[domain]
            print(f"Using auth preset for {domain}")
        
        if not credentials:
            return
        
        auth_type = credentials.get("type")
        auth_values = credentials.get("values", {})
        domain = credentials.get("domain") or domain
        
        if auth_type == "cookie":
            for name, value in auth_values.items():
                cookie = self._create_cookie(domain, name, value)
                self.browser.get_cookiejar().set_cookie(cookie)
                print(f"Set cookie {name} for domain {domain}")
        elif auth_type == "basic":
            self.browser.session.auth = (
                auth_values.get("username"),
                auth_values.get("password")
            )
            print("Set basic auth")
        elif auth_type == "bearer":
            self.browser.session.headers["Authorization"] = f"Bearer {auth_values.get('token')}"
            print("Set bearer token")
        elif auth_type == "apikey":
            self.browser.session.headers["X-API-Key"] = auth_values.get("key")
            print("Set API key")

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract image URLs from the page."""
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                if not src.startswith(("http://", "https://")):
                    # Convert relative URL to absolute
                    parsed_base = urlparse(base_url)
                    if src.startswith("//"):
                        src = f"{parsed_base.scheme}:{src}"
                    elif src.startswith("/"):
                        src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
                    else:
                        src = f"{parsed_base.scheme}://{parsed_base.netloc}/{src}"
                
                # Try to fetch image without credentials first
                temp_browser = mechanicalsoup.StatefulBrowser(
                    user_agent=self.browser.session.headers["User-Agent"]
                )
                response = temp_browser.get(src)
                
                # If access denied, try with credentials
                if response.status_code == 403:
                    response = self.browser.get(src)
                
                # Only add image if we can access it
                if response.ok:
                    images.append(src)
                else:
                    print(f"Warning: Could not access image {src}: {response.status_code}")
                    
        return images

    async def scrape_url(
        self,
        url: str,
        credentials: Optional[Dict[str, Any]] = None
    ) -> WebContent:
        """Scrape recipe content from a URL."""
        # Set up authentication if needed
        self._setup_authentication(url, credentials)
        
        # Fetch the page
        response = self.browser.get(url)
        if not response.ok:
            raise ValueError(f"Failed to fetch URL: {response.status_code}")
        
        # Parse the page
        soup = response.soup
        
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
        
        # Extract images
        image_urls = self._extract_images(soup, url)
        
        return WebContent(
            title=title,
            main_content=main_content,
            image_urls=image_urls
        ) 