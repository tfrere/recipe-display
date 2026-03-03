import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "constants"
CONSTANTS_PATH = DATA_DIR / "constants.json"
GLOSSARY_PATH = DATA_DIR / "glossary.json"

@router.get("/api/constants")
async def get_constants():
    try:
        with open(CONSTANTS_PATH, "r") as f:
            constants = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Constants file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON in constants file")

    try:
        with open(GLOSSARY_PATH, "r") as f:
            constants["glossary"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        constants["glossary"] = {"terms": [], "categories": [], "sources": []}

    return constants
