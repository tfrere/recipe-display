import os
import requests
from pathlib import Path
import glob

def upload_recipes():
    """Upload all recipes and images to the server."""
    base_url = "http://localhost:3001/api/recipe-files"
    recipes_path = Path("data/recipes")
    images_path = recipes_path / "images"

    # Upload recipe files
    for recipe_file in recipes_path.glob("*.recipe.json"):
        if recipe_file.name != "auth_presets.json":
            with open(recipe_file, "rb") as f:
                files = {"file": (recipe_file.name, f, "application/json")}
                response = requests.post(f"{base_url}/upload", files=files)
                print(f"Uploaded {recipe_file.name}: {response.status_code}")

    # Upload images
    for image_file in images_path.glob("*"):
        if image_file.is_file():
            with open(image_file, "rb") as f:
                files = {"file": (image_file.name, f, "image/jpeg")}
                response = requests.post(f"{base_url}/upload-image", files=files)
                print(f"Uploaded image {image_file.name}: {response.status_code}")

if __name__ == "__main__":
    upload_recipes() 