import asyncio
import json
import os
from dotenv import load_dotenv
from ..services.recipe_structurer import RecipeStructurer
from ..models.recipe import LLMRecipe
from ..models.text_content import TextContent
from ..llm.factory import create_provider
from ..config import load_config
from typing import Optional, Tuple, Literal
from pathlib import Path
from datetime import datetime
from .utils import MockProgressService, load_recipe_files
from ..llm.structured.instructor_adapter import TokenUsage

# Charge les variables d'environnement
load_dotenv()

ProviderType = Literal["openai", "anthropic"]

class StreamDiffService:
    """Service pour afficher uniquement les différences dans un stream de texte."""
    
    def __init__(self):
        self._last_text = ""
        print("\n\033[35m[DEBUG] StreamDiffService initialized\033[0m")
    
    def update(self, new_text: str) -> str:
        """
        Compare avec le dernier texte reçu et retourne uniquement la nouvelle partie.
        
        Args:
            new_text: Nouveau texte complet reçu
            
        Returns:
            La partie du texte qui n'a pas encore été affichée
        """
        # Si le nouveau texte est plus court, on recommence (cas d'un retry)
        if len(new_text) < len(self._last_text):
            self._last_text = ""
            return new_text
        
        # On ne garde que la nouvelle partie
        diff = new_text[len(self._last_text):]
        
        # Met à jour le dernier texte
        self._last_text = new_text
        
        return diff

class MockProgressService:
    def __init__(self):
        self._streaming = False
        self._first_chunk = True
        self._last_newline = False
        self._diff_service = StreamDiffService()
        self._token_usages = []  # Liste des usages au lieu d'un dict
        print("\n\033[35m[DEBUG] MockProgressService initialized with StreamDiffService\033[0m")
    
    async def update_step(
        self,
        progress_id: str,
        step: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        if details:
            # Vérifie si c'est une mise à jour d'usage de tokens
            if details.startswith("__TOKEN_USAGE__"):
                usage_data = json.loads(details[len("__TOKEN_USAGE__"):])
                self._token_usages.append(usage_data)  # Ajoute à la liste
                # Affiche les stats d'usage en cyan
                print(f"\n\033[36m[TOKEN USAGE] Attempt {len(self._token_usages)}")
                print(f"  Prompt tokens: {usage_data['prompt_tokens']}")
                print(f"  Completion tokens: {usage_data['completion_tokens']}")
                print(f"  Total tokens: {usage_data['total_tokens']}\033[0m")
                return
            
            # Début du streaming
            if self._first_chunk:
                print("\n\033[36m=== Start of stream ===\033[0m\n", flush=True)
                self._first_chunk = False
                self._streaming = True
            
            # Obtient uniquement la différence à afficher
            diff = self._diff_service.update(details)
            if diff:  # N'affiche que s'il y a une différence
                print(diff, end="", flush=True)
            else:
                print("\033[35m[DEBUG] No diff to display\033[0m")
            
            # Garde en mémoire si on termine par un saut de ligne
            self._last_newline = details.endswith("\n")
        
        elif message:
            # Si on était en train de streamer, on termine le stream
            if self._streaming:
                if not self._last_newline:
                    print()  # Ajoute un saut de ligne si nécessaire
                print("\n\033[36m=== End of stream ===\033[0m\n", flush=True)
                self._streaming = False
                self._first_chunk = True
            
            # Affiche les messages de progression en jaune
            print(f"\033[33m[INFO] {message}\033[0m")
            
            # Si c'est la fin d'une étape, affiche le total des tokens
            if status == "completed" and self._token_usages:
                # Calcule le total de tous les usages
                total_prompt = sum(usage['prompt_tokens'] for usage in self._token_usages)
                total_completion = sum(usage['completion_tokens'] for usage in self._token_usages)
                total_tokens = sum(usage['total_tokens'] for usage in self._token_usages)
                
                print(f"\n\033[36m[TOTAL TOKEN USAGE ACROSS ALL ATTEMPTS]")
                print(f"  Total prompt tokens: {total_prompt}")
                print(f"  Total completion tokens: {total_completion}")
                print(f"  Total tokens: {total_tokens}\033[0m")

def load_recipe_files(input_dir: str, recipe_slug: str) -> Tuple[str, Optional[bytes]]:
    """Load recipe text and image files from input directory."""
    input_path = Path(input_dir)
    
    # Load text content
    text_file = input_path / f"{recipe_slug}.txt"
    if not text_file.exists():
        raise FileNotFoundError(f"Recipe text file not found: {text_file}")
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    # Try to load image if it exists
    image_data = None
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        image_file = input_path / f"{recipe_slug}{ext}"
        if image_file.exists():
            with open(image_file, 'rb') as f:
                image_data = f.read()
            break
    
    return text_content, image_data

async def test_recipe_structurer(
    input_directory: str,
    recipe_slug: str,
    provider_type: ProviderType = "openai"  # Par défaut OpenAI
):
    """
    Teste la structuration d'une recette.
    
    Args:
        input_directory: Chemin vers le répertoire contenant les fichiers d'entrée
        recipe_slug: Slug de la recette à structurer
        provider_type: Type de provider à utiliser ("openai" ou "anthropic")
    """
    print(f"\nStarting structuring with {provider_type} provider...")
    print("=" * 80 + "\n")
    
    # Configure les chemins
    input_file = Path(input_directory) / f"{provider_type}_{recipe_slug}.txt"  # Added provider prefix back
    output_dir = Path(__file__).parent.parent.parent / "data" / "tests" / "structure" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Vérifie que le fichier d'entrée existe
        if not input_file.exists():
            raise FileNotFoundError(f"Recipe file not found at: {input_file}")
        
        # Charge la clé API appropriée
        api_key = os.getenv(f"{provider_type.upper()}_API_KEY")
        if not api_key:
            raise ValueError(f"{provider_type.upper()}_API_KEY not found in environment variables")
        
        # Crée le provider avec la clé API
        provider = create_provider(
            provider_type=provider_type,
            api_key=api_key,
            task="structure"
        )
        
        # Récupère le nom du modèle depuis le provider
        model_name = provider.model
        
        # Crée les noms de fichiers avec le nom du modèle
        output_file = output_dir / f"{model_name}_{recipe_slug}.json"
        error_file = output_dir / f"{model_name}_{recipe_slug}.error.json"
        
        structurer = RecipeStructurer(provider)
        
        # Crée le service de progression
        progress_service = MockProgressService()
        
        # Charge et structure le contenu
        print("\033[32m[START] Starting recipe structuring\033[0m\n")
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Crée un TextContent
        text_content = TextContent(
            main_content=content,
            selected_image_url=None
        )
        
        print("\033[32m[START] Sending prompt to LLM\033[0m\n")
        recipe_json = await structurer.generate_structured_recipe(
            content=text_content,
            source_url="",  # No source URL for text content
            image_urls=[],  # No image URLs for text content
            progress_service=progress_service,
            progress_id="test_progress"
        )
        
        # Valide la recette avec le modèle Pydantic simplifié
        recipe = LLMRecipe(**recipe_json)
        
        # Vérifie uniquement les champs essentiels
        assert recipe.metadata.name is not None, "Recipe should have a name"
        assert recipe.metadata.description is not None, "Recipe should have a description"
        assert recipe.metadata.servings > 0, "Recipe should have servings"
        assert len(recipe.ingredients) > 0, "Recipe should have ingredients"
        
        # Vérifie que tous les ingrédients sont utilisés
        used_ingredient_ids = set()
        for step in recipe.steps:
            for input in step.inputs:
                if input.input_type == "ingredient":
                    used_ingredient_ids.add(input.ref_id)
        
        all_ingredient_ids = {ing.id for ing in recipe.ingredients}
        unused_ingredients = all_ingredient_ids - used_ingredient_ids
        assert not unused_ingredients, f"Found unused ingredients: {unused_ingredients}"
        
        # Vérifie que tous les IDs référencés existent
        for step in recipe.steps:
            for input in step.inputs:
                if input.input_type == "ingredient":
                    assert input.ref_id in all_ingredient_ids, f"Referenced ingredient {input.ref_id} does not exist"
                elif input.input_type == "state":
                    # Vérifie que l'état référencé est la sortie d'une étape précédente
                    state_exists = any(
                        s.output_state.id == input.ref_id 
                        for s in recipe.steps[:recipe.steps.index(step)]
                    )
                    assert state_exists, f"Referenced state {input.ref_id} does not exist in previous steps"
        
        # Sauvegarde le résultat
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(recipe_json, f, indent=2, ensure_ascii=False)
        
        print(f"\n\033[32m[SUCCESS] Structured recipe saved to: {output_file}\033[0m")
        print("\033[32m[SUCCESS] Structuring successful!\033[0m\n")
        
    except Exception as e:
        # En cas d'erreur, sauvegarde le message d'erreur
        print(f"\n\033[31m[ERROR] Failed to structure recipe: {str(e)}\033[0m")
        print(f"\033[31m[ERROR] {str(e)}\033[0m")
        
        error_results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_message": str(e)
        }
        
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(error_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n\033[31m[ERROR] Error saved to: {error_file}\033[0m")
        raise

async def test_all_providers(input_directory: str, recipe_slug: str):
    """
    Teste la structuration avec tous les providers disponibles.
    
    Args:
        input_directory: Chemin vers le répertoire contenant les fichiers d'entrée
        recipe_slug: Slug de la recette à structurer
    """
    providers: list[ProviderType] = ["openai", "anthropic"]
    
    for provider in providers:
        try:
            await test_recipe_structurer(
                input_directory=input_directory,
                recipe_slug=recipe_slug,
                provider_type=provider
            )
        except Exception as e:
            print(f"\nTest failed for {provider}: {str(e)}")
            continue

if __name__ == "__main__":
    # Configure les chemins
    input_directory = str(Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "output")
    recipe_slug = "blanquette-de-veau"
    
    # Lance le test uniquement pour OpenAI
    asyncio.run(test_recipe_structurer(
        input_directory=input_directory,
        recipe_slug=recipe_slug,
        provider_type="anthropic"
    ))
