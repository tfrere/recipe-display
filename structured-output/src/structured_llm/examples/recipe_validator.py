from typing import List, Set, Tuple
from pydantic import ValidationError
from .recipe import LLMRecipe, Step

class RecipeValidator:
    def validate_recipe(self, recipe_json: dict) -> Tuple[bool, List[str]]:
        """
        Validate recipe in two steps:
        1. Schema validation (Pydantic)
        2. Business rules validation
        """
        # Step 1: Schema validation
        try:
            recipe = LLMRecipe.parse_obj(recipe_json)
        except ValidationError as e:
            return False, [f"Schema validation error: {err['msg']}" for err in e.errors()]
        
        # Step 2: Business rules validation
        business_errors = []
        
        # 2.1 Essential fields
        business_errors.extend(self.validate_essential_fields(recipe))
        
        # 2.2 Ingredients usage
        business_errors.extend(self.validate_ingredients_usage(recipe))
        
        # 2.3 Step references and states
        business_errors.extend(self.validate_step_references(recipe))
        
        # 2.4 Final state
        business_errors.extend(self.validate_final_state(recipe))
        
        return len(business_errors) == 0, business_errors
    
    def validate_essential_fields(self, recipe: LLMRecipe) -> List[str]:
        """Validate essential fields are present and valid"""
        errors = []
        
        if not recipe.metadata.title:
            errors.append("Recipe must have a title")
        if not recipe.metadata.description:
            errors.append("Recipe must have a description")
        if recipe.metadata.servings <= 0:
            errors.append("Recipe must have positive servings")
        if not recipe.ingredients:
            errors.append("Recipe must have ingredients")
        if not recipe.steps:
            errors.append("Recipe must have steps")
            
        return errors
    
    def validate_ingredients_usage(self, recipe: LLMRecipe) -> List[str]:
        """Validate all ingredients are used and references are valid"""
        errors = []
        
        # Track used ingredients
        used_ingredient_ids = set()
        for step in recipe.steps:
            for input in step.inputs:
                if input.input_type == "ingredient":
                    used_ingredient_ids.add(input.ref_id)
        
        # Check for unused ingredients
        all_ingredient_ids = {ing.id for ing in recipe.ingredients}
        unused_ingredients = all_ingredient_ids - used_ingredient_ids
        if unused_ingredients:
            errors.append(f"Found unused ingredients: {unused_ingredients}")
            
        return errors
    
    def validate_step_references(self, recipe: LLMRecipe) -> List[str]:
        """Validate step references (ingredients and states)"""
        errors = []
        
        all_ingredient_ids = {ing.id for ing in recipe.ingredients}
        
        for i, step in enumerate(recipe.steps):
            # Validate each input
            for input in step.inputs:
                if input.input_type == "ingredient":
                    if input.ref_id not in all_ingredient_ids:
                        errors.append(f"Step {i+1}: Referenced ingredient {input.ref_id} does not exist")
                elif input.input_type == "state":
                    # Check that referenced state is output of a previous step
                    state_exists = any(
                        s.output_state.id == input.ref_id 
                        for s in recipe.steps[:i]
                    )
                    if not state_exists:
                        errors.append(f"Step {i+1}: Referenced state {input.ref_id} does not exist in previous steps")
            
            # Validate output state
            if not step.output_state.description:
                errors.append(f"Step {i+1}: Output state must have a description")
                
        return errors
    
    def validate_final_state(self, recipe: LLMRecipe) -> List[str]:
        """Validate final state matches last step and is complete"""
        errors = []
        
        if not recipe.steps:
            return errors  # Already handled in validate_essential_fields
            
        last_step = recipe.steps[-1]
        if last_step.output_state.id != recipe.final_state.id:
            errors.append("Final state must be the output of the last step")
        if recipe.final_state.type != "final":
            errors.append("Final state must have type 'final'")
        if not recipe.final_state.description:
            errors.append("Final state must have a detailed description")
            
        return errors

    def build_retry_prompt(
        self,
        content: str,
        attempt: int,
        previous_response: str = "",
        validation_errors: List[str] = []
    ) -> str:
        """Build retry prompt with validation feedback"""
        if attempt == 1:
            return content
        
        return f"""⚠️ Previous attempt failed with these validation errors:
{validation_errors}

Previous response:
{previous_response}

🔍 CRITICAL REQUIREMENTS:

1. MINIMAL STRUCTURE (Required by schema):
{{
  "metadata": {{...}},
  "ingredients": [...],
  "steps": [...],
  "final_state": {{  // MUST be present and match last step
    "id": "...",
    "type": "final",
    "description": "..."
  }}
}}

2. INGREDIENT INPUTS - When using ingredients:
   * input_type: "ingredient"
   * ref_id: ID from ingredients list (e.g., "ing1")
   * name: Name of the ingredient
   * amount: Quantity (number)
   * unit: One of ["g", "cl", "unit", "tbsp", "tsp", "pinch"]

3. STATE INPUTS - When using states:
   * input_type: "state"
   * ref_id: ID from a previous step's output_state
   * name: Name of the state

4. EVERY step MUST have:
   * Unique ID
   * Clear action
   * Duration
   * Output state with description

5. ALL ingredients MUST be used in steps

Please fix ALL validation errors while keeping the same structure and content where possible.

Here is the original content again:
{content}"""

    def validate_step_inputs(self, step: Step, recipe: LLMRecipe) -> List[str]:
        """Validate the inputs of a step."""
        errors = []
        
        # Skip validation if no inputs (valid case)
        if not step.inputs:
            return errors
            
        # Validate each input
        for input in step.inputs:
            if input.input_type == "ingredient":
                if input.ref_id not in {ing.id for ing in recipe.ingredients}:
                    errors.append(f"Step {step.index}: Referenced ingredient {input.ref_id} does not exist")
            elif input.input_type == "state":
                # Check that referenced state is output of a previous step
                state_exists = any(
                    s.output_state.id == input.ref_id 
                    for s in recipe.steps[:step.index]
                )
                if not state_exists:
                    errors.append(f"Step {step.index}: Referenced state {input.ref_id} does not exist in previous steps")
        
        return errors 