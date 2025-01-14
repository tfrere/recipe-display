/**
 * Formate un ingrédient avec sa quantité et son état
 */
const formatIngredient = (ingredient, ingredientData) => {
  const amount = ingredientData.amount;
  const unit = ingredient.unit;
  const state = ingredientData.state ? `, ${ingredientData.state}` : "";
  return `- ${amount !== undefined ? amount + " " : ""}${unit || ""}${
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
  if (!subRecipe.ingredients || !recipe.ingredientsList) {
    console.log("Missing ingredients:", { subRecipe, recipe });
    return [];
  }

  return Object.entries(subRecipe.ingredients)
    .map(([ingredientId, data]) => {
      const ingredient = recipe.ingredientsList.find(
        (ing) => ing.id === ingredientId
      );
      if (!ingredient) {
        console.log("Missing ingredient:", {
          ingredientId,
          data,
          recipeIngredients: recipe.ingredientsList,
        });
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

  return Object.values(subRecipe.steps)
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

  return Object.entries(recipe.subRecipes).map(([id, subRecipe]) =>
    formatSubRecipe(subRecipe, recipe)
  );
};
