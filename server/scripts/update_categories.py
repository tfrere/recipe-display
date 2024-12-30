import json
import os
import glob

# Mapping des anciennes aux nouvelles catégories
category_mapping = {
    'epicerie-salee': 'pantry-savory',
    'epicerie-sucree': 'pantry-sweet',
    'cremerie': 'dairy',
    'fruits-legumes': 'produce',
    'condiments': 'condiments',  # reste identique
    'boissons': 'beverages'
}

# Chemin vers le dossier data
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

# Trouver tous les fichiers .recipe.json
recipe_files = glob.glob(os.path.join(data_dir, '**/*.recipe.json'), recursive=True)

for recipe_file in recipe_files:
    print(f"Processing {recipe_file}")
    
    # Lire le fichier
    with open(recipe_file, 'r', encoding='utf-8') as f:
        try:
            recipe = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading {recipe_file}: {e}")
            continue
    
    # Mettre à jour les catégories dans les ingrédients
    if 'ingredients' in recipe:
        for ingredient in recipe['ingredients']:
            if 'category' in ingredient and ingredient['category'] in category_mapping:
                ingredient['category'] = category_mapping[ingredient['category']]
    
    # Sauvegarder le fichier
    with open(recipe_file, 'w', encoding='utf-8') as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)
        
print("Done updating categories!")
