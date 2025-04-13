import json

# Read first 10 URLs from text file
with open('recipe-scrapping/ottolenghi/recipes_urls_original.txt', 'r') as f:
    urls = [line.strip() for line in f.readlines()[:10]]

# Save as JSON
with open('urls.json', 'w') as f:
    json.dump(urls, f, indent=2)

print(f'Created urls.json with {len(urls)} URLs') 