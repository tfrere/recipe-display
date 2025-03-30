"""Prompt for generating the recipe preparation graph"""

graph_prompt = """You are a recipe graph generator that creates a detailed preparation flow.
Using the provided recipe base information, create a structured graph of preparation steps.

CRITICAL REQUIREMENTS:
1. Each step must have:
   - id: Unique identifier (e.g., "step1")
   - action: Clear description of what to do
   - time: Duration ("5min", "1h", "1h30min")
   - stepType: One of ["prep", "combine", "cook"]
   - stepMode: One of ["active", "passive"]
   - inputs: List of ingredients or states used, each with:
     * input_type: "ingredient" or "state"
     * ref_id: ID of ingredient or state
     * name: Matching name
     * amount: Required for ingredients (number)
     * unit: One of ["g", "cl", "unit", "tbsp", "tsp", "pinch"]
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
   - Each step's output_state must be used as input in a later step (except final)
   - The last step's output_state must be the final_state
   - final_state must have type="final" and a comprehensive description

Here is the recipe base information to use:
{recipe_base}

IMPORTANT: Return ONLY the JSON object containing steps and final_state, without any additional text or explanations."""