from typing import List, Optional

class WebContent:
    """Class representing web content with title, main content and images."""
    def __init__(self, title: str, main_content: str, image_urls: List[str] = None):
        self.title = title
        self.main_content = main_content
        self.image_urls = image_urls or []  # All available image URLs
        self.selected_image_url: Optional[str] = None  # Selected image URL 