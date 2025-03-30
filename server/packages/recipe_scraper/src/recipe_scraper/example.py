"""
Example usage of the RecipeScraper class.
"""

import asyncio
import json
from pathlib import Path

from recipe_scraper import RecipeScraper


async def scrape_from_url_example():
    """Example of scraping a recipe from a URL."""
    # Create the scraper
    scraper = RecipeScraper()
    
    # Example URL (change to a real recipe URL)
    url = "https://www.example.com/recipe"
    
    # Optional: Example auth values
    auth_values = {
        "type": "cookie",
        "values": {
            "session": "your-session-cookie"
        },
        "description": "Example auth"
    }
    
    # Set to None to disable authentication
    auth_values = None
    
    # Scrape the recipe
    recipe_data = await scraper.scrape_from_url(url, auth_values)
    
    # Save the result
    if recipe_data:
        output_dir = Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        slug = recipe_data.get("metadata", {}).get("slug", "recipe")
        
        with open(output_dir / f"{slug}.recipe.json", "w") as f:
            json.dump(recipe_data, f, indent=2)
            
        print(f"Recipe saved to {output_dir / f'{slug}.recipe.json'}")
    else:
        print("Failed to scrape recipe")


async def scrape_from_text_example():
    """Example of structuring a recipe from text."""
    # Create the scraper
    scraper = RecipeScraper()
    
    # Example recipe text
    recipe_text = """
    Tarte aux Pommes

    Ingrédients:
    - 1 pâte brisée
    - 6 pommes Golden
    - 50g de beurre
    - 3 cuillères à soupe de sucre
    - 1 sachet de sucre vanillé
    
    Instructions:
    1. Préchauffer le four à 210°C (thermostat 7).
    2. Étaler la pâte brisée dans un moule à tarte.
    3. Éplucher les pommes, les couper en quartiers puis en lamelles.
    4. Disposer les pommes sur la pâte.
    5. Répartir des petits morceaux de beurre sur les pommes.
    6. Saupoudrer de sucre et de sucre vanillé.
    7. Enfourner pour 30 minutes environ.
    8. Servir tiède ou froid.
    """
    
    # Structure the recipe
    recipe_data = await scraper.scrape_from_text(recipe_text)
    
    # Save the result
    if recipe_data:
        output_dir = Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        slug = recipe_data.get("metadata", {}).get("slug", "recipe")
        
        with open(output_dir / f"{slug}.recipe.json", "w") as f:
            json.dump(recipe_data, f, indent=2)
            
        print(f"Recipe saved to {output_dir / f'{slug}.recipe.json'}")
    else:
        print("Failed to structure recipe")


async def main():
    """Run the examples."""
    print("=== Recipe Scraper Examples ===")
    
    print("\n1. Scraping from URL example:")
    # Uncomment to run:
    # await scrape_from_url_example()
    
    print("\n2. Scraping from text example:")
    await scrape_from_text_example()


if __name__ == "__main__":
    asyncio.run(main()) 