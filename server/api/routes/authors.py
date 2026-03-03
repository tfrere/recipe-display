"""Authors routes module."""
from fastapi import APIRouter, Query
import json
import logging
import os
import glob

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/authors", tags=["authors"])

_AUTHORS_FILE = os.path.join(os.path.dirname(__file__), "../../data/authors.json")


def _load_authors_config() -> dict[str, list[str]]:
    """Load authors.json. Supports 'public' (whitelist) and 'private' (blacklist) keys."""
    try:
        with open(_AUTHORS_FILE, "r") as f:
            data = json.load(f)
            config: dict[str, list[str]] = {}
            if "public" in data:
                config["public"] = [a.lower() for a in data["public"]]
            if "private" in data:
                config["private"] = [a.lower() for a in data["private"]]
            return config
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("authors.json not found or invalid — no filtering applied")
        return {}


def _author_matches(author: str, keywords: list[str]) -> bool:
    if not author or not keywords:
        return False
    return any(kw in author.lower() for kw in keywords)


@router.get("")
async def get_authors(include_private: bool = Query(default=False)):
    """Get the list of recipe authors."""
    config = _load_authors_config()

    recipes_path = os.path.join(os.path.dirname(__file__), "../../data/recipes")
    recipe_files = glob.glob(os.path.join(recipes_path, "*.recipe.json"))

    all_authors = set()
    for recipe_file in recipe_files:
        try:
            with open(recipe_file, "r") as f:
                recipe_data = json.load(f)
                author = recipe_data.get("metadata", {}).get("author", "")
                if not author:
                    continue

                if include_private:
                    all_authors.add(author)
                elif "public" in config and config["public"]:
                    if _author_matches(author, config["public"]):
                        all_authors.add(author)
                elif "private" in config and config["private"]:
                    if not _author_matches(author, config["private"]):
                        all_authors.add(author)
                else:
                    all_authors.add(author)
        except (json.JSONDecodeError, OSError):
            continue

    return sorted(list(all_authors))
