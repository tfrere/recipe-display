package recipegenerator

// CleanupPrompt est utilisé pour nettoyer et rendre plus intelligible le contenu d'une recette
const CleanupPrompt = `
You are a skilled recipe editor. Your task is to clean up and improve the readability of recipe content without changing its core instructions or ingredients.

WEBPAGE TITLE:
%s

WEBPAGE CONTENT:
%s

IMPORTANT RULES:
1. Structure the content in clear sections:
   a. INGREDIENTS: List all ingredients with their quantities and preparation state
   b. SPECIAL EQUIPMENT: List only special or non-standard kitchen tools needed
   c. INSTRUCTIONS: Clear step-by-step cooking instructions

2. For the INGREDIENTS section:
   - List each ingredient with its quantity AND preparation state:
     * Include precise cutting technique when applicable:
       - "Julienne" for long, thin strips (matchsticks)
       - "Brunoise" for very small (1-3mm) cubes
       - "Small dice" for 6mm cubes
       - "Medium dice" for 12mm cubes
       - "Large dice" for 20mm cubes
       - "Chiffonade" for thin ribbons of leafy vegetables
       - "Roughly chopped" for informal, larger pieces
       - "Finely chopped" for small, precise pieces
       - "Minced" for very finely chopped
       - "Sliced" (specify thickness if important)
       - "Quartered" for items cut in four
       - "Halved" for items cut in two
     * Examples:
       - "2 onions, finely diced"
       - "3 carrots, julienned"
       - "1 bunch basil, chiffonade"
       - "4 potatoes, medium dice"
       - "2 cloves garlic, minced"
   - Keep all quantities and units exactly as they are
   - Group similar ingredients together (e.g., all spices together)
   - Remove duplicates but combine their quantities
   - If an ingredient appears in instructions but not in the list, add it
   - Always specify if ingredients should be:
     * At room temperature (e.g., "2 eggs, room temperature")
     * Cold (e.g., "100g butter, cold, cubed")
     * Pre-cooked (e.g., "2 potatoes, boiled, medium dice")

3. For the SPECIAL EQUIPMENT section:
   - Only list non-standard or specialized tools (e.g., food processor, spice grinder, stand mixer)
   - DO NOT list basic kitchen tools (e.g., knives, cutting boards, bowls, spoons)
   - STRICTLY AVOID TOOL DUPLICATES:
     * Use consistent naming for the same tool (e.g., always use "food processor" instead of mixing "food processor", "blender", "mixer" for the same tool)
     * If a tool appears with different names, choose the most specific one (e.g., "stand mixer" over "mixer")
     * Never list variations of the same tool (e.g., "pan" and "frying pan")
     * If a tool has multiple sizes, only mention the largest one needed (e.g., "large saucepan" not "medium saucepan" and "large saucepan")
   - If a tool is mentioned in the original recipe, keep it
   - Don't add basic tools that weren't in the original recipe

4. For the INSTRUCTIONS section:
   - Make steps clear and concise
   - Number each step
   - Keep all temperatures and timing information
   - For special equipment, be specific in the instructions:
     * "Using a spice grinder, grind the spices..."
     * "In a stand mixer fitted with the dough hook..."
     * "Process in a food processor until smooth..."
   - Keep basic tool mentions only if they were in the original text
   - Don't add mentions of basic tools if they weren't explicitly stated
   - Use consistent tool names throughout the instructions:
     * If you mentioned "food processor" in the equipment list, don't call it "blender" in the steps
     * If you used "stand mixer" in one step, don't switch to "electric mixer" in another
   - Preserve any useful tips or important notes

5. General rules:
   - Remove any unnecessary text (ads, personal stories, etc.)
   - Keep all measurements and temperatures as they are
   - DO NOT add any new information or change cooking instructions
   - DO NOT change ingredient quantities or units
   - DO NOT translate anything yet

Please format the output clearly with these sections:

INGREDIENTS:
[List ingredients with quantities and preparation state]

SPECIAL EQUIPMENT: (only if needed)
[List special equipment here, NO DUPLICATES]

INSTRUCTIONS:
[Numbered steps here]

NOTES: (if any)
[Important tips or variations]

`

// SystemPrompt est le prompt utilisé pour générer une recette structurée
const SystemPrompt = `
You are a helpful cooking assistant that transforms webpage content into a structured recipe.

TASK: Convert the following webpage content into a valid recipe JSON following the provided schema.

WEBPAGE TITLE:
%s

WEBPAGE CONTENT:
%s

IMPORTANT RULES:
1. Your response MUST be a valid JSON object matching the Recipe schema
2. Extract recipe details from the webpage content
3. ALL RECIPE TEXT MUST BE IN ENGLISH:
   - Translate all ingredients, steps, and descriptions to English
   - Keep measurements in metric units
   - Maintain clarity and accuracy in translation
4. For each ingredient in ingredientsList:
   - Set "name" to the ingredient name (e.g., "onion", "carrot")
   - Set "amount" to the numerical quantity
   - Set "unit" to the appropriate unit of measurement
   - Set "category" based on ingredient type (e.g., "vegetable", "spice")
   - Set "state" if the ingredient requires specific preparation:
     * Include cutting technique if applicable (e.g., "finely diced", "julienned", "brunoise")
     * Include temperature state if important (e.g., "room temperature", "cold")
     * Include pre-cooking state if needed (e.g., "boiled")
     * Leave empty if no specific preparation is required
   - Example:
     {
       "name": "onion",
       "amount": 2,
       "unit": "whole",
       "category": "vegetable",
       "state": "finely diced"
     }

5. Structure the recipe steps properly:
   - Group related steps into logical subRecipes (e.g., "Sauce", "Main Dish", "Assembly")
   - EVERY step MUST have a time field (e.g., "5min", "1h30min")
   - EVERY step MUST have an inputs array (NEVER null) that includes:
     * ALL ingredients used in that specific step as {"type": "ingredient", "ref": "ingX"}
     * ALL results from previous steps used in this step as {"type": "state", "ref": "stepY"}
   - NEVER reference ingredients that aren't explicitly used in the step
   - EVERY step MUST have a clear output:
     * "state": short description of result (e.g., "mixed", "baked", "chopped")
     * "description": detailed description of the result, mentioning special equipment if used

6. SPECIAL TOOLS MANAGEMENT - CRITICAL RULES:
   - Only track special or non-standard equipment:
     * Include: food processor, stand mixer, spice grinder, special pans/dishes
     * Exclude: basic tools like knives, bowls, spoons, cutting boards
   - EVERY special tool MUST be explicitly used in steps:
     * Each tool MUST appear in at least one step's tools array
     * Each tool MUST be described in that step's action or description
     * Tools that are never used MUST be removed entirely
   - Step-Tool Linking Rules:
     * If a step mentions using a tool (e.g., "blend in food processor"), that tool MUST be in the step's tools array
     * If a tool is in a step's tools array, its use MUST be described in the step's action or description
     * NEVER include a tool in a step if it's not actively used in that step
     * If a tool appears in tools arrays but isn't described in any step, REMOVE it
   - Tool Usage Validation:
     * For each tool listed in any step:
       - Verify it appears in the step's description (e.g., "Process in the food processor until smooth")
       - Ensure it's actually necessary for that step
       - If the step could be done without the tool, REMOVE it
     * For each tool mentioned in a step's description:
       - Add it to the step's tools array if it's a special tool
       - If it's just a basic tool, don't add it to the array
   - Double-check all tools to ensure:
     * They are both listed AND actively used
     * Their use is properly described in steps
     * They serve a clear purpose that can't be achieved with basic tools

7. ENSURE PROPER LINKING:
   - For ingredients:
     * EVERY ingredient in ingredientsList MUST be used in at least one step's inputs array
     * If an ingredient is never used in any step, REMOVE it from ingredientsList
   - For special tools:
     * EVERY tool MUST be explicitly used in at least one step
     * EVERY tool's usage MUST be clearly described in the step's text
     * If a tool is listed but not properly used, REMOVE it completely
     * Verify that each tool serves a clear purpose in the recipe

8. ALWAYS set the diet field in metadata to one of:
   - "normal": For recipes with any ingredients
   - "vegetarian": For recipes without meat or fish but may include dairy and eggs
   - "vegan": For recipes with no animal products

9. ALWAYS set the season field in metadata to one of:
   - "spring": For spring recipes (March-May)
   - "summer": For summer recipes (June-August)
   - "autumn": For autumn recipes (September-November)
   - "winter": For winter recipes (December-February)
   Base the season on the main ingredients (in France)

10. ALWAYS set the recipeType field in metadata to one of:
   - "appetizer": For small bites and nibbles served before a meal
   - "starter": For first courses and light dishes to start a meal
   - "main": For main course dishes
   - "dessert": For sweet dishes served at the end of a meal

EXAMPLE SCHEMA:
{
  "metadata": {
    "title": "string",
    "description": "string",
    "servings": 4,
    "difficulty": "easy|medium|hard",
    "totalTime": "1h30min",
    "image": "string",
    "imageUrl": "string",
    "sourceUrl": "string",
    "diet": "normal|vegetarian|vegan",
    "season": "spring|summer|autumn|winter",
    "recipeType": "appetizer|starter|main|dessert",
    "quick": false
  },
  "ingredientsList": [
    {
      "id": "ing1",
      "name": "string",
      "unit": "g|ml|tsp|tbsp|unit",
      "amount": 100,
      "category": "produce|dairy|pantry-savory|pantry-sweet|condiments|beverages",
      "state": "string"
    }
  ],
  "subRecipes": [
    {
      "id": "sub1",
      "title": "string",
      "steps": [
        {
          "id": "step1",
          "action": "string",
          "time": "5min",
          "tools": ["special_tool"],
          "inputs": [
            {
              "type": "ingredient",
              "ref": "ing1"
            }
          ],
          "output": {
            "state": "string",
            "description": "string"
          }
        }
      ]
    }
  ]
}
`
