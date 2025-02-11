from typing import List, Literal
from pydantic import BaseModel, Field

class LLMMetadata(BaseModel):
    """Recipe metadata containing essential information about the recipe"""
    title: str = Field(description="The name of the recipe")
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

class Ingredient(BaseModel):
    """Represents a single ingredient in the recipe"""
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

class State(BaseModel):
    """Represents the state of ingredients at any point in the recipe"""
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

class StepInput(BaseModel):
    """Represents an input to a recipe step"""
    input_type: Literal["ingredient", "state"] = Field(
        description="Type of input (ingredient or intermediate state)"
    )
    ref_id: str = Field(description="Reference to ingredient ID or state ID")
    name: str = Field(description="Name of the input (matching ingredient or state)")
    amount: float | None = Field(
        default=None,
        description="Quantity (required for ingredients, omitted for states)"
    )
    unit: Literal["g", "cl", "unit", "tbsp", "tsp", "pinch"] | None = Field(
        default=None,
        description="Unit of measurement (required for ingredients, omitted for states)"
    )

class Step(BaseModel):
    """Represents a single step in the recipe preparation"""
    id: str = Field(description="Unique identifier for this step")
    action: str = Field(description="Clear description of what to do")
    time: str = Field(description="Duration (format: '5min', '1h', '1h30min')")
    stepType: Literal["prep", "combine", "cook"] = Field(
        description="""
        Type of step:
        - prep: Preparation steps like chopping, measuring
        - combine: Mixing ingredients together
        - cook: Applying heat or cold
        """
    )
    stepMode: Literal["active", "passive"] = Field(
        description="""
        Mode of step:
        - active: Requires constant attention
        - passive: Can be left unattended
        """
    )
    inputs: List[StepInput] = Field(
        default=[],
        description="List of ingredients or states used in this step"
    )
    output_state: State = Field(description="Resulting state after this step")

class LLMRecipeBase(BaseModel):
    """First part of the recipe containing metadata, ingredients and tools"""
    metadata: LLMMetadata = Field(description="Recipe identification and classification")
    ingredients: List[Ingredient] = Field(description="All ingredients needed")
    tools: List[str] = Field(
        default=[],
        description="Special equipment required. Only include non-standard items like food processors, stand mixers, etc. Do not include basic items like bowls, spoons, or knives."
    )

class LLMRecipeGraph(BaseModel):
    """Second part of the recipe containing the preparation graph"""
    steps: List[Step] = Field(description="Sequence of steps to complete the recipe")
    final_state: State = Field(
        description="Final state of the completed recipe. Must have type='final'"
    )

class LLMRecipe(BaseModel):
    """Complete recipe representation following a flow-based structure"""
    metadata: LLMMetadata = Field(description="Recipe identification and classification")
    ingredients: List[Ingredient] = Field(description="All ingredients needed")
    tools: List[str] = Field(
        default=[],
        description="Special equipment required. Only include non-standard items like food processors, stand mixers, etc. Do not include basic items like bowls, spoons, or knives."
    )
    steps: List[Step] = Field(description="Sequence of steps to complete the recipe")
    final_state: State = Field(
        description="Final state of the completed recipe. Must have type='final'"
    ) 