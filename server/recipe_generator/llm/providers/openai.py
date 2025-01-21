from typing import AsyncGenerator, Optional, Callable, Awaitable, Type, Any
from openai import AsyncOpenAI
import json

from ..base import LLMProvider, T  # Import T depuis la classe de base
from ..structured.instructor_adapter import InstructorAdapter

class OpenAIProvider(LLMProvider):
    """Provider pour l'API OpenAI."""
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialise le provider.
        
        Args:
            api_key: Clé API OpenAI
            model: Nom du modèle à utiliser
        """
        super().__init__(api_key, model)
        
        # Initialise le client avec la clé API
        self._client = AsyncOpenAI(api_key=api_key)
        self._instructor = InstructorAdapter(self._client, mode="openai")
    
    async def generate_stream(self, prompt: str, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        Génère du texte en streaming.
        
        Args:
            prompt: Texte d'entrée
            temperature: Température pour la génération
            
        Yields:
            Morceaux de texte générés
        """
        messages = [{"role": "user", "content": prompt}]
        
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True}  # Active la capture d'usage
        )
        
        async for chunk in response:
            # Vérifie que le chunk a des choices et un delta avec du contenu
            if (hasattr(chunk, "choices") and 
                chunk.choices and 
                hasattr(chunk.choices[0], "delta") and 
                hasattr(chunk.choices[0].delta, "content") and 
                chunk.choices[0].delta.content):
                yield chunk.choices[0].delta.content
            
            # Vérifie si le chunk contient des informations d'usage
            if hasattr(chunk, "usage") and chunk.usage:
                token_usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens
                }
                yield f"__TOKEN_USAGE__{json.dumps(token_usage)}"
    
    async def generate_structured(
        self,
        model: Type[T],
        prompt: dict[str, Any],
        temperature: float = 0.7,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        stream: bool = True
    ) -> T:
        """
        Génère une sortie structurée.
        
        Args:
            model: Classe du modèle Pydantic
            prompt: Dictionnaire contenant les données pour le prompt
            temperature: Température pour la génération
            progress_callback: Callback optionnel pour streamer le texte généré
            stream: Si True, utilise le streaming
            
        Returns:
            Instance du modèle Pydantic
        """
        return await self._instructor.generate_structured(
            model=model,
            prompt=prompt,
            temperature=temperature,
            progress_callback=progress_callback,
            stream=stream
        ) 