import json
import glob
import os
from slugify import slugify

inputFolderUrl = '../data/json/2/'
outputFolderUrl = '../../obsidian/recipe-vault/recipes/'

debug = False
recipes = []

if(debug):
    recipes = glob.glob(inputFolderUrl + "almond-butter-cake-with-cardamom-and-baked-plums.json")
else:
    recipes = glob.glob(inputFolderUrl + "*.json")

mdRecipes = glob.glob(outputFolderUrl + "*.md")
for mdRecipe in mdRecipes:
    os.remove(mdRecipe)

for recipeFile in recipes:
    with open(recipeFile, 'r') as fp:
        recipeJson = json.loads(fp.read())

        recipeMd = f'# {recipeJson["title"]}\n\n'

        recipeMd += f'{recipeJson["url"]}\n\n'

        for typeWord in recipeJson["ingredients"]:
            if(typeWord["name"]):
                recipeMd += f'#{typeWord["name"]} '
        recipeMd += f'\n\n\n'

        recipeMd += f'![[{recipeJson["local_image_url"]}]]\n\n'

        recipeMd += f'## About\n'
        recipeMd += f'{recipeJson["about"]}\n\n'

        recipeMd += f'## Notes\n'
        recipeMd += f'{recipeJson["notes"]}\n\n'

        recipeMd += f'## Size\n'
        recipeMd += f'{recipeJson["size"]}\n\n'

        recipeMd += f'## Ingredients\n'
        for ingredient in recipeJson["ingredients"]:
            recipeMd += f'* {ingredient["value"]}\n'

        recipeMd += f'\n\n## Steps\n'
        for step in recipeJson["steps"]:
            recipeMd += f'* {step}\n'

        with open(outputFolderUrl + recipeJson["slug"] + '.md', 'w') as fp:
            fp.write(recipeMd)

print("Json to hugo md done !")