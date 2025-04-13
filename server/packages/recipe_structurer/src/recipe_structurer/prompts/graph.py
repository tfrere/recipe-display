"""Prompt for generating the recipe preparation graph"""

graph_prompt = """You are a recipe graph generator that creates a detailed preparation flow.
Using the provided recipe base information, create a structured graph of preparation steps.

CRITICAL REQUIREMENTS:
1. Each step must have:
   - id: Unique identifier (e.g., "step1")
   - action: Clear description of what to do ( Try to keep the action as close as possible to the original recipe. You have to use cite all the ingredients used in the step. )
   - time: Duration ("5min", "1h", "1h30min")
   - stepType: One of ["prep", "combine", "cook"]
   - stepMode: One of ["active", "passive"]
   - subRecipe: Name of the sub-recipe this step belongs to (default: "main") ( Just add the main name, no need to add the recipe name before. Ex : "Black lime focaccia with smoky chipotle oil - smoky chipotle oil", you can keep only "smoky chipotle oil" )
   - inputs: List of ingredients or states used, each with:
     * input_type: "ingredient" or "state"
     * ref_id: ID of ingredient or state
     * name: Matching name
     * amount: Required for ingredients (number)
     * unit: One of ["g", "cl", "unit", "tbsp", "tsp", "pinch"]
     * initialState: Optional - describes the initial preparation state of the ingredient (e.g., "diced", "grated", "chopped", "sliced", "cubed", "minced", "julienned", "peeled")
   - output_state: Resulting state with:
     * id: Unique identifier
     * name: Descriptive name
     * type: One of ["intermediate", "subrecipe", "final"]
     * description: DETAILED description of what was achieved

2. Unit conversion rules:
   - Weights in grams (g)
   - Volumes in centiliters (cl) - convert ml to cl (1 cl = 10 ml)
   - Count in units (unit)
   - Spoons in tablespoons (tbsp) or teaspoons (tsp)
   - Very small amounts in pinches (pinch)

3. Graph structure rules:
   - Each ingredient must be used at least once
   - States must be properly chained between steps
   - You have to keep the exact steps from the original recipe.
   - Each step's output_state must be used as input in a later step (except final)
   - The last step's output_state must be the final_state
   - final_state must have type="final" and a comprehensive description
   - For the subRecipe :
      - Steps within a sub-recipe should have the same subRecipe value (matching the sub-recipe name)
      - If no explicit sub-recipe is mentioned, use "main" as the subRecipe value
      - If you have preheat step, you have to add it at the beginning of the concerned sub-recipe. It's mandatory.
      - If you have a step with "Preheat oven to 180°C (350°F)" you have to add it at the beginning of the concerned sub-recipe. ( often subRecipes where you have an oven step )

4. Ingredient initial state:
   - If an ingredient requires preparation before being used (like chopping, slicing, dicing, etc.), indicate this in the "initialState" field
   - Common initialState values include: "diced", "grated", "chopped", "sliced", "cubed", "minced", "julienned", "peeled", "quartered", etc.
   - Only add this field if the ingredient has a specific preparation requirement
   - The initialState should be derived from the recipe instructions
   - If an ingredient is used in its natural/whole form, omit the initialState field

Here is the recipe base information to use:
{recipe_base}

IMPORTANT: Return ONLY the JSON object containing steps and final_state, without any additional text or explanations."""