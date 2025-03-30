"""Service for generating recipe metadata"""
import json
from pydantic import ValidationError
from ..providers.deepseek_model import StreamingDeepseekModel
from ..providers.mistral_model import StreamingMistralModel
from ..models.recipe import LLMRecipeBase
from ..prompts.metadata import metadata_prompt
from ..exceptions import RecipeRejectedError
import re

async def generate_metadata(model: StreamingDeepseekModel | StreamingMistralModel, cleaned_text: str) -> LLMRecipeBase:
    """Generate recipe base (metadata, ingredients, tools)"""
    print("\n📝 Generating recipe metadata...")
    
    # Vérification de l'URL vide dans le texte d'entrée
    url_pattern = r"SELECTED IMAGE URL:(.*?)(?=\n\n|\n[A-Z])"
    url_match = re.search(url_pattern, cleaned_text, re.DOTALL)
    
    if url_match:
        url_content = url_match.group(1).strip()
        if not url_content:
            print("[ERROR] Empty image URL detected in input text")
            raise RecipeRejectedError("Empty image URL in input. Please provide a valid image URL for the recipe.")
    else:
        print("[ERROR] Could not find SELECTED IMAGE URL section")
        raise RecipeRejectedError("Missing image URL section in input. Please provide a valid image URL for the recipe.")
    
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
    
    try:
        # Réponse du modèle
        response = await model.complete(
            messages=base_messages,
            settings={"stream": True},
            validation_model=LLMRecipeBase
        )
        
        # Vérification des URL vides dans la réponse JSON
        raw_json = response.model_dump_json()
        parsed = json.loads(raw_json)
        
        if "metadata" in parsed and "sourceImageUrl" in parsed["metadata"]:
            url = parsed["metadata"]["sourceImageUrl"]
            if not url or url == "":
                print("[ERROR] Empty image URL detected in model response")
                raise RecipeRejectedError("Empty image URL returned by model. Please provide a valid image URL.")
        
        return response
    except ValidationError as e:
        # Capturer les erreurs de validation liées aux images
        for error in e.errors():
            if 'sourceImageUrl' in str(error.get('loc', [])):
                print(f"[ERROR] Image validation error: {error.get('msg')}")
                raise RecipeRejectedError(f"Missing or invalid image URL. Please provide a valid image for the recipe.") from e
        
        # Si l'erreur n'est pas liée à l'image, on la relance telle quelle
        raise 