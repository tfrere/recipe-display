from pathlib import Path
import os
from typing import Literal
from dotenv import load_dotenv
from .llm.providers.openai import OpenAIProvider
from .llm.providers.anthropic import AnthropicProvider
import json

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

# LLM Configuration
DEFAULT_TEMPERATURE = 0.3
ProviderType = Literal["openai", "anthropic"]

def load_config() -> dict:
    """
    Charge la configuration depuis le fichier config.json et les variables d'environnement.
    
    Returns:
        Configuration complète
    """
    # Charge la configuration de base depuis le fichier
    config_file = Path(__file__).parent / "config.json"
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # Surcharge avec les variables d'environnement
    config["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")
    config["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY", "")
    
    return config