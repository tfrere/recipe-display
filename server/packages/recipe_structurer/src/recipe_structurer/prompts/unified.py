"""
Unified Prompt — Pass 2 of the 2-pass pipeline (DAG construction).

This prompt receives PREFORMATTED structured text from Pass 1 and builds
the complete Recipe JSON graph (DAG). It no longer needs to parse raw
HTML or messy text — that work is done by the preformat pass.

Follows the Three-Block scaffold pattern (ROLE / GOAL / RESPONSE GUIDELINES)
recommended for DeepSeek V3 structured output, with a full few-shot example
demonstrating parallel sub-recipes and cross-sub-recipe state flows.
"""

import json
from typing import Optional

# ---------------------------------------------------------------------------
# Few-shot example: a complex recipe with parallel flows + separation step
# ---------------------------------------------------------------------------

# Preformatted input (what Pass 1 would produce)
FEW_SHOT_PREFORMATTED_INPUT = """TITLE: Poulet à la crème et champignons
DESCRIPTION: Un poulet rôti en cocotte, nappé d'une sauce crème aux champignons.
LANGUAGE: fr
SERVINGS: 4
DIFFICULTY: medium
TYPE: main_course
NATIONALITY: French
AUTHOR:
SOURCE:
IMAGE_URL:

TAGS:
- poulet
- champignons
- crème
- français

NOTES:
- Servir avec du riz basmati ou des pâtes fraîches.

TOOLS:
- cocotte en fonte
- poêle

INGREDIENTS:
- 4 «cuisses de poulet» [4 chicken thighs] {poultry}
- 250g «champignons de Paris» [250g mushrooms, sliced] {produce}, émincés
- 1 «oignon» [1 onion, diced] {produce}, ciselé
- 30g «beurre» [30g butter] {dairy}
- 200ml «crème fraîche épaisse» [200ml heavy cream] {dairy}
- 100ml «vin blanc sec» [100ml dry white wine] {beverage}
- 200ml «bouillon de volaille» [200ml chicken broth] {pantry}
- 1 c-à-s «farine» [1 tablespoon flour] {grain}
- 2 branches «thym frais» [2 sprigs fresh thyme] {spice}
- «sel» [salt] {spice} (à volonté)
- «poivre» [pepper] {spice} (à volonté)

INSTRUCTIONS:

**Poulet:**
1. Assaisonner les cuisses de poulet avec le sel et le poivre. (**2min**)
2. Dans la cocotte, faire fondre la moitié du beurre et saisir les cuisses sur toutes les faces. Réserver. (**8min**, doré sur toutes les faces)

**Sauce:**
1. Dans la même cocotte, faire revenir l'oignon ciselé dans le fond de cuisson. (**3min**, translucide)
2. Déglacer au vin blanc en grattant les sucs. Ajouter le bouillon et le thym, porter à frémissement. (**3min**)

**Poulet (suite):**
1. Remettre les cuisses de poulet dans la cocotte, couvrir et laisser braiser à feu doux à **160°C**. (**30min**, poulet cuit à cœur) [PASSIVE]

**Champignons:**
1. Pendant ce temps, dans une poêle, faire sauter les champignons émincés dans le reste du beurre. Saupoudrer de farine et mélanger. (**5min**, dorés et sans eau)

**Sauce (suite):**
1. Retirer le poulet de la cocotte. Ajouter la crème fraîche et les champignons sautés dans le jus de cuisson. Mélanger et laisser épaissir. (**5min**, sauce nappante)

**Assemblage:**
1. Disposer les cuisses de poulet dans un plat de service et napper de sauce crème aux champignons. (**2min**)"""

FEW_SHOT_EXPECTED_OUTPUT = {
    "metadata": {
        "title": "Poulet à la crème et champignons",
        "description": "Un poulet rôti en cocotte, nappé d'une sauce crème aux champignons.",
        "servings": 4,
        "difficulty": "medium",
        "recipeType": "main_course",
        "tags": ["poulet", "champignons", "crème", "français"],
        "imageUrl": None,
        "nationality": "French",
        "author": None,
        "source": None,
        "notes": ["Servir avec du riz basmati ou des pâtes fraîches."]
    },
    "ingredients": [
        {"id": "chicken_thighs", "name": "cuisses de poulet", "name_en": "chicken thighs", "quantity": 4, "unit": "piece", "category": "poultry", "preparation": None, "notes": None, "optional": False},
        {"id": "mushrooms", "name": "champignons de Paris", "name_en": "mushrooms", "quantity": 250, "unit": "g", "category": "produce", "preparation": "sliced", "notes": None, "optional": False},
        {"id": "onion", "name": "oignon", "name_en": "onion", "quantity": 1, "unit": "piece", "category": "produce", "preparation": "diced", "notes": None, "optional": False},
        {"id": "butter", "name": "beurre", "name_en": "butter", "quantity": 30, "unit": "g", "category": "dairy", "preparation": None, "notes": None, "optional": False},
        {"id": "cream", "name": "crème fraîche épaisse", "name_en": "heavy cream", "quantity": 200, "unit": "ml", "category": "dairy", "preparation": None, "notes": None, "optional": False},
        {"id": "white_wine", "name": "vin blanc sec", "name_en": "dry white wine", "quantity": 100, "unit": "ml", "category": "beverage", "preparation": None, "notes": None, "optional": False},
        {"id": "chicken_broth", "name": "bouillon de volaille", "name_en": "chicken broth", "quantity": 200, "unit": "ml", "category": "pantry", "preparation": None, "notes": None, "optional": False},
        {"id": "flour", "name": "farine", "name_en": "flour", "quantity": 1, "unit": "tbsp", "category": "grain", "preparation": None, "notes": None, "optional": False},
        {"id": "thyme", "name": "thym frais", "name_en": "fresh thyme", "quantity": 2, "unit": "piece", "category": "spice", "preparation": None, "notes": "branches", "optional": False},
        {"id": "salt", "name": "sel", "name_en": "salt", "quantity": None, "unit": None, "category": "spice", "preparation": None, "notes": None, "optional": False},
        {"id": "pepper", "name": "poivre", "name_en": "pepper", "quantity": None, "unit": None, "category": "spice", "preparation": None, "notes": None, "optional": False}
    ],
    "tools": ["cocotte en fonte", "poêle"],
    "steps": [
        {
            "id": "season_chicken",
            "action": "Assaisonner les cuisses de poulet avec le sel et le poivre.",
            "duration": "PT2M",
            "temperature": None,
            "stepType": "prep",
            "isPassive": False,
            "subRecipe": "poulet",
            "uses": ["chicken_thighs", "salt", "pepper"],
            "produces": "seasoned_chicken",
            "requires": [],
            "visualCue": None
        },
        {
            "id": "sear_chicken",
            "action": "Dans la cocotte, faire fondre la moitié du beurre et saisir les cuisses de poulet sur toutes les faces. Réserver.",
            "duration": "PT8M",
            "temperature": None,
            "stepType": "cook",
            "isPassive": False,
            "subRecipe": "poulet",
            "uses": ["seasoned_chicken", "butter"],
            "produces": "seared_chicken",
            "requires": [],
            "visualCue": "doré sur toutes les faces"
        },
        {
            "id": "saute_onion",
            "action": "Dans la même cocotte, faire revenir l'oignon ciselé dans le fond de cuisson.",
            "duration": "PT3M",
            "temperature": None,
            "stepType": "cook",
            "isPassive": False,
            "subRecipe": "sauce",
            "uses": ["onion"],
            "produces": "sauteed_onion",
            "requires": [],
            "visualCue": "translucide"
        },
        {
            "id": "deglaze",
            "action": "Déglacer au vin blanc en grattant les sucs. Ajouter le bouillon et le thym, porter à frémissement.",
            "duration": "PT3M",
            "temperature": None,
            "stepType": "cook",
            "isPassive": False,
            "subRecipe": "sauce",
            "uses": ["sauteed_onion", "white_wine", "chicken_broth", "thyme"],
            "produces": "sauce_base",
            "requires": [],
            "visualCue": "frémissant"
        },
        {
            "id": "braise_chicken",
            "action": "Remettre les cuisses de poulet dans la cocotte, couvrir et laisser braiser à feu doux.",
            "duration": "PT30M",
            "temperature": 160,
            "stepType": "cook",
            "isPassive": True,
            "subRecipe": "poulet",
            "uses": ["seared_chicken", "sauce_base"],
            "produces": "braised_chicken",
            "requires": [],
            "visualCue": "poulet cuit à cœur"
        },
        {
            "id": "saute_mushrooms",
            "action": "Pendant ce temps, dans une poêle, faire sauter les champignons émincés dans le reste du beurre. Saupoudrer de farine et mélanger.",
            "duration": "PT5M",
            "temperature": None,
            "stepType": "cook",
            "isPassive": False,
            "subRecipe": "champignons",
            "uses": ["mushrooms", "butter", "flour"],
            "produces": "sauteed_mushrooms",
            "requires": [],
            "visualCue": "dorés et sans eau"
        },
        {
            "id": "make_cream_sauce",
            "action": "Retirer le poulet de la cocotte. Ajouter la crème fraîche et les champignons sautés dans le jus de cuisson. Mélanger et laisser épaissir.",
            "duration": "PT5M",
            "temperature": None,
            "stepType": "cook",
            "isPassive": False,
            "subRecipe": "sauce",
            "uses": ["braised_chicken", "cream", "sauteed_mushrooms"],
            "produces": "cream_mushroom_sauce",
            "requires": [],
            "visualCue": "sauce nappante"
        },
        {
            "id": "plate",
            "action": "Disposer les cuisses de poulet dans un plat de service et napper de sauce crème aux champignons.",
            "duration": "PT2M",
            "temperature": None,
            "stepType": "serve",
            "isPassive": False,
            "subRecipe": "assemblage",
            "uses": ["braised_chicken", "cream_mushroom_sauce"],
            "produces": "poulet_creme_champignons",
            "requires": [],
            "visualCue": None
        }
    ],
    "finalState": "poulet_creme_champignons"
}

FEW_SHOT_JSON = json.dumps(FEW_SHOT_EXPECTED_OUTPUT, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# System prompt – Three-Block scaffold (Pass 2: DAG construction)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""#ROLE
You are an expert culinary AI that transforms preformatted recipe text into a structured JSON graph.
You understand cooking techniques, ingredient relationships, and recipe flow deeply.

#GOAL
You receive a PREFORMATTED recipe (already cleaned and structured as plain text).
Your ONLY job is to convert it into a COMPLETE directed acyclic graph (DAG) where:
- Every ingredient flows through steps to produce the final dish
- Parallel preparations (sauce, garnish, dough…) are modeled as separate sub-recipes
- The graph is fully connected: no orphan nodes, no dead-end states

The input is already clean — you do NOT need to parse HTML, remove ads, or fix formatting.
Focus entirely on building a correct graph.

#RESPONSE GUIDELINES

## 1. Language — CRITICAL
- `metadata.title`: keep the ORIGINAL language from the input
- `metadata.description`: use the description from the input (same language)
- `step.action`: write in the SAME language as the input recipe
- `ingredient.name`: keep the ORIGINAL language from the input
- NEVER translate recipe content to English unless the source is already in English

## 2. INGREDIENTS — ALREADY PARSED (CRITICAL)
- The ingredients have ALREADY been parsed by a NER model and are provided as JSON in the user message.
- You MUST use these ingredients EXACTLY as provided (same IDs, same names, same quantities).
- DO NOT invent, rename, or modify ingredient IDs. Use the `id` field from the provided ingredients JSON in your `uses` arrays.
- DO NOT add, remove, or modify any ingredient — the ingredients list in your response should be IDENTICAL to the provided JSON.

## 3. Graph connectivity — CRITICAL
- `uses` MUST NEVER be empty except for a step that only sets up equipment (e.g., "preheat oven").
- Every step transforms something. If a step works on the result of a previous step (e.g., "cut the cooked carrots"), it MUST reference the state that contains those items in `uses`.
- When a step separates components (e.g., strain broth from solids), it produces ONE state. ALL subsequent steps that work on ANY part of that separation MUST reference that state in `uses`.
- Every ingredient MUST appear in `uses` of at least one step. No unused ingredients.
- Every state produced by a step MUST be referenced in `uses` or `requires` by a later step, OR be the `finalState`.

## 3. Sub-recipes
- Use `subRecipe` to group related steps: "main", "sauce", "garniture", "pâte", etc.
- The input may already indicate sub-recipes with **bold headers** — use those names.
- Steps from different sub-recipes CAN reference each other's states — this is how the graph connects parallel flows.
- The final assembly step typically brings together states from multiple sub-recipes.

## 4. IDs
- Ingredient IDs: snake_case of the ingredient name → "all_purpose_flour", "unsalted_butter"
- State IDs: describe what was created → "dry_mix", "seared_chicken", "cream_sauce"
- Step IDs: semantic action name → "sear_chicken", "make_roux", "deglaze"

## 5. Ingredient categorization
Assign each ingredient a category from: meat, poultry, seafood, produce, dairy, egg, pantry, spice, condiment, beverage, other.

## 6. Ingredient preparation state
- The `preparation` field describes HOW the ingredient should be prepared BEFORE cooking starts.
- Look for preparation hints in the input ingredient list (e.g., "émincés", "ciselé", "diced").
- If no specific preparation is mentioned, leave `preparation` as null.

## 7. Data formatting
- ISO 8601 durations for STEP durations: "5min" → "PT5M", "1h30min" → "PT1H30M", "2h" → "PT2H"
- Temperature: always Celsius (integer)
- Quantities: numeric float or null for "to taste" / "à volonté"
- Unit: null when quantity is null
- Canned/packaged ingredients: if the input provides a weight (e.g., "800ml coconut milk"), use that weight as quantity+unit (quantity=800, unit="ml"), NOT "2 cans"
- Use the metadata from the input (SERVINGS, DIFFICULTY, TYPE, etc.) directly
- DO NOT generate `prepTime`, `cookTime`, `totalTime` in metadata — these are computed automatically from the step DAG after generation. Only generate `duration` on individual steps.

## 8. isPassive
- Steps marked with [PASSIVE] in the input should have `isPassive: true`
- Passive steps are those where the food cooks unattended (simmering, resting, baking)

## 9. Optional ingredients (toppings, garnishes, serving suggestions)
- Ingredients marked "(optionnel)" in the input MUST have `optional: true` in the output
- Optional ingredients do NOT need to be referenced in any step's `uses` — they are exempt from the graph connectivity rule
- However, if there is a garnish/topping/serving step in the instructions, optional ingredients SHOULD be included in that step's `uses`
- If no such step exists, create a final step of type "serve" with subRecipe "garniture" that references the optional ingredients
- This step should describe the topping/garnish options as written in the source

## COMPLETE EXAMPLE

Below is an example showing preformatted input and the expected JSON output.

**Input (preformatted text):**
```
{FEW_SHOT_PREFORMATTED_INPUT}
```

**Expected output:**
```json
{FEW_SHOT_JSON}
```

Key observations:
- `uses` is NEVER empty (every step transforms something)
- Sub-recipes "poulet", "sauce", "champignons" produce states used across each other
- `braised_chicken` is referenced by both `make_cream_sauce` and `plate`
- "sel" and "poivre" have `quantity: null` and `unit: null` (to-taste ingredients)
- All text is in French because the input recipe is in French
- The metadata values (servings, difficulty, type, etc.) come directly from the input
"""


def get_user_prompt(preformatted_text: str, ingredients_json: Optional[str] = None) -> str:
    """Generate the user prompt for DAG construction from preformatted text."""

    ingredients_section = ""
    if ingredients_json:
        ingredients_section = f"""

## Pre-parsed Ingredients (from NER — use these EXACTLY)

The following ingredients have been pre-parsed by a specialized NER model.
You MUST use them as-is in your output. Reference their `id` fields in your steps' `uses` arrays.
DO NOT modify ingredient IDs, names, quantities, or units.

```json
{ingredients_json}
```

"""

    return f"""Convert the following preformatted recipe into the JSON graph format defined in your instructions.

## Preformatted Recipe

{preformatted_text}
{ingredients_section}
---

## Checklist before generating

1. Language: keep ALL text in the same language as the input above.

2. Ingredients: use the pre-parsed ingredients JSON EXACTLY as provided.
   - Reference ingredient `id` fields in your steps' `uses` arrays.
   - DO NOT rename, add, or remove ingredients.

3. Graph completeness:
   - Every NON-optional ingredient appears in at least one step's `uses`
   - Optional ingredients (`optional: true`) are exempt from this rule but SHOULD be in a garnish/serve step if one exists
   - Every step has a non-empty `uses` (except equipment-only steps like "preheat oven")
   - Every produced state is consumed by a later step or is the `finalState`
   - The graph is fully connected from ingredients → finalState

4. Quantities: already handled by NER — do not override.

5. Use metadata from the input: SERVINGS, DIFFICULTY, TYPE, NATIONALITY, etc.

6. Optional ingredients: mark with `optional: true`. Include a garnish/serve step if toppings are present.

Now generate the complete structured recipe JSON."""


# Keep backward compatibility — the old single-pass function signature
def get_user_prompt_raw(recipe_text: str, image_urls: list[str] | None = None) -> str:
    """Generate user prompt from raw text (backward compat, used if pipeline falls back)."""

    image_section = ""
    if image_urls:
        image_section = f"""
## Available Images
The following image URLs are available for this recipe. Select the most appropriate one for `imageUrl`:
{chr(10).join(f'- {url}' for url in image_urls)}
"""

    return f"""Structure the following recipe into the JSON format defined in your instructions.

{image_section}

## Recipe Content

{recipe_text}

---

## Checklist before generating

1. If this is NOT a valid recipe (login page, error, empty content, recipe compilation/roundup listing multiple independent recipes), respond with:
   {{"error": "NOT_A_RECIPE", "reason": "explanation"}}

2. Language: write description, actions, and ingredient names in the SAME language as the recipe above.

3. Graph completeness:
   - Every ingredient appears in at least one step's `uses`
   - Every step has a non-empty `uses` (except equipment-only steps like "preheat oven")
   - Every produced state is consumed by a later step or is the `finalState`
   - The graph is fully connected from ingredients → finalState

4. Quantities: use null (not 0) for "to taste" / "à volonté" ingredients.

Now generate the complete structured recipe JSON."""
