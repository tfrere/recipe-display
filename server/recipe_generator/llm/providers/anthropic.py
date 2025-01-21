from typing import AsyncGenerator, Optional, Callable, Awaitable, Type, Any
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam
import json

from ..base import LLMProvider, T
from ..structured.instructor_adapter import InstructorAdapter

class AnthropicProvider(LLMProvider):
    """Provider pour l'API Anthropic."""
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialise le provider.
        
        Args:
            api_key: Clé API Anthropic
            model: Nom du modèle à utiliser
        """
        super().__init__(api_key, model)
        
        # Initialise le client avec la clé API
        self._client = AsyncAnthropic(api_key=api_key)
        self._instructor = InstructorAdapter(self._client, mode="anthropic")
    
    async def generate_stream(self, prompt: str, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        Génère du texte en streaming.
        
        Args:
            prompt: Texte d'entrée
            temperature: Température pour la génération
            
        Yields:
            Morceaux de texte générés
        """
        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        
        async with self._client.messages.stream(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=8100
        ) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                    yield chunk.delta.text
                elif chunk.type == "message_delta" and hasattr(chunk, "usage"):
                    # Capture tous les attributs de l'objet usage qui sont des types simples
                    usage = chunk.usage
                    token_usage = {}
                    
                    for attr in dir(usage):
                        if not attr.startswith('_'):  # Ignore les attributs privés
                            value = getattr(usage, attr)
                            # Ne garde que les types simples (int, float, str, bool)
                            if isinstance(value, (int, float, str, bool)):
                                token_usage[attr] = value
                            
                    print(f"[DEBUG] Full usage data: {token_usage}")
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