from typing import Dict, Any, Optional
from urllib.parse import urlparse
from pathlib import Path
import json
import httpx
from .models import AuthPreset

class AuthManager:
    """Manages authentication for recipe websites."""
    
    def __init__(self, client: httpx.AsyncClient, auth_presets_path: Optional[Path] = None):
        """
        Initialize with an httpx client instance.
        
        Args:
            client: The httpx client to use
            auth_presets_path: Optional path to the auth presets file
        """
        self.client = client
        self.auth_presets_path = auth_presets_path
        self.auth_presets = self._load_auth_presets() if auth_presets_path else {}

    def _load_auth_presets(self) -> Dict[str, AuthPreset]:
        """Load authentication presets from file."""
        try:
            with open(self.auth_presets_path, "r") as f:
                data = json.load(f)
                # Convertit chaque preset en modèle Pydantic
                return {
                    domain: AuthPreset(**preset)
                    for domain, preset in data.items()
                }
        except Exception as e:
            print(f"Note: Could not load auth presets: {e}")
            return {}

    async def setup_authentication(self, url: str, preset: Optional[AuthPreset] = None) -> None:
        """
        Set up authentication for the client.
        
        Args:
            url: The URL to access
            preset: Optional authentication preset. If not provided, will try to load from presets file.
        """
        domain = urlparse(url).netloc
        
        # Try to get preset from file if not provided
        if not preset and domain in self.auth_presets:
            preset = self.auth_presets[domain]
            print(f"Using auth preset for {domain}")
        
        if not preset:
            return
        
        # Configure authentication based on type
        if preset.type == "cookie":
            self.client.cookies.update(preset.values)
            print(f"Set {len(preset.values)} cookies for {preset.domain}")
            
        elif preset.type == "basic":
            self.client.auth = httpx.BasicAuth(
                username=preset.values["username"],
                password=preset.values["password"]
            )
            print("Set basic auth")
            
        elif preset.type == "bearer":
            self.client.headers["Authorization"] = f"Bearer {preset.values['token']}"
            print("Set bearer token")
            
        elif preset.type == "apikey":
            self.client.headers["X-API-Key"] = preset.values["key"]
            print("Set API key") 