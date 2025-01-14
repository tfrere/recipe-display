"""
Recipe Generator
==============

A Python package to generate structured recipes from web content using OpenAI's GPT models.
"""

from .generator.recipe_generator import RecipeGenerator
from .models.recipe import Recipe
from .models.web_content import WebContent
from .storage.recipe_storage import RecipeStorage

__version__ = "0.1.0"

__all__ = [
    "RecipeGenerator",
    "Recipe",
    "WebContent",
    "RecipeStorage",
] 