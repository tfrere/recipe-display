"""Authors routes module."""
from fastapi import APIRouter, Query
import json
import logging
import os
import glob

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/authors", tags=["authors"])

_AUTHORS_FILE = os.path.join(os.path.dirname(__file__), "../../data/authors.json")


def _load_private_authors() -> list[str]:
    """Load private author list. Returns empty list if file is missing."""
    try:
        with open(_AUTHORS_FILE, "r") as f:
            data = json.load(f)
            return [a.lower() for a in data.get("private", [])]
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("authors.json not found or invalid — no private filtering applied")
        return []


@router.get("")
async def get_authors(include_private: bool = Query(default=False)):
    """Get the list of recipe authors."""
    private_authors = _load_private_authors()

    # Get list of all recipe files
    recipes_path = os.path.join(os.path.dirname(__file__), "../../data/recipes")
    recipe_files = glob.glob(os.path.join(recipes_path, "*.recipe.json"))
    
    # Collect all unique authors
    all_authors = set()
    for recipe_file in recipe_files:
        with open(recipe_file, "r") as f:
            recipe_data = json.load(f)
            author = recipe_data.get("metadata", {}).get("author", "")
            if author:
                # Check if this author contains any private author name
                author_lower = author.lower()
                is_private = any(private_author in author_lower for private_author in private_authors)
                
                # Only add if it's not private or if private access is granted
                if include_private or not is_private:
                    all_authors.add(author)
    
    return sorted(list(all_authors)) 