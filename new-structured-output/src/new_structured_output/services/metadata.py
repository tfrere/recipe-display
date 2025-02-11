"""Service for generating recipe metadata"""
from pydantic_ai.settings import ModelSettings
from ..providers.deepseek_model import StreamingDeepseekModel
from ..models.recipe import LLMRecipeBase
from ..prompts.metadata import metadata_prompt

async def generate_metadata(model: StreamingDeepseekModel, cleaned_text: str) -> LLMRecipeBase:
    """Generate recipe base (metadata, ingredients, tools)"""
    print("\n📝 Generating recipe metadata...")
    
    # Log des tailles pour déboguer
    print(f"Taille du prompt système : {len(metadata_prompt)} caractères")
    print(f"Taille du texte nettoyé : {len(cleaned_text)} caractères")
    
    base_messages = [
        {
            "role": "system",
            "content": metadata_prompt
        },
        {
            "role": "user",
            "content": cleaned_text
        }
    ]
    
    # Utiliser ModelSettings au lieu d'un dictionnaire
    settings = ModelSettings(
        stream=True,
        temperature=0.2,  # Réduire la température pour plus de précision
        max_tokens=4000  # S'assurer d'avoir assez de tokens pour la réponse
    )
    
    # Le modèle va déjà parser et valider la réponse
    response = await model.complete(
        messages=base_messages,
        settings=settings,
        validation_model=LLMRecipeBase
    )
    
    # La réponse contient déjà l'objet validé
    return response 