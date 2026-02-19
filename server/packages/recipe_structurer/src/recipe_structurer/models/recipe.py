"""
Recipe Models - Simplified format leveraging modern LLM capabilities.

This format uses a graph-implicit approach where:
- `uses` references ingredients or states consumed by a step
- `produces` creates a new state that can be referenced by later steps
- `requires` specifies parallel dependencies (e.g., oven must be preheated)

The frontend can reconstruct the DAG automatically from these relationships.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class Metadata(BaseModel):
    """Recipe metadata - essential information about the recipe."""

    title: str = Field(
        description="Original recipe name (keep original language, no parentheses)"
    )
    description: str = Field(
        description="Brief 1-2 sentence description of the dish, in the SAME language as the recipe"
    )
    servings: int = Field(
        ge=1,
        description="Number of portions this recipe yields"
    )
    prepTime: Optional[str] = Field(
        default=None,
        description="DEPRECATED — kept for backward compat. Times are now computed from the step DAG at enrichment."
    )
    cookTime: Optional[str] = Field(
        default=None,
        description="DEPRECATED — kept for backward compat. Times are now computed from the step DAG at enrichment."
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        description="Recipe difficulty level"
    )
    recipeType: Literal["appetizer", "starter", "main_course", "dessert", "drink", "base"] = Field(
        description="Recipe classification"
    )
    totalTime: Optional[str] = Field(
        default=None,
        description="Total wall-clock time (critical path through step DAG) in ISO 8601 (e.g. 'PT1H30M'). Computed at enrichment, not by LLM."
    )
    totalActiveTime: Optional[str] = Field(
        default=None,
        description="Active (non-passive) time on critical path in ISO 8601. Computed at enrichment."
    )
    totalPassiveTime: Optional[str] = Field(
        default=None,
        description="Passive (unattended) time on critical path in ISO 8601. Computed at enrichment."
    )
    tags: List[str] = Field(
        default=[],
        description="Relevant tags (cuisine type, diet, main ingredient, etc.)"
    )
    imageUrl: Optional[str] = Field(
        default=None,
        description="URL of the recipe's main image"
    )
    nationality: Optional[str] = Field(
        default=None,
        description="Country or cuisine of origin"
    )
    author: Optional[str] = Field(
        default=None,
        description="Recipe author if known"
    )
    source: Optional[str] = Field(
        default=None,
        description="Book, website, or publication source"
    )
    notes: List[str] = Field(
        default=[],
        description="Additional tips, variations, or serving suggestions"
    )


class Ingredient(BaseModel):
    """A single ingredient with quantity and preparation state."""

    id: str = Field(
        description="Unique identifier (snake_case, e.g., 'all_purpose_flour')"
    )
    name: str = Field(
        description="Ingredient name in the SAME language as the recipe"
    )
    name_en: Optional[str] = Field(
        default=None,
        description="Ingredient name in English (for standardization, nutrition lookup, etc.)"
    )
    quantity: Optional[float] = Field(
        default=None,
        description="Numeric quantity (null for 'to taste' items)"
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement (g, ml, tbsp, tsp, cup, piece, etc.). null when quantity is null."
    )
    category: Literal[
        "meat", "poultry", "seafood", "produce", "dairy", "egg",
        "grain", "legume", "nuts_seeds", "oil", "herb",
        "pantry", "spice", "condiment", "beverage", "other"
    ] = Field(
        description="Ingredient category for grouping (supermarket-aisle based)"
    )
    preparation: Optional[str] = Field(
        default=None,
        description="Initial preparation state (e.g., 'diced', 'minced', 'room temperature')"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes (e.g., 'or substitute with...')"
    )
    optional: bool = Field(
        default=False,
        description="Whether this ingredient is optional"
    )


class Step(BaseModel):
    """A single preparation step with graph relationships."""

    id: str = Field(
        description="Unique semantic identifier (e.g., 'sear_chicken', 'make_roux')"
    )
    action: str = Field(
        description="Clear instruction in the SAME language as the recipe. Include ingredient names."
    )
    duration: Optional[str] = Field(
        default=None,
        description="Duration in ISO 8601 format (e.g., 'PT5M' for 5 minutes)"
    )
    temperature: Optional[int] = Field(
        default=None,
        description="Temperature in Celsius if applicable"
    )
    stepType: Literal["prep", "combine", "cook", "rest", "serve"] = Field(
        description="Type of action: prep (cutting, measuring), combine (mixing), cook (heat), rest (waiting), serve (plating)"
    )
    isPassive: bool = Field(
        default=False,
        description="True if step can be left unattended (e.g., simmering, resting)"
    )
    subRecipe: str = Field(
        default="main",
        description="Name of sub-recipe this step belongs to (e.g., 'main', 'sauce', 'dough')"
    )

    # Graph relationships
    uses: List[str] = Field(
        default=[],
        description="List of ingredient IDs or state IDs consumed/transformed by this step. MUST NOT be empty unless the step only sets up equipment."
    )
    produces: str = Field(
        description="State ID created by this step (e.g., 'dry_mix', 'caramelized_onions')"
    )
    requires: List[str] = Field(
        default=[],
        description="State IDs that must exist but aren't consumed (e.g., preheated oven)"
    )

    # Visual cues
    visualCue: Optional[str] = Field(
        default=None,
        description="Visual indicator of completion (e.g., 'golden brown', 'bubbling')"
    )


# Keywords for equipment-only steps (allowed to have empty `uses`)
_EQUIPMENT_KEYWORDS = {"preheat", "préchauffer", "allumer", "préparer le four"}


class Recipe(BaseModel):
    """
    Complete recipe.

    This simplified format allows the LLM to focus on semantic understanding
    while providing all information needed to reconstruct the preparation graph.
    """

    metadata: Metadata = Field(
        description="Recipe identification and classification"
    )
    ingredients: List[Ingredient] = Field(
        description="All ingredients needed for the recipe"
    )
    tools: List[str] = Field(
        default=[],
        description="Special equipment required (exclude basic items like bowls, knives)"
    )
    steps: List[Step] = Field(
        description="Ordered sequence of preparation steps"
    )
    finalState: str = Field(
        description="The state ID representing the completed dish"
    )

    # Not generated by LLM - added post-processing
    originalText: Optional[str] = Field(
        default=None,
        description="Original raw text of the recipe (added post-generation, not by LLM)"
    )
    preformattedText: Optional[str] = Field(
        default=None,
        description="Preformatted text from Pass 1 (added post-generation, not by LLM)"
    )

    @model_validator(mode='after')
    def validate_graph(self) -> 'Recipe':
        """Validate the recipe graph is complete and connected."""
        ingredient_ids = {ing.id for ing in self.ingredients}
        produced_states: dict[str, int] = {}  # state → step index
        errors: list[str] = []

        for i, step in enumerate(self.steps):
            # --- Rule 1: `uses` must not be empty (unless equipment step) ---
            if not step.uses:
                is_equipment = any(
                    kw in step.action.lower()
                    for kw in _EQUIPMENT_KEYWORDS
                )
                if not is_equipment:
                    errors.append(
                        f"Step '{step.id}' has empty `uses` but is not an equipment step. "
                        f"Every step must reference the ingredients or states it transforms."
                    )

            # --- Rule 2: every ref in `uses` must be a known ingredient or state ---
            for ref in step.uses:
                if ref not in ingredient_ids and ref not in produced_states:
                    errors.append(
                        f"Step '{step.id}' uses '{ref}' which is neither an ingredient ID "
                        f"nor a state produced by a previous step."
                    )

            # --- Rule 3: every ref in `requires` must be a known state ---
            for ref in step.requires:
                if ref not in produced_states:
                    errors.append(
                        f"Step '{step.id}' requires '{ref}' which has not been produced yet."
                    )

            # Register the produced state
            if step.produces in produced_states:
                errors.append(
                    f"Duplicate state: '{step.produces}' is produced by both "
                    f"step '{self.steps[produced_states[step.produces]].id}' and '{step.id}'."
                )
            produced_states[step.produces] = i

        # --- Rule 4: finalState must be produced by some step ---
        if self.finalState not in produced_states:
            errors.append(
                f"finalState '{self.finalState}' is not produced by any step."
            )

        # --- Rule 5: every non-optional ingredient must be used at least once ---
        optional_ingredient_ids = {ing.id for ing in self.ingredients if ing.optional}
        required_ingredient_ids = ingredient_ids - optional_ingredient_ids
        used_ingredients = set()
        for step in self.steps:
            for ref in step.uses:
                if ref in ingredient_ids:
                    used_ingredients.add(ref)
        unused_required = required_ingredient_ids - used_ingredients
        if unused_required:
            errors.append(
                f"Unused ingredients (not referenced in any step's `uses`): {sorted(unused_required)}"
            )

        # --- Rule 6: every produced state must be consumed or be finalState ---
        consumed_states = set()
        for step in self.steps:
            for ref in step.uses + step.requires:
                if ref in produced_states:
                    consumed_states.add(ref)
        orphan_states = set(produced_states.keys()) - consumed_states - {self.finalState}
        if orphan_states:
            errors.append(
                f"Orphan states (produced but never consumed and not finalState): {sorted(orphan_states)}"
            )

        if errors:
            raise ValueError(
                "Graph validation failed. Fix these issues:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )

        return self
