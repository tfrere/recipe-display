
import os
import re
from bs4 import BeautifulSoup

baseUrl = "https://www.academiedugout.fr/ustensiles"


def getPage(url):
    result = os.popen(
        "curl "+url+" -H 'cookie: PHPSESSID2=be2fc426723c0905261c5593faaff065' --compressed --insecure").read()
    return BeautifulSoup(result)


index = 0
max_index = 12

ingredient_urls = []

while index < max_index:
    index += 1
    page = getPage(baseUrl + f"?page={index}")
    print(page)
    ingredients = page.find_all(class_="grid__item")
    for ingredient in ingredients:
        a_tag = ingredient.find("a", href=True)
        if a_tag:
            href = a_tag["href"]
            if href.startswith("https://"):
                ingredient_urls.append(href)

# Write the URLs to a text file
with open('ustenciles_urls.txt', 'w') as file:
    for url in ingredient_urls:
        file.write(url + '\n')
print('Done')
