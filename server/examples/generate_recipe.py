import asyncio
import sys
import json
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from recipe_generator.config import load_config
from recipe_generator.generator.recipe_generator import RecipeGenerator
from recipe_generator.storage.recipe_storage import RecipeStorage
from recipe_generator.prompts.cleanup_recipe import CLEANUP_PROMPT
from recipe_generator.prompts.structured_recipe import format_structured_recipe_prompt

async def main():
    """Main function to generate a recipe."""
    try:
        # Charger les constantes
        constants_path = Path(__file__).parent.parent / "shared" / "constants.json"
        with open(constants_path, 'r', encoding='utf-8') as f:
            constants = json.load(f)
        
        # Afficher les prompts
        print("\n=== CLEANUP PROMPT ===")
        print(CLEANUP_PROMPT)
        
        print("\n=== STRUCTURED RECIPE PROMPT ===")
        example_prompt = format_structured_recipe_prompt(
            content="Example content",
            constants=constants
        )
        print(example_prompt)
        
        print("\n=== DÉBUT DE LA GÉNÉRATION ===\n")
        
        # Charger la configuration
        config = load_config()
        
        # Créer le générateur de recettes et le stockage
        generator = RecipeGenerator(api_key=config["openai_api_key"])
        storage = RecipeStorage()
        
        # URL de test
        url = "https://books.ottolenghi.co.uk/jerusalem/recipe/stuffed-aubergine-with-lamb-pine-nuts/"
        print(f"\nGénération de la recette depuis {url}...")
        
        # Générer la recette
        recipe = await generator.generate_from_url(url)
        print("\nRecette générée avec succès !")
        
        # Sauvegarder la recette
        print("\nSauvegarde de la recette...")
        await storage.save_recipe(recipe, {"source_url": url})
        print("Recette sauvegardée !")
        
        # Afficher le résultat
        print("\nDétails de la recette :")
        print(recipe.model_dump_json(indent=2))
        
    except ValueError as e:
        if "existe déjà" in str(e):
            print(f"\nInfo : {str(e)}")
        else:
            print(f"\nErreur de validation : {str(e)}")
    except Exception as e:
        print(f"\nUne erreur est survenue : {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 