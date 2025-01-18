"""Pydantic models for recipe schema."""
from typing import List, Literal
from pydantic import BaseModel, Field

# METADATA

class Metadata(BaseModel):
    title: str
    description: str
    servings: int
    diets: List[Literal["omnivorous", "vegetarian", "vegan"]]
    seasons: List[Literal["spring", "summer", "autumn", "winter", "all"]]
    recipeType: Literal["appetizer", "starter", "main_course", "dessert", "drink", "base"]
    notes: List[str]
    imageUrl: str
    sourceImageUrl: str
    sourceUrl: str
    nationality: str
    author: str
    bookTitle: str
    slug: str
    totalTime: float
    quick: bool

class OpenAIMetadata(BaseModel):
    title: str
    description: str
    servings: int
    recipeType: Literal["appetizer", "starter", "main_course", "dessert", "drink", "base"]
    notes: List[str]
    sourceImageUrl: str
    nationality: str
    author: str
    bookTitle: str
    slug: str

    class Config:
        extra = "forbid"

# INGREDIENT

class Ingredient(BaseModel):
    id: str
    name: str
    unit: Literal["g", "ml", "unit", "tbsp", "tsp", "pinch"]
    category: Literal[
        "meat", "produce", "egg", "dairy", "pantry", "spice", "condiment", 
        "beverage", "seafood", "other"
    ]

    class Config:
        extra = "forbid"

class Tool(BaseModel):
    id: str
    name: str

    class Config:
        extra = "forbid"

# RECIPE REFERENCES

class ComponentRef(BaseModel):
    inputType: Literal["component"]
    ref: str
    type: Literal["ingredient", "tool"]
    amount: float

    class Config:
        extra = "forbid"

class StateRef(BaseModel):
    inputType: Literal["state"]
    ref: str
    preparation: str
    name: str

    class Config:
        extra = "forbid"

class SubRecipeRef(BaseModel):
    inputType: Literal["subRecipe"]
    ref: str  # ID de la sous-recette
    name: str  # Nom descriptif du résultat de la sous-recette

    class Config:
        extra = "forbid"

# STEP

class Step(BaseModel):
    id: str
    action: str
    time: str
    stepType: Literal["prep", "combine", "cook"]
    stepMode: Literal["active", "passive"]
    inputs: List[ComponentRef | StateRef | SubRecipeRef]
    output: StateRef

    class Config:
        extra = "forbid"

# SUB RECIPE 

class SubRecipe(BaseModel):
    id: str
    title: str
    ingredients: List[ComponentRef]
    steps: List[Step]

    class Config:
        extra = "forbid"

# RECIPE 

class Recipe(BaseModel):
    metadata: Metadata
    ingredients: List[Ingredient]
    tools: List[Tool]
    subRecipes: List[SubRecipe]

    class Config:
        extra = "forbid"

class OpenAIRecipe(BaseModel):
    metadata: OpenAIMetadata
    ingredients: List[Ingredient]
    tools: List[Tool]
    subRecipes: List[SubRecipe]

    class Config:
        extra = "forbid"

# class SubRecipeIngr(BaseModel):
#     amount: float
#     state: str

#     class Config:
#         extra = "forbid"


# class Ingr(BaseModel):
#     id: str
#     name: str
#     unit: Literal["g", "ml", "unit", "tbsp", "tsp", "pinch"]
#     category: Literal[
#         "meat", "produce", "dairy", "pantry-savory", 
#         "pantry-sweet", "spice", "condiments", 
#         "beverages", "autres"
#     ]

#     class Config:
#         extra = "forbid"

# class SubRec(BaseModel):
#     id: str
#     title: str
#     ingredients: List[SubRecipeIngr]
#     steps: List[Step]

#     class Config:
#         extra = "forbid"

# class OpenAIRecipe(BaseModel):
#     metadata: OpenAIMetadata
#     ingredients: List[Ingr]
#     subRecipes: List[SubRec]

#     class Config:
#         extra = "forbid"


# # Example usage
if __name__ == "__main__":
    import asyncio
    import json
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    import os

    async def stream_recipe():
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Example content
        content = """
        This is a recipe for a delicious chocolate cake.
        
        You'll need:
        - 200g dark chocolate
        - 200g butter
        - 200g sugar
        - 4 eggs
        - 200g flour
        - 1 tsp baking powder
        
        Instructions:
        1. Preheat oven to 180°C
        2. Melt chocolate and butter
        3. Mix sugar and eggs
        4. Add melted chocolate mixture
        5. Add flour and baking powder
        6. Bake for 25 minutes
        """

        # Create system message with instructions
        system_message = """
        You are a helpful cooking assistant that converts recipe text into structured data.
        Follow these guidelines:
        1. Extract all ingredients with their quantities
        2. Break down the recipe into logical sub-recipes (preparation, cooking, etc.)
        3. For each step, include precise timing information
        4. Categorize ingredients appropriately
        5. Include descriptive metadata about the recipe
        """

        try:
            # Stream the completion
            async with client.beta.chat.completions.stream(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": content}
                ],
                temperature=0.7,
                response_format=OpenAIRecipe
            ) as stream:
                print("Streaming response...")
                
                async for event in stream:
                    if event.type == "content.delta":
                        if event.parsed is not None:
                            # Print the partial response
                            print("\nPartial response:")
                            print(json.dumps(event.parsed, indent=2))
                    elif event.type == "content.done":
                        # Get the final completion
                        final_completion = await stream.get_final_completion()
                        final_dict = final_completion.model_dump()
                        recipe_data = final_dict['choices'][0]['message']['parsed']
                        
                        # Validate with our schema
                        recipe = OpenAIRecipe(**recipe_data)
                        print("\nFinal validated recipe:")
                        print(json.dumps(recipe.model_dump(), indent=2))
                    elif event.type == "error":
                        print(f"Error in stream: {event.error}")
                        raise ValueError(f"Stream error: {event.error}")

        except Exception as e:
            print(f"Error: {str(e)}")
            raise

    # Run the example
    asyncio.run(stream_recipe())


