"""Recipe cleanup prompt module."""
from typing import List
import sys
import os


def format_cleanup_recipe_prompt(content: str, image_urls: List[str]) -> str:
    """Format the cleanup recipe prompt with the provided data."""
    # Combine all prompts in the correct order
    # Static content first, dynamic content last

    prompt = """
You are a skilled recipe editor. Your task is to clean up and improve the readability of recipe content without changing its core instructions or ingredients.

CRITICAL VALIDATION RULE:
Before processing the content, you MUST verify that this is actually a recipe. The content MUST contain:
1. A list of ingredients OR mentions of food items/quantities
2. Cooking instructions OR preparation steps

If the content does not meet these criteria, you MUST respond with EXACTLY this format:
VALIDATION_ERROR
[Add a brief explanation why on the next line]

For example:
VALIDATION_ERROR
This content appears to be a login page.

VALIDATION_ERROR
This content is a blog post without any recipe.

VALIDATION_ERROR
This content is an article about cooking but contains no specific recipe.

Only proceed with the recipe cleanup if the content is validated as a proper recipe.




5. General rules:
   - CRITICAL - TEXT PRESERVATION:
   - Remove only clearly unrelated content (ads, navigation elements, etc.)
   - Keep all measurements and temperatures as they are
   - DO NOT add any new information or change cooking instructions
   - DO NOT change ingredient quantities or units
   - DO NOT translate anything

6. Extract recipe notes and metadata:
     * Extract and keep VERBATIM (word for word) ALL text sections that:
       - Describe the recipe
       - Talk about the author
       - Discuss cultural context
       - Give background information
       - Provide tips or variations
       - Include personal stories
       - Mention serving suggestions
     * Include these sections in a NOTES section
     * Separate each distinct text section with "---"
     * DO NOT modify, summarize, or rewrite ANY of these texts
     * Keep them in their original order of appearance
     * Keep ALL punctuation and formatting exactly as is
   - Look for any introductory text, anecdotes, or additional information about the recipe that appears before the ingredients or instructions.
   - Keep relevant information about:
     * Recipe origin or history
     * Ingredient substitutions
     * Recipe nationality or cuisine type
     * Author of the recipe (if mentioned)
     * Book title or source (if mentioned)


     
     
2. For the INGREDIENTS section:
   - Keep all quantities and units exactly as they are
   - Group similar ingredients together (e.g., all spices together)
   - Vegetables have to be treated as units (e.g., 1 onion, 2 carrots, 3 potatoes)
   - Remove duplicates but combine their quantities
   - If an ingredient appears in instructions but not in the list, add it


3. For the INSTRUCTIONS section:
   - Break down the recipe into clear, numbered steps
   - Each step should focus on one main action
   - Put important values in bold using **value**, such as:
     * Temperatures: "Preheat the oven to **180°C**"
     * Cooking times: Use exact format without spaces:
       - For seconds only: "**XXs**" (e.g., "30s")
       - For minutes only: "**XXmin**" (e.g., "5min")
       - For hours only: "**XXh**" (e.g., "2h")
       - For combinations:
         * Hours and minutes: "**XhYYmin**" (e.g., "1h30min")
         * Minutes and seconds: "**XXminYYs**" (e.g., "5min30s")
         * Hours, minutes and seconds: "**XhYYminZZs**" (e.g., "1h30min15s")
       - ⚠️ CRITICAL: NEVER use time ranges (no "15-20 minutes" or "5-6min")
       - ⚠️ CRITICAL: If source has a time range (e.g. "15-20 minutes"), you MUST ALWAYS use the shortest time (e.g. "15min")
       - ⚠️ CRITICAL: For "until done" or similar vague times, you MUST choose a specific time based on average
       - Examples of INCORRECT time formats to AVOID:
         * "5-6min" ❌ (use "5min" ✅)
         * "15–20 minutes" ❌ (use "15min" ✅)
         * "1-2h" ❌ (use "1h" ✅)
         * "until done" ❌ (use specific time like "30min" ✅)
     * Specific measurements: "Roll out to **1cm** thickness"
     * Heat levels: "Cook over **medium-high** heat"
   - For each sub-recipe (if any):
     * Start with a clear title in bold: "**For the chimichurri:**"
     * MUST include at least one step
     * Number the steps independently
     * Include any specific equipment needed
     * NEVER leave a sub-recipe without steps
   - Use precise cooking verbs:
     * "Sauté" instead of "cook" for quick pan cooking
     * "Caramelize" for slow browning of sugars
     * "Sweat" for cooking vegetables without color
     * "Reduce" for cooking down liquids
   - Include visual or textural cues:
     * "until golden brown"
     * "until tender when pierced with a knife"
     * "until the edges start to bubble"
   - Be explicit about ingredient combinations:
     * Always mention ingredient names when mixing multiple ingredients
     * Example: Instead of "Mix together", write "Mix the onions, garlic, and ginger"
   - Specify pan types and sizes when relevant
   - Include resting times and temperatures if needed
   - End with plating instructions if relevant

1. Structure the content in clear sections:
   a. INGREDIENTS: List all ingredients with their quantities and preparation state
   b. SPECIAL EQUIPMENT: List only special or non-standard kitchen tools needed
   c. INSTRUCTIONS: Clear step-by-step cooking instructions

4. For the SPECIAL EQUIPMENT section:
   - Only list non-standard or specialized tools (e.g., food processor, spice grinder, stand mixer)
   - DO NOT list basic kitchen tools (e.g., knives, cutting boards, bowls, spoons)
   - STRICTLY AVOID TOOL DUPLICATES:
     * Use consistent naming for the same tool (e.g., always use "food processor" instead of mixing "food processor", "blender", "mixer" for the same tool)
     * If a tool appears with different names, choose the most specific one (e.g., "stand mixer" over "mixer")
     * Never list variations of the same tool (e.g., "pan" and "frying pan")
     * If a tool has multiple sizes, only mention the largest one needed (e.g., "large saucepan" not "medium saucepan" and "large saucepan")
   - If a tool is mentioned in the original recipe, keep it
   - Don't add basic tools that weren't in the original recipe






RESPONSE FORMAT:
Return the cleaned content in this format:

TITLE:
[Recipe title]

NOTES:
[Any relevant recipe notes]

METADATA:
NATIONALITY: [Recipe nationality or cuisine type, if available]
AUTHOR: [Recipe author, if mentioned]
BOOK: [Book title or source, if from a cookbook]
QUALITY_SCORE: [Recipe quality score, from 0 to 100]

SELECTED IMAGE URL:
[The most relevant URL or empty string if none are suitable]

SPECIAL EQUIPMENT:
- [Tool 1]
- [Tool 2]
...

INGREDIENTS:
- [Ingredient 1 with quantity]
- [Ingredient 2 with quantity]
...


INSTRUCTIONS:

**For [Sub-recipe 1 Title]:**
1. [Step 1]
2. [Step 2]
...

**For [Sub-recipe 2 Title]:**
1. [Step 1]
2. [Step 2]
...

[IMPORTANT: Each sub-recipe MUST have its own numbered steps. NEVER leave a sub-recipe without steps.]

    """

    return "\n".join([
        prompt,
        "INPUT CONTENT:",
        content,
        "AVAILABLE IMAGE URLS:",
        "\n".join(image_urls) if image_urls else "No images available"
    ])

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
    example_images = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
    ]
    
    # Format and print the prompt
    prompt = format_cleanup_recipe_prompt(example_content, example_images)
    print("\nCLEANUP RECIPE PROMPT:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
