"""Structured recipe prompt module."""
from typing import Dict, Any
import sys
import os
import json

def format_structured_recipe_prompt(content: str) -> str:
    """Format the structured recipe prompt with the provided data."""
    prompt_template = """
TASK: Convert the recipe content into a structured format following these guidelines:

1. CORE REQUIREMENTS:
   - Your response MUST be a valid JSON object matching the LLMRecipe schema
   - ALL RECIPE TEXT MUST BE IN ENGLISH:
     - Translate all ingredients, steps, and descriptions to English
     - Keep measurements in metric units
     - Maintain clarity and accuracy in translation

2. SCHEMA STRUCTURE:
   - name: Recipe name (string)
   - metadata:
     - title: Recipe name
     - description: Brief description
     - servings: Number of portions (integer)
     - recipeType: One of ["appetizer", "starter", "main_course", "dessert", "drink", "base"]
     - sourceImageUrl: Must be an empty string if no image URL provided
     - notes: List of additional notes (optional)
     - nationality: Country of origin (optional)
     - author: Recipe creator (optional)
     - bookTitle: Source book (optional)

   - ingredients: List of ingredients, each with:
     - id: Unique identifier (e.g., "ing1")
     - name: Ingredient name (WITHOUT quantity or preparation instructions)
     - category: One of ["meat", "produce", "egg", "dairy", "pantry", "spice", "condiment", "beverage", "seafood", "other"]
     IMPORTANT: Do NOT include amount or unit here. Quantities go in step inputs.

   - tools: List of special equipment, each with:
     - id: Unique identifier (e.g., "tool1")
     - name: Tool name (only non-standard equipment)

   - steps: List of preparation steps, each with:
     - id: Unique identifier (e.g., "step1")
     - action: Clear description of what to do
     - time: Duration ("5min", "1h", "1h30min") - REQUIRED for each step
     - stepType: One of ["prep", "combine", "cook"]
     - stepMode: One of ["active", "passive"]
     - inputs: List of ingredients/states used, each with:
       - input_type: One of ["ingredient", "state"]
       - ref_id: ID reference to ingredient/state
       - name: Description of the input
       - amount: Quantity (REQUIRED for ingredients, omit for states)
       - unit: One of ["g", "cl", "unit", "tbsp", "tsp", "pinch"] (REQUIRED for ingredients)
       IMPORTANT: unit not in kg or liter, you always have to use g and cl like in "2500g", "1100cl", "5unit", "3tbsp", "2tsp", "1pinch"
       - preparation: How to prepare (for ingredients)
     - output_state:
       - id: Unique identifier (e.g., "state1")
       - name: Description of resulting state
       - type: One of ["intermediate", "subrecipe", "final"]
       - description: Detailed description (optional)

   - final_state: REQUIRED - Represents the completed dish at the end of all steps
     The final_state MUST:
     - Have type="final"
     - Be referenced as the output_state of the last step
     - Include a complete description of the finished dish
     - Have a unique ID different from other states
     Example:
     {
       "id": "state_final",
       "name": "Completed Blanquette de Veau",
       "type": "final",
       "description": "A creamy, tender veal stew with mushrooms and pearl onions, finished with a rich white sauce and ready to serve."
     }

3. IMPORTANT RULES:
   - Generate unique IDs for all elements (ingredients, states, steps)
   - Ensure all references use correct IDs
   - Break down complex steps into smaller ones
   - Be specific with measurements and preparations
   - Ensure each step has clear inputs and outputs
   - ALWAYS include time for each step
   - ALWAYS include final_state with type="final" and make sure it's the output of the last step
   - Put ingredient quantities in step inputs, NOT in ingredients list
   - Each ingredient should appear at least once in step inputs with its quantity
   - The last step MUST produce the final_state as its output_state

4. FINAL STATE VALIDATION:
   - Verify that final_state exists and has type="final"
   - Ensure the last step's output_state matches the final_state
   - Include a detailed description of the completed dish in final_state
   - The final_state should represent the recipe at serving time

3. ⚠️ CRITICAL INGREDIENT AND STATE USAGE RULES ⚠️
   This is the most important part of the recipe structure!
   
   A. EVERY SINGLE INGREDIENT MUST BE USED:
      - Each ingredient in the ingredients list MUST appear in at least one step
      - If you're not sure how to use an ingredient, DO NOT add it to the ingredients list
      - Double-check all ingredients are used before finalizing the recipe
   
   B. EVERY STATE MUST BE PROPERLY CONNECTED:
      - Each state (except final_state) MUST be used as input in a subsequent step
      - States can't be "dead ends" - they must contribute to the final result
      - Every step's output_state must be used as input somewhere (except the last step)
   
   Example of INCORRECT state usage:
   {
     "steps": [
       {
         "id": "step1",
         "output_state": {
           "id": "state1",
           "name": "Chopped vegetables"
         }
       },
       {
         "id": "step2",
         "inputs": [],  // ❌ state1 is never used!
         "output_state": {
           "id": "state2",
           "name": "Final mixture"
         }
       }
     ]
   }
   
   Example of CORRECT state usage:
   {
     "steps": [
       {
         "id": "step1",
         "output_state": {
           "id": "state1",
           "name": "Chopped vegetables"
         }
       },
       {
         "id": "step2",
         "inputs": [
           {
             "input_type": "state",
             "ref_id": "state1"  // ✅ state1 is used as input
           }
         ],
         "output_state": {
           "id": "state2",
           "name": "Final mixture"
         }
       }
     ]
   }
   
   VALIDATION CHECKLIST:
   Before returning the JSON:
   1. List all ingredients and states
   2. For each ingredient:
      - Find where it's used in the steps
      - If not used, either add a step or remove it
   3. For each state (output_state from steps):
      - Find where it's used as input in a later step
      - If not used, either connect it or restructure steps
   4. Verify all references are valid:
      - Ingredient IDs exist in ingredients list
      - State IDs exist as output_state of previous steps
   5. Check the final_state:
      - Must be the output_state of the last step
      - Must have type="final"

INPUT CONTENT:
"""
    return prompt_template


if __name__ == "__main__":
    # Example usage
    example_content = """
    A delicious chocolate cake recipe.
    
    Ingredients:
    - 200g flour
    - 100g sugar
    - 2 eggs
    
    Instructions:
    1. Mix dry ingredients
    2. Add wet ingredients
    3. Bake at 180°C for 30 minutes
    """
    
    # Format and print the prompt
    prompt = format_structured_recipe_prompt(example_content)
    print("\nSTRUCTURED RECIPE PROMPT:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)