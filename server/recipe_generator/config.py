from pathlib import Path
import os
from dotenv import load_dotenv

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
RECIPES_DIR = DATA_DIR / "recipes"
ERRORS_DIR = RECIPES_DIR / "errors"
SHARED_DIR = Path(__file__).parent.parent / "shared"
CONSTANTS_FILE = SHARED_DIR / "constants.json"
AUTH_PRESETS_FILE = DATA_DIR / "auth_presets.json"

# HTTP Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

# OpenAI Configuration
OPENAI_TEMPERATURE = 0.3

def load_config():
    """Load configuration from environment variables."""
    # Find and load .env file
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    # Check for required environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in .env file")
    
    # Load model names from environment
    cleanup_model = os.getenv("CLEANUP_MODEL", "gpt-4-1106-preview")
    structure_model = os.getenv("STRUCTURE_MODEL", "gpt-4-1106-preview")
    
    return {
        "openai_api_key": api_key,
        "cleanup_model": cleanup_model,
        "structure_model": structure_model,
        "temperature": OPENAI_TEMPERATURE,
        "headers": DEFAULT_HEADERS
    }