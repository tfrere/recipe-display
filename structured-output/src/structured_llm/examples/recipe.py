from typing import List, Literal
from pydantic import BaseModel, Field

class Metadata(BaseModel):
    name: str
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

class BaseConfigModel(BaseModel):
    """Base model with extra fields forbidden for all recipe models."""
    class Config:
        extra = "forbid"

class LLMMetadata(BaseConfigModel):
    """
    Recipe metadata containing essential information about the recipe.
    Captures the basic information needed to identify and classify a recipe.
    """
    name: str = Field(description="The name of the recipe")
    description: str = Field(description="Brief description of the recipe")
    servings: int = Field(description="Number of portions this recipe yields")
    recipeType: Literal["appetizer", "starter", "main_course", "dessert", "drink", "base"] = Field(
        description="""
        Recipe classification:
        - appetizer: Small, savory bites served before a meal
        - starter: Light first course served at the table
        - main_course: Principal dish of a meal
        - dessert: Sweet course served at end of meal
        - drink: Beverages, both alcoholic and non-alcoholic
        - base: Fundamental recipes used as components
        """
    )
    sourceImageUrl: str = Field(description="URL of the recipe's image")
    notes: List[str] = Field(
        default=[],
        description="Additional notes or tips about the recipe"
    )
    nationality: str = Field(
        default="",
        description="Country or culture of origin for this recipe"
    )
    author: str = Field(
        default="",
        description="Creator or source of the recipe"
    )
    bookTitle: str = Field(
        default="",
        description="Book or publication where recipe was found"
    )

class Ingredient(BaseConfigModel):
    """
    Represents a single ingredient in the recipe.
    Each ingredient must be categorized and have a unique identifier.
    """
    id: str = Field(description="Unique identifier for this ingredient (e.g., 'ing1')")
    name: str = Field(description="Name of the ingredient")
    category: Literal[
        "meat", "produce", "egg", "dairy", "pantry", "spice", "condiment", 
        "beverage", "seafood", "other"
    ] = Field(
        description="""
        Ingredient category:
        - meat: All meat and poultry
        - produce: Fresh fruits and vegetables
        - egg: All types of eggs
        - dairy: Milk, cheese, and dairy products
        - pantry: Dry goods, flour, rice, pasta, etc.
        - spice: Herbs, spices, and seasonings
        - condiment: Sauces, oils, vinegars
        - beverage: Drinks and liquid ingredients
        - seafood: Fish and seafood
        - other: Ingredients not fitting above
        """
    )

class State(BaseConfigModel):
    """
    Represents the state of ingredients at any point in the recipe.
    Could be intermediate steps, sub-recipes, or the final dish.
    """
    id: str = Field(description="Unique identifier for this state (e.g., 'state1')")
    name: str = Field(description="Descriptive name of this state")
    type: Literal["intermediate", "subrecipe", "final"] = Field(
        description="""
        Type of state:
        - intermediate: Temporary states during preparation
        - subrecipe: Major components that could be reused
        - final: The completed dish
        """
    )
    description: str = Field(
        default="",
        description="Optional detailed description of this state"
    )

class StepInput(BaseConfigModel):
    """
    Represents an input to a recipe step.
    Could be an ingredient, or previous state.
    """
    input_type: Literal["ingredient", "state"] = Field(
        description="Type of input this represents. Tool inputs are optional."
    )
    ref_id: str = Field(description="ID reference to the ingredient, or state")
    name: str = Field(description="Name or description of the input")
    amount: float = Field(
        default=0.0,
        description="Quantity needed, only for ingredients"
    )
    unit: str = Field(
        default="",
        description="""
        Unit of measurement:
        - g: Weight in grams, ALWAYS USE THIS FOR SOLIDS
        - cl: Volume in centiliters, ALWAYS USE THIS FOR LIQUIDS
        - unit: Count of items
        - tbsp: Tablespoons
        - tsp: Teaspoons
        - pinch: Very small amount
        """
    )
    preparation: str = Field(
        default="",
        description="""
        How the ingredient should be prepared before this step.
        
        Cutting techniques:
        - "Julienne": Long, thin strips (matchsticks)
        - "Brunoise": Very small (1-3mm) cubes
        - "Small dice": 6mm cubes
        - "Medium dice": 12mm cubes
        - "Large dice": 20mm cubes
        - "Chiffonade": Thin ribbons of leafy vegetables
        - "Roughly chopped"
        - "Finely chopped"
        - "Minced"
        - "Sliced" (specify thickness if important)
        - "Quartered"
        - "Halved"
        
        Specific preparations:
        - "Toasted": For nuts or spices
        - "Crushed": For garlic or spices
        - "Ground": For spices
        - "Peeled": Only if not obvious
        
        Temperature states:
        - "Room temperature": For butter, eggs, etc.
        - "Cold": For ingredients that must be kept cold
        
        DO NOT include:
        - Quantities (handled by amount field)
        - Final states like "cooked", "baked", "thickened"
        - Generic states like "fresh", "plain", "whole"
        - Quality descriptors like "good quality" or "organic"
        - Preparation states in the ingredient name
        
        Examples:
        - "diced 1cm cubes"
        - "finely minced"
        - "roughly chopped and toasted"
        - "julienned 5cm lengths"
        - "room temperature and beaten"
        """
    )

class Step(BaseConfigModel):
    """
    Represents a single step in the recipe process.
    Each step must have clear outputs, and timing.
    Inputs are optional (empty list by default) for steps like preheating an oven.
    """
    id: str = Field(description="Unique identifier for this step")
    action: str = Field(description="Clear description of what to do in this step")
    time: str = Field(
        description="""
        Duration of the step in format:
        - Minutes only: "5min"
        - Hours only: "1h"
        - Hours and minutes: "1h30min"
        No spaces allowed.
        """
    )
    stepType: Literal["prep", "combine", "cook"] = Field(
        description="""
        Type of action:
        - prep: Ingredient preparation without heat
        - combine: Mixing ingredients without heat
        - cook: Any step involving heat
        """
    )
    stepMode: Literal["active", "passive"] = Field(
        description="""
        Level of attention needed:
        - active: Requires constant attention
        - passive: Can be left unattended
        """
    )
    inputs: List[StepInput] = Field(
        default=[],
        description="Ingredients or states used in this step. Can be empty for steps like preheating."
    )
    output_state: State = Field(description="Resulting state after this step")

class LLMRecipe(BaseConfigModel):
    """
    Complete recipe representation following a flow-based structure.
    Tracks the progression of ingredients through various states to the final dish.
    """
    metadata: LLMMetadata = Field(description="Recipe identification and classification")
    ingredients: List[Ingredient] = Field(description="All ingredients needed")
    tools: List[str] = Field(default=[], description="Special equipment required. Only include non-standard items like food processors, stand mixers, etc. Do not include basic items like bowls, spoons, or knives.")
    steps: List[Step] = Field(description="Sequence of steps to complete the recipe")
    final_state: State = Field(
        description="Final state of the completed recipe. Must have type='final'"
    )

class Recipe(BaseConfigModel):
    metadata: Metadata
    ingredients: List[Ingredient]
    tools: List[str] = Field(default=[])
    steps: List[Step]
    final_state: State