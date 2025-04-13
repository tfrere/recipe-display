"""Authors routes module."""
from fastapi import APIRouter, Query
import json
import os
import glob

router = APIRouter(prefix="/api/authors", tags=["authors"])

@router.get("")
async def get_authors(include_private: bool = Query(default=False)):
    """Get the list of recipe authors."""
    # Read private authors from JSON file
    authors_file = os.path.join(os.path.dirname(__file__), "../../data/authors.json")
    with open(authors_file, "r") as f:
        authors_data = json.load(f)
        private_authors = [author.lower() for author in authors_data.get("private", [])]

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