/**
 * Formate un ingrédient avec sa quantité et son état
 */
const formatIngredient = (ingredient, data) => {
  const amount = data.amount;
  const unit = ingredient.unit;
  const state = data.state ? `, ${data.state}` : "";
  return `- ${amount != null ? amount + " " : ""}${unit || ""}${
    unit ? " " : ""
  }${ingredient.name}${state}`;
};

/**
 * Formate une étape avec son numéro et son temps
 */
const formatStep = (step, index) => {
  return `${index + 1}. ${step.action}${
    step.time && step.time !== "N/A" ? ` (${step.time})` : ""
  }`;
};

/**
 * Formate les ingrédients d'une sous-recette
 */
export const formatSubRecipeIngredients = (subRecipe, recipe) => {
  if (!subRecipe.ingredients || !recipe.ingredients) {
    return [];
  }

  // Build ingredients map for quick lookup
  const ingredientsMap = {};
  recipe.ingredients.forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  return (subRecipe.ingredients || [])
    .map((data) => {
      const ingredient = ingredientsMap[data.ref];
      if (!ingredient) {
        return null;
      }
      return formatIngredient(ingredient, data);
    })
    .filter(Boolean);
};

/**
 * Formate les étapes d'une sous-recette
 */
export const formatSubRecipeSteps = (subRecipe) => {
  if (!subRecipe.steps) return [];

  return subRecipe.steps
    .map((step, index) => formatStep(step, index))
    .filter(Boolean);
};

/**
 * Formate une sous-recette complète
 */
export const formatSubRecipe = (subRecipe, recipe) => {
  const ingredients = formatSubRecipeIngredients(subRecipe, recipe);
  const steps = formatSubRecipeSteps(subRecipe);

  return {
    title: subRecipe.title,
    ingredients,
    steps,
  };
};

/**
 * Obtient toutes les sous-recettes formatées
 */
export const getFormattedSubRecipes = (recipe) => {
  if (!recipe?.subRecipes) return [];

  return recipe.subRecipes.map((subRecipe) =>
    formatSubRecipe(subRecipe, recipe)
  );
};
