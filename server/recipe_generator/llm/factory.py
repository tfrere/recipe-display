from typing import Literal
from ..config import load_config
from .base import LLMProvider
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider

ProviderType = Literal["openai", "anthropic"]

def create_provider(
    provider_type: ProviderType,
    api_key: str,
    task: str,
    model: str | None = None
) -> LLMProvider:
    """
    Crée une instance du provider LLM spécifié.
    
    Args:
        provider_type: Type de provider ("openai" ou "anthropic")
        api_key: Clé API pour le provider
        task: Tâche à effectuer ("cleanup" ou "structure")
        model: Modèle à utiliser (optionnel, utilise le modèle de config.json si non spécifié)
        
    Returns:
        Instance du provider LLM
        
    Raises:
        ValueError: Si le type de provider n'est pas supporté
    """
    config = load_config()
    
    if provider_type == "openai":
        default_model = config["openai_models"][task]
        return OpenAIProvider(api_key, model or default_model)
    elif provider_type == "anthropic":
        default_model = config["anthropic_models"][task]
        return AnthropicProvider(api_key, model or default_model)
    else:
        raise ValueError(f"Provider type not supported: {provider_type}") 