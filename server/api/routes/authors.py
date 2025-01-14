"""Authors routes module."""
from fastapi import APIRouter, Query
import json
import os

router = APIRouter()

@router.get("")
async def get_authors(include_private: bool = Query(default=False)):
    """Get the list of recipe authors."""
    # Read authors from JSON file
    authors_file = os.path.join(os.path.dirname(__file__), "../../data/authors.json")
    with open(authors_file, "r") as f:
        authors_data = json.load(f)
    
    # Return all authors if include_private is True, otherwise only public ones
    if include_private:
        return authors_data["public"] + authors_data["private"]
    return authors_data["public"] 