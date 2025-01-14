import json
import os
from pathlib import Path
from datetime import datetime

def load_constants() -> dict:
    """Load constants from the shared constants file."""
    constants_path = Path(__file__).parent.parent.parent / "shared" / "constants.json"
    try:
        with open(constants_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError as e:
        # Try with relative path to working directory
        current_dir = os.getcwd()
        alternative_path = os.path.join(current_dir, "shared", "constants.json")
        try:
            with open(alternative_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Error reading constants (tried paths: {constants_path}, {alternative_path}): {e}"
            )