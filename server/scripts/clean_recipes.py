import requests
from dotenv import load_dotenv
import os

def clean_recipes():
    """Clean all recipes and images from the server."""
    load_dotenv()
    base_url = os.getenv("RECIPE_SERVER_URL", "https://recipes.tfrere.com/api/recipe-files")
    response = requests.delete(f"{base_url}/clean")
    print(f"Clean response: {response.status_code}")

if __name__ == "__main__":
    clean_recipes() 