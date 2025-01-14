import json
import glob
import os
from slugify import slugify

inputFolderUrl = '../data/json/2/'
outputFolderUrl = '../../hugo/assets/data/'

debug = False
recipes = []
recipesIndex = []
ingredient_list = []
ingredient_list_with_score = []
total_recipes = 0
total_ingredients = 0

if(debug):
    recipes = glob.glob(inputFolderUrl + "almond-butter-cake-with-cardamom-and-baked-plums.json")
else:
    recipes = glob.glob(inputFolderUrl + "*.json")

def uniqueList(listToUnique):
    return list(set(listToUnique))

for i, recipeFile in enumerate(recipes):
    with open(recipeFile, 'r') as fp:
        recipeJson = json.loads(fp.read())

        total_recipes += 1

        for ingredient in recipeJson["ingredients"]:
            if(ingredient["name"]):
                total_ingredients += 1
                ingredient_list.append(ingredient["name"])

        tags = ""
        for tag in recipeJson["tags"]:
            tags += "" + tag.replace("-", " ") + ", "

        isSimple = len(recipeJson["ingredients"]) <= 10

        tags += recipeJson['title'] + ", " 
        if(isSimple):
                tags += "quick" + ", " 
        tags += recipeJson["book"]

        recipesIndex.append({
            "id": i,
            "name": recipeJson['title'],
            "url": recipeJson['slug'],
            "image_file_name": recipeJson['image_file_name'],
            "tags": tags
        })

uniqueIngredidentList = uniqueList(ingredient_list)

with open(outputFolderUrl + 'index.json', 'w') as fp:

    data = recipesIndex
    fp.write(json.dumps(data))

with open(outputFolderUrl + 'meta.json', 'w') as fp:

    data = {
        "total_ingredients": len(uniqueIngredidentList),
        "total_recipes": total_recipes,
        "ingredient_list": uniqueIngredidentList
    }

    fp.write(json.dumps(data))