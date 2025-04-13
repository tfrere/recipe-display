import json
import glob
import re
import os
from bs4 import BeautifulSoup
from slugify import slugify

i = 0
debug = False
recipes = []

inputFolderUrl = "../data/html/"

outputFolderUrl = "../data/json/1/"
outputImageFolderUrl = "../data/images/"

if(debug):
    recipes = glob.glob(inputFolderUrl + "a-ja-bread-fritters.html")
else:
    recipes = glob.glob(inputFolderUrl + "*.html")


def getRecipeName(url):
    get_recipe_name_regex = r"\/([a-z0-9\-]*).html$"
    return re.search(get_recipe_name_regex, url)[1]

def getIngredientSlug(url):
    get_recipe_name_regex = r"\/([a-z0-9\-]*)$"
    return re.search(get_recipe_name_regex, url)[1]

def parseRecipeUrl(content):
    return content.findAll("link", {"rel" : "canonical"})[0]["href"]

    
def parseIngredients(content):
    ingLists = []

    asideContent = content.select_one('.recipe__aside')
    lists = asideContent.find_all('ul')
    titles = asideContent.find_all('h3')

    for i, item in enumerate(lists):
        dicIndex = ""
        if(i == 0):
            dicIndex = "main"
        else:
            dicIndex = titles[i-1].get_text()

        for ing in item.find_all('li'):

            # print(ing)

            try:
                qty = ing.select_one('strong').get_text()
            except:
                qty = ""

            try:
                name = getIngredientSlug(ing.select_one('a')["href"])
            except:
                name = ""

            
            value =  {
                "qty": qty,
                "name": name,
                "value":  trimAndRemoveBreaklines(ing.get_text()),
                "category": trimAndRemoveBreaklines(dicIndex),
            }
            ingLists.append(value)
    return ingLists

def parseTitle(content):
    return content.select_one('.recipe__title').contents[0]

def parseBook(content):
    return content.select_one('.current')["href"][1:]

def parseSize(content):
    return content.select_one('.recipe-meta--yield').contents[0]

def parseAbout(content):
    return content.find_all("div",attrs={"itemprop": "description"})[0].find_next_sibling("div").get_text()

def parseNotes(content):
    notes = ''
    if(content.select_one('.recipe__aside').find_all('p')):
        notes = content.select_one('.recipe__aside').find_all('p')[0].get_text()
    return notes

def parseImageFileName(slug, img_url):
    return f'{slug}.{img_url.split(".")[-1]}'

def parseImgUrl(content):
    imgs = content.select_one('.recipe__aside').find_all("img")
    return imgs[0]["src"]

def parseBookTags(content):
    keywords =  []
    for ing in filter(lambda score: score != " ", content.select_one('.recipe__types').contents):
        keywords.append( {"value": slugify(ing.get_text()), "category": "book-tag"})

    if(content.select_one('.simple-icons')):
        for ing in content.select_one('.simple-icons').find_all('a'):
            keywords.append( {"value": slugify(ing.get_text()), "category": "book-tag"})

    for ing in content.select_one('.entry-categories').find_all('a'):
        keywords.append( {"value": slugify(ing.get_text()), "category": "book-tag"})

    return keywords

def parseSteps(content):
    steps = []
    for ing in content.select_one('.recipe-list').find_all('li'):
        value = ing.get_text()
        steps.append(trimAndRemoveBreaklines(value))
    return steps

def trimAndRemoveBreaklines(string):
    return string.replace("\n", "").strip().lower()

def getNumberOfIngredients(ingrs):
    i = 0
    for ingredientBlock in ingrs:
        for ingredient in ingredientBlock['ingredients']:
            i += 1
    return i

    
def downloadImage(url, slug):

    img_file_format = url.split(".")[-1]
    imageLocalUrl = outputImageFolderUrl + slug + "." + img_file_format

    command = ("curl -H 'cookie: SSESSdcfc4c6f51fcab09b2179daf0e4cc999=96cd99a1aa53ce55bd8026c6bc3e2d0c' --compressed --insecure " + url + " > " + imageLocalUrl).replace("\n", " ")
    if(debug):
        print(command)
    os.popen(command).read()

for recipeFile in recipes:

    with open(recipeFile, 'r') as fp:
        item = fp.read()

        content = BeautifulSoup(item)
        slug = getRecipeName(recipeFile)

        title = parseTitle(content)
        url = parseRecipeUrl(content)
        img_url = parseImgUrl(content)
        image_file_name = parseImageFileName(slug, img_url)
        ingredients = parseIngredients(content)
        book = parseBook(content)
        about = trimAndRemoveBreaklines(parseAbout(content))
        notes = trimAndRemoveBreaklines(parseNotes(content))
        tags = parseBookTags(content)
        steps = parseSteps(content)
        size = trimAndRemoveBreaklines(parseSize(content))

        print(str(i) + " - " + title)
        i += 1
        
        if(debug):
            print(title)
            print("-----")
            print(slug)
            print("-----")
            print(url)
            print("-----")
            print(img_url)
            print("-----")
            print(size)
            print("-----")
            print(about)
            print("-----")
            for step in steps:
                print(step)

        recipeJson = {
            "title": title,
            "slug": slug,
            "book": book,
            "author": "ottolenghi",
            "about": about,
            "notes": notes,
            "size": size,
            "url": url,
            "image_url": img_url,
            "image_file_name": image_file_name,
            "ingredients": ingredients,
            "keywords": tags,
            "steps": steps,
        }

        downloadImage(img_url, slug)
        with open(outputFolderUrl + slug + '.json', 'w') as fp:
            json_data = json.dumps(recipeJson, ensure_ascii=False)
            fp.write(json_data)
            if(debug):
                print('Done')

print("Html to json done !")