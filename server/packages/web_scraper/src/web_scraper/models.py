from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class WebContent(BaseModel):
    """Content scraped from a recipe website."""
    title: str
    main_content: str
    image_urls: List[str]

class AuthPreset(BaseModel):
    """Authentication preset for a website."""
    type: str  # "cookie", "basic", "bearer", "apikey"
    domain: str
    values: Dict[str, str]  # Les valeurs dépendent du type d'auth
    description: Optional[str] = None  # Description optionnelle pour l'UI

# Format du fichier auth_presets.json :
# {
#     "books.ottolenghi.co.uk": {
#         "type": "cookie",
#         "domain": ".books.ottolenghi.co.uk",
#         "values": {
#             "cookie_name": "cookie_value"
#         },
#         "description": "Ottolenghi Books"
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