"""Recipe scraper package for extracting recipe content from websites."""

from .scraper import WebScraper
from .models import AuthPreset, WebContent

__all__ = ["WebScraper", "AuthPreset", "WebContent"] 