import os
import requests
from bs4 import BeautifulSoup

baseUrls = [
    "https://www.academiedugout.fr/recettes/c/entree_2?sort=recentes",
    "https://www.academiedugout.fr/recettes/c/plat_13?sort=recentes",
    "https://www.academiedugout.fr/recettes/c/dessert_3?sort=recentes"
]


def getPage(url):
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')


def getRecipeUrls(baseUrl):
    recipe_urls = []
    page = 1
    while True:
        url = f"{baseUrl}&page={page}"
        print(f"Getting {url}")
        soup = getPage(url)
        recipes = soup.find_all(class_="mod-recipe")
        print(f"Found {len(recipes)} recipes for {url}")
        if not recipes:
            break
        for recipe in recipes:
            a_tag = recipe.find("a", href=True)
            if a_tag and a_tag["href"].startswith("https://"):
                recipe_urls.append(a_tag["href"])
        # print(f"Found {recipe_urls[len(recipe_urls)-1]} recipe URLs")
        page += 1

    return recipe_urls


all_recipe_urls = []
for baseUrl in baseUrls:
    urls = getRecipeUrls(baseUrl)
    all_recipe_urls.extend(urls)

# Écrire les URLs dans un fichier
with open('recipe_urls.txt', 'w') as file:
    for url in all_recipe_urls:
        file.write(url + '\n')

print('Done')
