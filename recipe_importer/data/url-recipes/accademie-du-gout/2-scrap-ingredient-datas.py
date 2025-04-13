import os
import json
from bs4 import BeautifulSoup


def getPage(url):
    result = os.popen(
        "curl "+url+" -H 'cookie: PHPSESSID2=be2fc426723c0905261c5593faaff065' --compressed --insecure").read()
    return BeautifulSoup(result, 'html.parser')


def extractInformation(url):
    page = getPage(url)
    # Vous devez remplacer 'selector_for_name' par le véritable sélecteur pour extraire le nom de l'ingrédient
    name = page.select_one('.pedia-header__title').text.strip()
    desc = page.select_one(
        'body > div.wrapper.js-stickybit-parent > div.content > section:nth-child(2) > div > div > div > p').text.strip()
    season_list = page.select_one(
        'body > div.wrapper.js-stickybit-parent > div.content > section:nth-child(2) > div > section:nth-child(2) > div > p').text.strip()

    # Ajoutez ici d'autres extractions si nécessaire
    return {'name': name, 'url': url}


ingredient_urls = []
with open('ingredients_urls.txt', 'r') as file:
    ingredient_urls = file.readlines()

ingredients_data = []

for url in ingredient_urls:
    ingredient_data = extractInformation(url.strip())
    ingredients_data.append(ingredient_data)

# Écriture des données dans un fichier JSON
os.makedirs('data', exist_ok=True)
with open('data/ingredients-data.json', 'w') as json_file:
    json.dump(ingredients_data, json_file, ensure_ascii=False, indent=4)

print('Done')
