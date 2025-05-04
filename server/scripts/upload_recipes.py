import os
import requests
from pathlib import Path
import glob
from dotenv import load_dotenv

def upload_recipes():
    """Upload all recipes and images to the server."""
    load_dotenv()
    base_url = os.getenv("RECIPE_SERVER_URL", "https://recipes.tfrere.com/api/recipe-files")
    recipes_path = Path("data/recipes")
    images_path = recipes_path / "images"

    # Upload recipe files
    for recipe_file in recipes_path.glob("*.recipe.json*"):
        if recipe_file.name != "auth_presets.json":
            # Extract the base name without timestamp
            base_name = recipe_file.name.split(".recipe.json")[0] + ".recipe.json"
            with open(recipe_file, "rb") as f:
                files = {"file": (base_name, f, "application/json")}
                response = requests.post(f"{base_url}/upload", files=files)
                print(f"Uploaded {base_name}: {response.status_code}")

    # Upload images
    for image_file in images_path.glob("*"):
        if image_file.is_file():
            with open(image_file, "rb") as f:
                files = {"file": (image_file.name, f, "image/jpeg")}
                response = requests.post(f"{base_url}/upload-image", files=files)
                print(f"Uploaded image {image_file.name}: {response.status_code}")

if __name__ == "__main__":
    upload_recipes() 