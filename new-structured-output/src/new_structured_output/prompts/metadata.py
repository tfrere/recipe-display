"""Prompt for extracting recipe metadata, ingredients, and tools"""

metadata_prompt = """You are a recipe parser that extracts basic recipe information.
Please parse this recipe to extract metadata, ingredients, and required tools.

REQUIRED JSON STRUCTURE:
{
  "metadata": {  // <-- IMPORTANT: All metadata fields MUST be inside this object
    "title": "Recipe name",
    "description": "Brief description",
    "servings": 4,  // integer
    "recipeType": "main_course",  // one of the allowed types
    "sourceImageUrl": "",
    "notes": [],
    "nationality": "",
    "author": "",
    "bookTitle": ""
  },
  "ingredients": [  // List of ingredients at root level
    {
      "id": "ing1",
      "name": "ingredient name",
      "category": "category"  // one of the allowed categories
    }
  ],
  "tools": []  // List of special tools at root level
}

CRITICAL REQUIREMENTS:
1. Metadata fields MUST be inside a "metadata" object:
   - title: Recipe name
   - description: Brief but clear description
   - servings: Number of portions (integer)
   - recipeType: One of ["appetizer", "starter", "main_course", "dessert", "drink", "base"]
   - sourceImageUrl: Empty string (no image)
   - notes: List of important tips (optional)
   - nationality: Country of origin (optional)
   - author: Recipe creator (optional)
   - bookTitle: Source book (optional)

2. List all ingredients with:
   - id: Unique identifier (e.g., "ing1", "ing2")
   - name: Ingredient name WITHOUT quantity
   - category: One of:
     * meat: All meat and poultry
     * produce: Fresh fruits and vegetables
     * egg: All types of eggs
     * dairy: Milk, cheese, and dairy products
     * pantry: Dry goods, flour, rice, pasta
     * spice: Herbs, spices, seasonings
     * condiment: Sauces, oils, vinegars
     * beverage: Drinks and liquid ingredients
     * seafood: Fish and seafood
     * other: Ingredients not fitting above

3. Identify special tools:
   - List ONLY non-standard equipment
   - Exclude basic items like bowls, spoons, knives
   - Include items like food processors, stand mixers, special pans

IMPORTANT: Return ONLY the JSON object matching the LLMRecipeBase schema, without any additional text or explanations."""