from typing import TypeVar, Type, Any, AsyncGenerator, Callable, Awaitable, Optional
from pydantic import BaseModel, ValidationError
import instructor
from instructor import Mode
from anthropic import AsyncAnthropic
import logging
import json
from recipe_generator.models.recipe import LLMRecipe  # Import du modèle LLMRecipe
from dataclasses import dataclass

# Configure le logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

@dataclass
class TokenUsage:
    """Stocke les informations d'usage des tokens."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, other: 'TokenUsage'):
        """Ajoute les tokens d'un autre usage."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }

class InstructorAdapter:
    """Adaptateur pour utiliser Instructor avec différents providers."""
    
    def __init__(self, client: Any, mode: str = "openai", max_retries: int = 3):
        """
        Initialise l'adaptateur.
        
        Args:
            client: Client API (OpenAI ou Anthropic)
            mode: Mode d'utilisation ("openai" ou "anthropic")
            max_retries: Nombre maximum de tentatives pour la validation
        """
        self._mode = mode
        self._max_retries = max_retries
        self._client = client  # On garde le client original sans patch
    
    def _build_prompt(self, prompt: dict[str, Any]) -> str:
        """
        Construit le prompt complet à partir des parties fixe et dynamique.
        
        Args:
            prompt: Dictionnaire contenant 'content' (partie dynamique) et optionnellement 'image_urls'
        """
        # Récupère la partie fixe selon le type de prompt
        fixed_content = prompt.get("fixed_content", "")  # La partie fixe du prompt
        dynamic_content = prompt.get("content", "")  # La partie dynamique
        
        # Combine les parties dans le bon ordre : fixe puis dynamique
        parts = [
            fixed_content,  # D'abord la partie fixe avec les instructions
            "INPUT CONTENT:",  # Puis le marqueur pour le contenu
            dynamic_content  # Et enfin le contenu dynamique
        ]
        
        # Ajoute les URLs d'images si présentes (pour le cleanup)
        if "image_urls" in prompt:
            parts.extend([
                "AVAILABLE IMAGE URLS:",
                "\n".join(prompt["image_urls"])
            ])
        
        # Combine les parties
        return "\n".join(parts)
    
    def validate_recipe_structure(self, recipe: LLMRecipe) -> list[str]:
        """
        Valide la structure d'une recette et retourne la liste des erreurs trouvées.
        
        Args:
            recipe: La recette à valider
            
        Returns:
            Liste des erreurs trouvées. Liste vide si la recette est valide.
        """
        errors = []
        
        # Vérifie les champs essentiels
        if not recipe.metadata.name:
            errors.append("Recipe must have a name")
        if not recipe.metadata.description:
            errors.append("Recipe must have a description")
        if recipe.metadata.servings <= 0:
            errors.append("Recipe must have positive servings")
        if not recipe.ingredients:
            errors.append("Recipe must have ingredients")
            
        # Vérifie que tous les ingrédients sont utilisés
        used_ingredient_ids = set()
        for step in recipe.steps:
            for input in step.inputs:
                if input.input_type == "ingredient":
                    used_ingredient_ids.add(input.ref_id)
        
        all_ingredient_ids = {ing.id for ing in recipe.ingredients}
        unused_ingredients = all_ingredient_ids - used_ingredient_ids
        if unused_ingredients:
            errors.append(f"Found unused ingredients: {unused_ingredients}")
        
        # Vérifie que tous les IDs référencés existent
        for i, step in enumerate(recipe.steps):
            for input in step.inputs:
                if input.input_type == "ingredient":
                    if input.ref_id not in all_ingredient_ids:
                        errors.append(f"Step {i+1}: Referenced ingredient {input.ref_id} does not exist")
                elif input.input_type == "state":
                    # Vérifie que l'état référencé est la sortie d'une étape précédente
                    state_exists = any(
                        s.output_state.id == input.ref_id 
                        for s in recipe.steps[:i]  # Utilise l'index pour être plus précis
                    )
                    if not state_exists:
                        errors.append(f"Step {i+1}: Referenced state {input.ref_id} does not exist in previous steps")
        
        # Vérifie que le final_state est bien l'output du dernier step
        if not recipe.steps:
            errors.append("Recipe must have steps")
        else:
            last_step = recipe.steps[-1]
            if last_step.output_state.id != recipe.final_state.id:
                errors.append("Final state must be the output of the last step")
            if recipe.final_state.type != "final":
                errors.append("Final state must have type 'final'")
        
        return errors
    
    def _build_enhanced_content(
        self,
        schema_str: str,
        content: str,
        attempt: int,
        previous_response: str = ""
    ) -> str:
        """
        Construit le contenu enrichi du prompt selon la tentative.
        
        Args:
            schema_str: Le schéma JSON en string
            content: Le contenu original ou l'erreur
            attempt: Numéro de la tentative
            previous_response: Réponse précédente en cas de retry
        """
        if attempt == 1:
            return f"""Here is the JSON schema with descriptions for the expected response:
{schema_str}

{self._build_prompt({'content': content})}"""
        else:
            return f"""Your previous response had validation errors. Here is your previous response:

{previous_response}

The validation failed with these errors:
{content}

IMPORTANT: You MUST respond with ONLY a valid JSON object. DO NOT include any explanations, questions, or other text.
DO NOT ask for confirmation or clarification. Just provide the corrected JSON directly.

Please fix ALL these validation errors while keeping the same structure and content where possible.
Make sure to follow these CRITICAL REQUIREMENTS:
1. Every ingredient in the ingredients list MUST be used in at least one step
2. Every state referenced in a step MUST be the output of a previous step
3. The final_state MUST:
   - Have type="final"
   - Be the output_state of the last step
   - Have a complete description

Here is the JSON schema again for reference:
{schema_str}

REMEMBER: Respond with ONLY the corrected JSON. No other text."""

    async def _validate_and_parse_response(
        self,
        model: Type[T],
        accumulated_text: str,
        logger: logging.Logger
    ) -> T:
        """
        Valide et parse la réponse du modèle.
        
        Args:
            model: Type du modèle Pydantic
            accumulated_text: Texte accumulé de la réponse
            logger: Logger pour les messages de debug
        """
        # Essaie de trouver et parser le JSON
        start_idx = accumulated_text.find("{")
        end_idx = accumulated_text.rfind("}") + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No valid JSON found in response")
            
        json_str = accumulated_text[start_idx:end_idx]
        logger.info(f"Found JSON (length: {len(json_str)} chars)")
        logger.info(f"Last 100 chars of JSON: {json_str[-100:]}")
        
        try:
            # Vérifie d'abord si le JSON est valide
            parsed = json.loads(json_str)
            logger.info("✅ JSON is valid")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON: {str(e)}")
            raise
        
        # Parse avec Pydantic
        result = model.model_validate_json(json_str)
        logger.info("✅ Pydantic validation successful!")

        # Validation structurelle supplémentaire
        if isinstance(result, LLMRecipe):
            validation_errors = self.validate_recipe_structure(result)
            if validation_errors:
                error_msg = "\n".join(validation_errors)
                logger.error(f"❌ Structure validation failed:\n{error_msg}")
                raise ValueError(f"Recipe structure validation failed: {error_msg}")
            logger.info("✅ Structure validation successful!")

        return result

    async def _retry_anthropic(
        self,
        model: Type[T],
        content: str,
        temperature: float,
        model_name: str,
        progress_callback: Callable[[str], Awaitable[None]],
        attempt: int = 1,
        previous_response: str = "",
        token_usage: Optional[TokenUsage] = None
    ) -> T:
        """Tente de générer une réponse valide avec Anthropic, avec retry en cas d'erreur."""
        # Initialise ou réutilise le token usage
        token_usage = token_usage or TokenUsage()
        
        # Génère le schéma JSON avec les descriptions via Pydantic
        schema = model.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        
        # Construit le contenu enrichi
        enhanced_content = self._build_enhanced_content(schema_str, content, attempt, previous_response)
        
        # Estime les prompt tokens (approximatif)
        token_usage.prompt_tokens = len(enhanced_content) // 4  # Estimation grossière: 1 token ≈ 4 caractères

        logger.info(f"\n=== Attempt {attempt}/{self._max_retries} ===")
        logger.info(f"Sending prompt to {model_name} (length: {len(enhanced_content)} chars)")
        
        # Stream la réponse avec Anthropic
        accumulated_text = ""
        async with self._client.messages.stream(
            model=model_name,
            max_tokens=8192,
            messages=[{"role": "user", "content": enhanced_content}],
            temperature=temperature
        ) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                    text = chunk.delta.text
                    accumulated_text += text
                    await progress_callback(text)
                elif chunk.type == "message_delta" and hasattr(chunk.delta, "usage"):
                    # Capture l'usage des tokens
                    usage = chunk.delta.usage
                    if hasattr(usage, "output_tokens"):
                        token_usage.completion_tokens = usage.output_tokens
                        token_usage.total_tokens = token_usage.prompt_tokens + token_usage.completion_tokens
                        # Met à jour le progress avec l'usage actuel
                        await progress_callback(f"\n__TOKEN_USAGE__{json.dumps(token_usage.to_dict())}\n")
        
        logger.info(f"Received response (length: {len(accumulated_text)} chars)")
        
        try:
            result = await self._validate_and_parse_response(model, accumulated_text, logger)
            # Envoie l'usage final une fois la validation réussie
            await progress_callback(f"\n__TOKEN_USAGE__{json.dumps(token_usage.to_dict())}\n")
            return result
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"❌ Validation failed: {str(e)}")
            
            if attempt < self._max_retries:
                return await self._retry_anthropic(
                    model=model,
                    content=str(e),
                    temperature=temperature,
                    model_name=model_name,
                    progress_callback=progress_callback,
                    attempt=attempt + 1,
                    previous_response=accumulated_text,
                    token_usage=token_usage  # Passe l'usage accumulé
                )
            else:
                raise

    async def _retry_openai(
        self,
        model: Type[T],
        content: str,
        temperature: float,
        model_name: str,
        progress_callback: Callable[[str], Awaitable[None]],
        attempt: int = 1,
        previous_response: str = "",
        token_usage: Optional[TokenUsage] = None
    ) -> T:
        """Tente de générer une réponse valide avec OpenAI, avec retry en cas d'erreur."""
        # Initialise ou réutilise le token usage
        token_usage = token_usage or TokenUsage()
        
        # Génère le schéma JSON avec les descriptions via Pydantic
        schema = model.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        
        # Construit le contenu enrichi
        enhanced_content = self._build_enhanced_content(schema_str, content, attempt, previous_response)

        logger.info(f"\n=== Attempt {attempt}/{self._max_retries} ===")
        logger.info(f"Sending prompt to {model_name} (length: {len(enhanced_content)} chars)")
        
        # Stream la réponse avec OpenAI
        accumulated_text = ""
        response = await self._client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": enhanced_content}],
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True}  # Active la capture d'usage
        )
        
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                accumulated_text += text
                await progress_callback(text)
            
            if chunk.usage:  # Capture l'usage final des tokens
                token_usage.prompt_tokens = chunk.usage.prompt_tokens
                token_usage.completion_tokens = chunk.usage.completion_tokens
                token_usage.total_tokens = chunk.usage.total_tokens
                # Met à jour le progress avec l'usage final dans un message séparé
                await progress_callback(f"\n__TOKEN_USAGE__{json.dumps(token_usage.to_dict())}\n")
        
        logger.info(f"Received response (length: {len(accumulated_text)} chars)")
        
        try:
            result = await self._validate_and_parse_response(model, accumulated_text, logger)
            # Envoie l'usage final une fois la validation réussie
            await progress_callback(f"\n__TOKEN_USAGE__{json.dumps(token_usage.to_dict())}\n")
            return result
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"❌ Validation failed: {str(e)}")
            
            if attempt < self._max_retries:
                return await self._retry_openai(
                    model=model,
                    content=str(e),
                    temperature=temperature,
                    model_name=model_name,
                    progress_callback=progress_callback,
                    attempt=attempt + 1,
                    previous_response=accumulated_text,
                    token_usage=token_usage  # Passe l'usage accumulé
                )
            else:
                raise

    async def generate_structured(
        self,
        model: Type[T],
        prompt: dict[str, Any],
        temperature: float,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        stream: bool = True
    ) -> T:
        """
        Génère une sortie structurée en utilisant Instructor.
        
        Args:
            model: Classe Pydantic pour la validation
            prompt: Dictionnaire contenant les données pour le prompt
            temperature: Température pour la génération
            progress_callback: Callback optionnel pour streamer le texte généré
            stream: Si True, utilise le streaming
            
        Returns:
            Instance du modèle Pydantic
        """
        # Fonction callback par défaut si non fournie
        async def noop_callback(text: str) -> None:
            pass
        progress_callback = progress_callback or noop_callback
        
        # Initialise le token usage
        token_usage = TokenUsage()
        
        try:
            if self._mode == "openai":
                return await self._retry_openai(
                    model=model,
                    content=prompt.get("content", ""),
                    temperature=temperature,
                    model_name=prompt.get("model"),
                    progress_callback=progress_callback,
                    token_usage=token_usage
                )
            else:
                return await self._retry_anthropic(
                    model=model,
                    content=prompt.get("content", ""),
                    temperature=temperature,
                    model_name=prompt.get("model"),
                    progress_callback=progress_callback,
                    token_usage=token_usage
                )
        except Exception as e:
            logger.error(f"❌ Generation failed: {str(e)}")
            raise ValueError(str(e)) 