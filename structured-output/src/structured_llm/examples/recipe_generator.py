import asyncio
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env file
load_dotenv()

class Recipe(BaseModel):
    title: str = Field(description="The title of the recipe")
    ingredients: List[str] = Field(description="List of ingredients with quantities")
    steps: List[str] = Field(description="Step by step cooking instructions")
    prep_time_minutes: int = Field(description="Preparation time in minutes")
    cooking_time_minutes: int = Field(description="Cooking time in minutes")
    difficulty: str = Field(description="Difficulty level: 'easy', 'medium', or 'hard'")

async def generate_recipe(recipe_prompt: str) -> Recipe:
    # Initialize the model
    model = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0.7)
    
    # Create the output parser
    parser = JsonOutputParser(pydantic_object=Recipe)
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional chef who creates detailed recipes."),
        ("user", """Generate a detailed recipe based on this request: {recipe_request}
        Make sure to include all necessary ingredients with precise quantities,
        and detailed step-by-step instructions.
        
        {format_instructions}""")
    ])
    
    # Create the chain
    chain = prompt | model | parser
    
    # Generate the recipe
    recipe = await chain.ainvoke({
        "recipe_request": recipe_prompt,
        "format_instructions": parser.get_format_instructions()
    })
    
    return recipe

async def main():
    recipe_prompt = "Une délicieuse tarte aux pommes traditionnelle française"
    
    print("Generating recipe...")
    recipe = await generate_recipe(recipe_prompt)
    print("\nRecipe:")
    print(recipe.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 
