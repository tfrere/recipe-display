from abc import ABC, abstractmethod
from typing import AsyncGenerator, TypeVar, Type, Any, Optional, Callable, Awaitable
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class LLMProvider(ABC):
    """Interface abstraite pour les providers de LLM."""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """
        Génère du texte en streaming.
        Utilisé pour les cas simples comme le nettoyage de recette.
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        model: Type[T],
        prompt: dict[str, Any],
        temperature: float,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        stream: bool = True
    ) -> T:
        """
        Génère une sortie structurée basée sur un modèle Pydantic.
        Utilisé pour la structuration de recette.
        
        Args:
            model: Type du modèle Pydantic à générer
            prompt: Dictionnaire contenant les données pour le prompt
            temperature: Température pour la génération
            progress_callback: Callback optionnel pour streamer le texte généré
            stream: Si True, utilise le streaming quand disponible
        """
        pass 