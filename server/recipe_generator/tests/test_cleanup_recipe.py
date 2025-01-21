import os
import asyncio
import json
from dotenv import load_dotenv
from ..services.content_cleaner import ContentCleaner
from ..models.text_content import TextContent
from ..llm.factory import create_provider
from ..config import load_config
from typing import Optional, Tuple, Literal
from pathlib import Path
from datetime import datetime
from .utils import MockProgressService, load_recipe_files

# Charge les variables d'environnement
load_dotenv()

ProviderType = Literal["openai", "anthropic"]

async def test_cleanup_recipe(
    input_directory: str,
    recipe_slug: str,
    provider_type: ProviderType = "openai"  # Par défaut OpenAI
):
    """
    Teste le nettoyage d'une recette.
    
    Args:
        input_directory: Chemin du dossier contenant les fichiers d'entrée
        recipe_slug: Slug de la recette à tester
        provider_type: Type de provider à utiliser
    """
    print(f"\nStarting cleanup with {provider_type} provider...")
    print("=" * 80 + "\n")
    
    # Configure les chemins
    input_file = Path(input_directory) / f"{recipe_slug}.txt"
    output_dir = Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "output"
    output_file = output_dir / f"{provider_type}_{recipe_slug}.txt"
    error_file = output_dir / f"{provider_type}_{recipe_slug}.error.txt"
    
    # Crée le répertoire de sortie si nécessaire
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Vérifie que le fichier d'entrée existe
        if not input_file.exists():
            raise FileNotFoundError(f"Recipe file not found at: {input_file}")
        
        # Récupère la clé API selon le provider
        if provider_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        # Crée le provider avec la clé API
        provider = create_provider(
            provider_type=provider_type,
            api_key=api_key,
            task="cleanup"
        )
        cleaner = ContentCleaner(provider)
        
        # Crée le service de progression
        progress_service = MockProgressService()
        
        # Crée la fonction de callback asynchrone
        async def progress_callback(text: str) -> None:
            await progress_service.update_step(
                progress_id="test",
                step="cleanup",
                status="in_progress",
                details=text
            )
        
        # Charge et nettoie le contenu
        print("\033[32m[START] Starting text content cleaning\033[0m\n")
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        print("\033[32m[START] Sending prompt to LLM\033[0m\n")
        cleaned_content = await cleaner.clean_text_content(
            text=content,
            on_progress=progress_callback
        )
        
        # Affiche le résumé final de l'usage des tokens
        await progress_service.update_step(
            progress_id="test",
            step="cleanup",
            status="completed",
            message="Cleanup completed"
        )
        
        # Sauvegarde le résultat
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        
        print(f"\n\033[32m[SUCCESS] Cleaned recipe saved to: {output_file}\033[0m")
        print("\033[32m[SUCCESS] Cleanup successful!\033[0m\n")
        
    except Exception as e:
        # En cas d'erreur, sauvegarde le message d'erreur
        print(f"\n\033[31m[ERROR] Failed to clean text content: {str(e)}\033[0m")
        print(f"\033[31m[ERROR] {str(e)}\033[0m")
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(str(e))
        print(f"\n\033[31m[ERROR] Error saved to: {error_file}\033[0m")
        raise

async def test_all_providers(input_directory: str, recipe_slug: str):
    """
    Teste le nettoyage avec tous les providers disponibles.
    
    Args:
        input_directory: Chemin vers le répertoire contenant les fichiers d'entrée
        recipe_slug: Slug de la recette à nettoyer
    """
    providers: list[ProviderType] = ["openai", "anthropic"]
    
    for provider in providers:
        try:
            await test_cleanup_recipe(
                input_directory=input_directory,
                recipe_slug=recipe_slug,
                provider_type=provider
            )
        except Exception as e:
            print(f"\nTest failed for {provider}: {str(e)}")
            continue

if __name__ == "__main__":
    # Configure les chemins par défaut
    input_directory = str(Path(__file__).parent.parent.parent / "data" / "tests" / "cleanup" / "input")
    recipe_slug = "blanquette-de-veau"
    
    # Lance le test avec tous les providers
    asyncio.run(test_all_providers(input_directory, recipe_slug)) 

class MockProgressService:
    def __init__(self):
        self._streaming = False
        self._first_chunk = True
        self._last_newline = False
        self._diff_service = StreamDiffService()
        self._token_usages = []  # Liste des usages
    
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
                self._token_usages.append(usage_data)
                # Affiche les stats d'usage en cyan
                print(f"\n\033[36m[TOKEN USAGE]")
                print(f"  Prompt tokens: {usage_data['prompt_tokens']}")
                print(f"  Completion tokens: {usage_data['completion_tokens']}")
                print(f"  Total tokens: {usage_data['total_tokens']}\033[0m")
                return
            
            # Début du streaming
            if self._first_chunk:
                print("\n=== Start of stream ===\n", flush=True)
                self._first_chunk = False
                self._streaming = True
            
            # Obtient uniquement la différence à afficher
            diff = self._diff_service.update(details)
            if diff:  # N'affiche que s'il y a une différence
                print(diff, end="", flush=True)
            
            # Garde en mémoire si on termine par un saut de ligne
            self._last_newline = details.endswith("\n")
        
        elif message:
            # Si on était en train de streamer, on termine le stream
            if self._streaming:
                if not self._last_newline:
                    print()  # Ajoute un saut de ligne si nécessaire
                print("\n=== End of stream ===\n", flush=True)
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
                
                print(f"\n\033[36m[TOTAL TOKEN USAGE]")
                print(f"  Total prompt tokens: {total_prompt}")
                print(f"  Total completion tokens: {total_completion}")
                print(f"  Total tokens: {total_tokens}\033[0m") 