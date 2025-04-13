"""
recipe_scraper package for scraping and structuring recipes from URLs or text files.
"""

from .scraper import RecipeScraper
from .cli import main

__all__ = ["RecipeScraper", "main"] 