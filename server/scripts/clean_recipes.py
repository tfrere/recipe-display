import requests

def clean_recipes():
    """Clean all recipes and images from the server."""
    base_url = "http://localhost:3001/api/recipe-files"
    response = requests.delete(f"{base_url}/clean")
    print(f"Clean response: {response.status_code}")

if __name__ == "__main__":
    clean_recipes() 