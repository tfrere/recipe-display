import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Primary: volume-mounted data dir (user can override constants)
_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "constants"
# Fallback: bundled at build time (survives volume overlay in Docker)
_BUNDLED_DIR = Path("/app/constants_bundled")


def _resolve(filename: str) -> Path:
    """Return the first existing path for a constants file."""
    data_path = _DATA_DIR / filename
    if data_path.exists():
        return data_path
    bundled_path = _BUNDLED_DIR / filename
    if bundled_path.exists():
        return bundled_path
    return data_path


@router.get("/api/constants")
async def get_constants():
    constants_path = _resolve("constants.json")
    try:
        with open(constants_path, "r") as f:
            constants = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Constants file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON in constants file")

    glossary_path = _resolve("glossary.json")
    try:
        with open(glossary_path, "r") as f:
            constants["glossary"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        constants["glossary"] = {"terms": [], "categories": [], "sources": []}

    return constants
