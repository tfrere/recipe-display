
import os
import re 
from bs4 import BeautifulSoup

baseUrl = "https://books.ottolenghi.co.uk/"
#books = ["simple", "flavour", "sweet", "nopi", "flavour", "cookbook", "otk-shelf-love", "jerusalem", "falastin"]
books = ["plenty", "plenty-more", "extra-good-things"]
outputFolderUrl = '../data/txt/recipes_urls.txt'

get_total_pages_regex = r"\/([0-9]*)\/$"
get_recipe_name = r"\/([a-z0-9\-]*)\/$"

def getPage(url):
    result  = os.popen("curl "+url+" -H 'cookie: SSESSdcfc4c6f51fcab09b2179daf0e4cc999=96cd99a1aa53ce55bd8026c6bc3e2d0c' --compressed --insecure").read()
    return BeautifulSoup(result)

def getRecipesUrls(page_urls):
    recipes_urls = []
    for a in page_urls:
        url = a['href']
        if "/recipe/" in url:
            recipes_urls.append(url)
    return recipes_urls

def getRecipeName(url):
    return re.search(get_recipe_name, url)[1]

def getTotalPages(url):
    return re.search(get_total_pages_regex, url)[1]


recipes_urls = []

for book in books:
    soup = getPage(baseUrl+book+"/recipes/")
    page_urls = soup.find_all('a', href=True,  class_="page-link")
    total_pages = getTotalPages(page_urls[-2]['href'])
    recipes_urls += getRecipesUrls(page_urls)

    for i in range(2, int(total_pages)):
        soup = getPage("https://books.ottolenghi.co.uk/"+book+"/recipes/page/"+str(i)+"/")
        page_urls = soup.find_all('a', href=True)
        recipes_urls += getRecipesUrls(page_urls)

with open(outputFolderUrl, 'w') as fp:
    for item in recipes_urls:
        fp.write("%s\n" % item)
    print('Done')

print("Scrap recipes done !")
