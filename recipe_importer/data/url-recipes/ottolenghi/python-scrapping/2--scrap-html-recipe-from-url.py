import os
import re 

intputFileUrl = '../data/txt/recipes_urls.txt'
outputFolderUrl = '../data/html/'

def getPage(url):
    command = ("curl "+url+" -H 'cookie: SSESSdcfc4c6f51fcab09b2179daf0e4cc999=96cd99a1aa53ce55bd8026c6bc3e2d0c' --compressed --insecure").replace("\n", " ")
    return os.popen(command).read()

def getRecipeName(url):
    get_recipe_name_regex = r"\/([a-z0-9\-]*)\/$"
    return re.search(get_recipe_name_regex, url)[1]

with open(intputFileUrl, 'r') as fp:
    for i, item in enumerate(fp):
        slug = getRecipeName(item)
        with open(outputFolderUrl + slug + '.html', 'w') as fp:
            fp.write(getPage(item))
            print('Done : ' + str(i))

print("Scap recipes done !")