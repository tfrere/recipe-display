from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class WebContent(BaseModel):
    """Content scraped from a recipe website."""
    title: str
    main_content: str
    image_urls: List[str]
    structured_data: Optional[Dict[str, Any]] = None

class AuthPreset(BaseModel):
    """Authentication preset for a website."""
    type: str  # "cookie", "basic", "bearer", "apikey"
    domain: str
    values: Dict[str, str]  # Les valeurs dépendent du type d'auth
    description: Optional[str] = None  # Description optionnelle pour l'UI

# Format du fichier auth_presets.json :
# {
#     "recipes.example.com": {
#         "type": "cookie",
#         "domain": ".recipes.example.com",
#         "values": {
#             "cookie_name": "cookie_value"
#         },
#         "description": "Example Recipe Site"
#     },
#     "example.com": {
#         "type": "basic",
#         "domain": "example.com",
#         "values": {
#             "username": "user",
#             "password": "pass"
#         },
#         "description": "Example Site"
#     }
# } 