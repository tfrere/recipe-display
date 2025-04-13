import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

CONSTANTS_PATH = Path(__file__).parent.parent.parent / "data" / "constants" / "constants.json"

@router.get("/api/constants")
async def get_constants():
    try:
        with open(CONSTANTS_PATH, "r") as f:
            constants = json.load(f)
        return constants
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Constants file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON in constants file")
