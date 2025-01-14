from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class GenerateRecipeRequest(BaseModel):
    type: Literal["url", "text"]
    url: Optional[str] = None
    text: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded
    credentials: Optional[Dict[str, Any]] = None