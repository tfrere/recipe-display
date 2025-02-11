import asyncio
import json
import os
from typing import List, Dict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field, PositiveInt, HttpUrl
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.globals import set_verbose
from langchain.cache import SQLiteCache
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import WebBaseLoader
import langchain
import sys
sys.path.append("src")
from structured_llm.examples.recipe import LLMRecipe, LLMMetadata, Ingredient, Step, State, StepInput
from structured_llm.examples.recipe_validator import RecipeValidator
from structured_llm.examples.recipe_prompt import BASE_PROMPT

# Enable verbose mode and caching
set_verbose(True)
langchain.cache = SQLiteCache(database_path=".langchain.db")

# Load environment variables from .env file
load_dotenv()

def save_recipe_to_file(recipe: LLMRecipe, provider: str, attempt_type: str = "normal"):
    """Save recipe to a JSON file in the test directory"""
    # Create filename based on recipe name and provider
    recipe_name = recipe.metadata.title.lower().replace(" ", "_")
    filename = f"test/{recipe_name}_{provider}_{attempt_type}.json"
    
    # Save recipe to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(recipe.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\nRecipe saved to {filename}")

async def fetch_recipe_from_url(
    url: str, 
    headers: Dict[str, str] | None = None, 
    cookies: Dict[str, str] | None = None
) -> str:
    """Fetch recipe content from a URL with optional authentication"""
    # Prepare requests_kwargs with headers, cookies and verify
    requests_kwargs = {
        "verify": False  # Utile pour les sites avec des certificats auto-signés
    }
    if headers:
        requests_kwargs["headers"] = headers
    if cookies:
        requests_kwargs["cookies"] = cookies

    loader = WebBaseLoader(
        web_paths=[url],
        requests_kwargs=requests_kwargs
    )
    docs = loader.load()
    return docs[0].page_content

def get_llm(provider: Literal["anthropic", "deepseek"]):
    """Get the appropriate LLM based on provider"""
    if provider == "anthropic":
        return ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0.7,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            streaming=True
        )
    else:  # deepseek
        return ChatOpenAI(
            model="deepseek-chat",
            temperature=0.7,
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
            streaming=True
        )

async def generate_recipe(
    recipe_prompt: str, 
    provider: Literal["anthropic", "deepseek"] = "anthropic",
    url: str | None = None,
    auth_headers: Dict[str, str] | None = None,
    auth_cookies: Dict[str, str] | None = None
) -> LLMRecipe:
    # Initialize the model and validator
    model = get_llm(provider)
    validator = RecipeValidator()
    
    # Create a more explicit output parser
    parser = PydanticOutputParser(pydantic_object=LLMRecipe)
    
    # Create the prompt template with base prompt
    if url:
        content = await fetch_recipe_from_url(url, headers=auth_headers, cookies=auth_cookies)
        system_message = f"{BASE_PROMPT}\n\nHere's the recipe content from {url}:\n{content}\n\nIMPORTANT: Return ONLY the JSON object, without any additional text or explanations."
    else:
        system_message = f"{BASE_PROMPT}\n\nIMPORTANT: Return ONLY the JSON object, without any additional text or explanations."
    
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    from langchain_core.prompts import ChatPromptTemplate
    
    # Create message templates
    system_template = SystemMessage(content=system_message)
    human_template = HumanMessage(content="{input}")
    
    # Create a function to format validation errors
    def format_validation_errors(errors: List[str]) -> str:
        if not errors:
            return ""
        return "\n\n⚠️ Previous validation errors:\n" + "\n".join(f"- {error}" for error in errors)
    
    # Create the chain
    chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {
            "input": x["prompt"] + format_validation_errors(x.get("errors", []))
        })
        | ChatPromptTemplate.from_messages([system_template, human_template])
        | model
        | parser
    )
    
    config = RunnableConfig(
        callbacks=[],
        configurable={"stream": True},
        run_name="Recipe Generation"
    )
    
    # Try generating the recipe with retries
    max_attempts = 3
    last_response = None
    last_errors = []
    
    for attempt in range(max_attempts):
        try:
            print(f"\nAttempt {attempt + 1}...")
            
            # Generate recipe with validation feedback
            recipe = await chain.ainvoke(
                {
                    "prompt": recipe_prompt,
                    "errors": last_errors
                },
                config=config
            )
            
            # Validate recipe
            errors = validator.validate_recipe(recipe)
            if not errors:
                return recipe
                
            print(f"\nValidation errors:\n{json.dumps(errors, indent=2)}")
            last_response = recipe
            last_errors = errors
            
        except Exception as e:
            print(f"\nAttempt {attempt + 1} failed with error: {str(e)}")
            if attempt < max_attempts - 1:
                print("Retrying with error feedback...")
            else:
                raise
    
    raise ValueError(f"Failed to generate valid recipe after {max_attempts} attempts")

async def main():
    # Load auth presets
    with open("auth_presets.json", "r") as f:
        auth_presets = json.load(f)
    
    # Test recipe from URL with auth
    print("\nTesting Ottolenghi recipe extraction...")
    url = "https://books.ottolenghi.co.uk/jerusalem/recipe/stuffed-aubergine-with-lamb-pine-nuts/"
    
    # Get Ottolenghi credentials from presets
    ottolenghi_preset = auth_presets.get("books.ottolenghi.co.uk", {})
    print(f"\nUsing auth preset: {json.dumps(ottolenghi_preset, indent=2)}")
    
    auth_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    auth_cookies = ottolenghi_preset.get("values", {})
    
    try:
        print("\nFetching recipe content...")
        content = await fetch_recipe_from_url(url, headers=auth_headers, cookies=auth_cookies)
        print(f"\nFetched content:\n{content}")
        
        print("\nGenerating structured recipe...")
        recipe = await generate_recipe(
            "Convert this Ottolenghi recipe to a structured format", 
            url=url,
            auth_headers=auth_headers,
            auth_cookies=auth_cookies
        )
        print("\nStructured Recipe:")
        print(json.dumps(recipe.model_dump(), indent=2, ensure_ascii=False))
        
        # Save recipe to file
        save_recipe_to_file(recipe, "anthropic", "ottolenghi")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, '__cause__'):
            print(f"Caused by: {str(e.__cause__)}")

if __name__ == "__main__":
    # Create a new event loop and run the main function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close() 
