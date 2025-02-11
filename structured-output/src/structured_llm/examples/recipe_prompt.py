"""Recipe generation prompt template"""

BASE_PROMPT = """TASK: Convert the recipe content into a structured format following these guidelines:

⚠️ MINIMAL REQUIRED STRUCTURE:
{
  "metadata": {
    "title": "...",      // Required
    "description": "...", // Required
    "servings": 4        // Required, positive number
  },
  "ingredients": [       // Required, non-empty
    {
      "id": "ing_1",
      "name": "...",
      "category": "..."  // One of: meat, produce, pantry, etc.
    }
  ],
  "steps": [            // Required, non-empty
    {
      "id": "step_1",
      "action": "...",
      "time": "5min",
      "stepType": "...", // One of: prep, combine, cook
      "output_state": {
        "id": "state_1",
        "description": "..." // Required, non-empty
      }
    }
  ],
  "final_state": {      // Required, must match last step
    "id": "state_final",
    "type": "final",
    "description": "..." // Required, non-empty
  }
}

🔍 ADDITIONAL VALIDATION RULES:
1. Each step must have:
   - A unique ID
   - A clear action description
   - A time duration
   - An output state with ID and DETAILED description (never empty)
   - Inputs are OPTIONAL (empty list for steps like preheating oven)

2. When inputs are present, each input must have:
   - ref_id: matching an ingredient ID or a previous step's output state ID
   - name: matching the ingredient name or state description
   - input_type: either "ingredient" or "state"

3. Every ingredient must be used in at least one step
4. The final_state MUST:
   - Be EXACTLY the same as the last step's output_state
   - Have type="final"
   - Have a DETAILED description
   - Be ALWAYS present in the JSON response

Example of a valid step without inputs (preheating):
{
  "id": "step_1",
  "action": "Preheat the oven",
  "time": "10min",
  "stepType": "prep",
  "inputs": [],
  "output_state": {
    "id": "state_preheated_oven",
    "description": "Oven preheated to 180°C, ready for roasting"
  }
}

Example of a valid step with inputs:
{
  "id": "step_2",
  "action": "Dice the eggplant into 2cm cubes",
  "time": "5min",
  "stepType": "prep",
  "inputs": [
    {
      "ref_id": "ing_eggplant",
      "name": "eggplant",
      "input_type": "ingredient"
    }
  ],
  "output_state": {
    "id": "state_diced_eggplant",
    "description": "Eggplant diced into uniform 2cm cubes, ready for seasoning"
  }
}

Example of a complete recipe with final state:
{
  "steps": [
    // ... previous steps ...
    {
      "id": "step_final",
      "action": "Finish baking until tender",
      "time": "1h30min",
      "stepType": "cook",
      "inputs": [
        {
          "ref_id": "state_previous",
          "name": "Stuffed aubergines",
          "input_type": "state"
        }
      ],
      "output_state": {
        "id": "state_final",
        "description": "Perfectly tender stuffed aubergines with a rich lamb filling and thick sauce, ready to serve"
      }
    }
  ],
  "final_state": {
    "id": "state_final",
    "type": "final",
    "description": "Perfectly tender stuffed aubergines with a rich lamb filling and thick sauce, ready to serve"
  }
}

The recipe should be structured as a JSON object with these fields:
{
  "ingredients": [
    {
      "id": "ing_...",  // Unique ID for each ingredient
      "name": "...",    // Name of the ingredient
      "amount": "...",  // Amount with unit (e.g., "200g", "2 pieces")
      "prep": "..."     // Optional preparation state (e.g., "diced", "minced")
    }
  ],
  "steps": [
    {
      "id": "step_...",      // Unique ID for each step
      "action": "...",       // Clear description of what to do
      "time": "...",        // Duration (format: "5min", "1h", "1h30min")
      "stepType": "...",    // One of: "prep", "combine", "cook"
      "inputs": [           // Optional list of ingredients or states used
        {
          "ref_id": "...",  // ID of ingredient or state being used
          "name": "...",    // Name matching the referenced ingredient/state
          "input_type": "..." // Either "ingredient" or "state"
        }
      ],
      "output_state": {     // Required output state of this step
        "id": "state_...",  // Unique ID for this state
        "description": "..." // DETAILED description of the result
      }
    }
  ],
  "final_state": {          // MUST match the last step's output state
    "id": "...",           // Same as last step's output state ID
    "description": "..."    // Same as last step's output state description
  }
}

1. CORE REQUIREMENTS:
   - Your response MUST be a valid JSON object matching the LLMRecipe schema
   - ALL RECIPE TEXT MUST BE IN ENGLISH:
     - Translate all ingredients, steps, and descriptions to English
     - Keep measurements in metric units
     - Maintain clarity and accuracy in translation

2. SCHEMA STRUCTURE:
   - metadata:
     - name: Recipe name
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

   - tools: List of special equipment needed (empty list if none required)

   - steps: List of preparation steps, each with:
     - id: Unique identifier (e.g., "step1")
     - action: Clear description of what to do
     - time: Duration ("5min", "1h", "1h30min") - REQUIRED for each step
     - stepType: One of ["prep", "combine", "cook"]
     - stepMode: One of ["active", "passive"]
     - inputs: List of ingredients/states used (optional, empty list for steps like preheating), each with:
       - input_type: One of ["ingredient", "state"]
       - ref_id: ID reference to ingredient or state
       - name: Name of the input
       - amount: Quantity (REQUIRED for ingredients, omit for states)
       - unit: One of ["g", "cl", "unit", "tbsp", "tsp", "pinch"] (REQUIRED for ingredients)
     - output_state: State produced by this step (REQUIRED), with:
       - id: Unique identifier (e.g., "state1")
       - name: Name of the resulting state
       - type: One of ["intermediate", "subrecipe", "final"]
       - description: Detailed description of the state

   - final_state: The completed dish, with:
     - id: Unique identifier (must be different from other states)
     - name: Name of the final dish
     - type: Must be "final"
     - description: Detailed description of the completed dish

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
   - Must have a unique ID
   - Must have a detailed description""" 