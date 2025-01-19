import json
import glob

debug = False
recipes = []

inputFolderUrl = '../data/json/1/'
outputFolderUrl = '../data/json/2/'

if(debug):
    recipes = glob.glob(inputFolderUrl + "almond-butter-cake-with-cardamom-and-baked-plums.json")
else:
    recipes = glob.glob(inputFolderUrl + "*.json")

for recipeFile in recipes:
    with open(recipeFile, 'r') as fp:
        recipe = json.loads(fp.read())

        recipe["tags"] = []

        for ingredient in recipe["ingredients"]:
            if(ingredient["name"]):
                recipe["tags"].append(ingredient["name"])

        with open(outputFolderUrl + recipe["slug"] + '.json', 'w') as fp:
            fp.write(json.dumps(recipe))

print("Extrapolation done !")