from dataclasses import dataclass
from typing import Optional

@dataclass
class TextContent:
    """Simple wrapper for text content."""
    main_content: str
    selected_image_url: Optional[str] = None 