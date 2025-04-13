import os
import glob
import json
from pathlib import Path
import sys

def debug_file_content(file_path, max_length=500):
    """Affiche le contenu d'un fichier (limité à max_length caractères)"""
    try:
        with open(file_path, 'r') as f:
            content = f.read(max_length)
            if len(content) == max_length:
                content += "... (truncated)"
            return content
    except Exception as e:
        return f"Erreur lors de la lecture: {str(e)}"

def main():
    """Fonction principale de débogage"""
    print("\n===== DÉBOGAGE DU SERVEUR DE RECETTES =====\n")
    
    # Vérifier le répertoire de travail
    cwd = os.getcwd()
    print(f"Répertoire de travail actuel: {cwd}")
    
    # Chemins à vérifier
    base_path = Path("data")
    recipes_path = base_path / "recipes"
    authors_path = base_path / "authors.json"
    
    # Vérifier si les répertoires existent
    print(f"\nVérification des répertoires:")
    print(f"- base_path ({base_path}) existe: {os.path.exists(base_path)}")
    print(f"- recipes_path ({recipes_path}) existe: {os.path.exists(recipes_path)}")
    
    # Vérifier si authors.json existe
    print(f"\nVérification des fichiers essentiels:")
    print(f"- authors.json existe: {os.path.exists(authors_path)}")
    if os.path.exists(authors_path):
        print(f"- Contenu de authors.json: {debug_file_content(authors_path)}")
    
    # Lister les fichiers de recettes
    if os.path.exists(recipes_path):
        recipe_files = glob.glob(os.path.join(recipes_path, "*.recipe.json"))
        print(f"\nFichiers de recettes trouvés: {len(recipe_files)}")
        
        # Afficher les 5 premiers fichiers
        for i, recipe_file in enumerate(recipe_files[:5]):
            file_size = os.path.getsize(recipe_file)
            print(f"- {os.path.basename(recipe_file)} ({file_size} bytes)")
            
            # Vérifier si c'est un JSON valide
            try:
                with open(recipe_file, 'r') as f:
                    json_data = json.load(f)
                    title = json_data.get("metadata", {}).get("title", "Sans titre")
                    print(f"  - Titre: {title}")
                    print(f"  - JSON valide: Oui")
            except json.JSONDecodeError as e:
                print(f"  - JSON valide: Non - {str(e)}")
                print(f"  - Premiers caractères: {debug_file_content(recipe_file, 100)}")
        
        if len(recipe_files) > 5:
            print(f"... et {len(recipe_files) - 5} autres fichiers")
    else:
        print("\nAucun fichier de recette trouvé car le répertoire n'existe pas.")
    
    # Vérifier les variables d'environnement
    print("\nVariables d'environnement pertinentes:")
    for env_var in ["PORT", "DATA_DIR", "BASE_URL"]:
        print(f"- {env_var}: {os.environ.get(env_var, 'Non définie')}")
    
    print("\n===== FIN DU DÉBOGAGE =====\n")
    
if __name__ == "__main__":
    main() 