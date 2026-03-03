/**
 * Formate un ingrédient avec sa quantité et son état.
 * @param {object} ingredient - ingredient from recipe.ingredients
 * @param {object} data - ingredient reference from subRecipe.ingredients
 * @param {function} [amountFormatter] - optional (amount, unit, ingredient) => string
 */
const formatIngredient = (ingredient, data, amountFormatter) => {
  const amount = data.amount;
  const unit = data.unit || ingredient.unit;
  const state = data.state ? `, ${data.state}` : "";

  if (amountFormatter && amount != null) {
    const formatted = amountFormatter(amount, unit, ingredient);
    return `- ${formatted} ${ingredient.name}${state}`;
  }

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
export const formatSubRecipeIngredients = (subRecipe, recipe, amountFormatter) => {
  if (!subRecipe.ingredients || !recipe.ingredients) {
    return [];
  }

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
      return formatIngredient(ingredient, data, amountFormatter);
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
export const formatSubRecipe = (subRecipe, recipe, amountFormatter) => {
  const ingredients = formatSubRecipeIngredients(subRecipe, recipe, amountFormatter);
  const steps = formatSubRecipeSteps(subRecipe);

  return {
    title: subRecipe.title,
    ingredients,
    steps,
  };
};

/**
 * Obtient toutes les sous-recettes formatées
 * @param {object} recipe
 * @param {function} [amountFormatter] - optional (amount, unit, ingredient) => string
 */
export const getFormattedSubRecipes = (recipe, amountFormatter) => {
  if (!recipe?.subRecipes) return [];

  return recipe.subRecipes.map((subRecipe) =>
    formatSubRecipe(subRecipe, recipe, amountFormatter)
  );
};
