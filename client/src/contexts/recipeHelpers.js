import { parseTimeToMinutes } from "../utils/timeUtils";

export const calculateUnusedItems = (recipe, completedSteps) => {
  const unusedIngredients = {
    bySubRecipe: {},
  };
  const unusedTools = {};
  const unusedStates = new Set();

  recipe.subRecipes.forEach((subRecipe) => {
    unusedIngredients.bySubRecipe[subRecipe.id] = {};

    const graph = new Map();
    const reverseGraph = new Map();

    (subRecipe.steps || []).forEach((step) => {
      graph.set(step.id, new Set());
      reverseGraph.set(step.id, new Set());

      (step.inputs || []).forEach((input) => {
        const inputId =
          input.type === "ingredient"
            ? `${input.type}-${input.ref}`
            : input.ref;

        if (!graph.has(inputId)) {
          graph.set(inputId, new Set());
          reverseGraph.set(inputId, new Set());
        }
        graph.get(inputId).add(step.id);
        reverseGraph.get(step.id).add(inputId);
      });

      if (step.tools) {
        step.tools.forEach((toolId) => {
          const isProducedState = (subRecipe.steps || []).some(
            (s) => s.output && s.output.state === toolId
          );
          if (isProducedState) {
            if (!graph.has(toolId)) {
              graph.set(toolId, new Set());
              reverseGraph.set(toolId, new Set());
            }
            graph.get(toolId).add(step.id);
            reverseGraph.get(step.id).add(toolId);
          } else {
            const toolNodeId = `tool-${toolId}`;
            if (!graph.has(toolNodeId)) {
              graph.set(toolNodeId, new Set());
              reverseGraph.set(toolNodeId, new Set());
            }
            graph.get(toolNodeId).add(step.id);
            reverseGraph.get(step.id).add(toolNodeId);
          }
        });
      }

      if (step.output) {
        const outputId = step.output.state;
        if (!graph.has(outputId)) {
          graph.set(outputId, new Set());
          reverseGraph.set(outputId, new Set());
        }
        graph.get(step.id).add(outputId);
        reverseGraph.get(outputId).add(step.id);
      }
    });

    (subRecipe.steps || []).forEach((step) => {
      if (completedSteps[step.id]) {
        const visited = new Set();
        const stack = [step.id];

        while (stack.length > 0) {
          const currentId = stack.pop();
          if (visited.has(currentId)) continue;
          visited.add(currentId);

          const predecessors = reverseGraph.get(currentId) || new Set();
          for (const predId of predecessors) {
            if (!visited.has(predId)) {
              stack.push(predId);
            }
          }

          const isUsedLater = Array.from(
            graph.get(currentId) || new Set()
          ).some((successorId) => {
            if (subRecipe.steps?.some((s) => s.id === successorId)) {
              return !completedSteps[successorId];
            }
            return true;
          });

          if (!isUsedLater) {
            if (currentId.startsWith("ingredient-")) {
              const ingredientId = currentId.replace("ingredient-", "");
              const ingredient = recipe.ingredients?.find(
                (ing) => ing.id === ingredientId
              );
              if (ingredient) {
                unusedIngredients.bySubRecipe[subRecipe.id][ingredientId] = true;
              }
            } else if (currentId.startsWith("tool-")) {
              unusedTools[currentId.replace("tool-", "")] = true;
            } else {
              const isState = (subRecipe.steps || []).some(
                (s) =>
                  (s.output && s.output.state === currentId) ||
                  s.produces === currentId
              );
              if (isState) {
                unusedStates.add(currentId);
              }
            }
          }
        }
      }
    });
  });

  return { unusedIngredients, unusedTools, unusedStates };
};

export const extractToolsFromSteps = (recipe) => {
  const toolsSet = new Set();

  if (recipe.tools && Array.isArray(recipe.tools)) {
    recipe.tools.forEach((tool) => toolsSet.add(tool));
  }

  (recipe.subRecipes || []).forEach((subRecipe) => {
    (subRecipe.steps || []).forEach((step) => {
      (step.requires || []).forEach((tool) => toolsSet.add(tool));
      (step.tools || []).forEach((tool) => toolsSet.add(tool));
    });
  });

  return Array.from(toolsSet).map((toolName) => ({
    id: toolName.toLowerCase().replace(/\s+/g, "-"),
    name: toolName,
  }));
};

export const transformToSubRecipes = (recipe) => {
  const ingredientsMap = {};
  (recipe.ingredients || []).forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  const producedStates = new Set();
  (recipe.steps || []).forEach((step) => {
    if (step.produces) {
      producedStates.add(step.produces);
    }
  });

  const transformStep = (step) => {
    const inputs = (step.uses || []).map((ref) => {
      if (ingredientsMap[ref]) {
        const ing = ingredientsMap[ref];
        return {
          inputType: "component",
          ref: ref,
          type: "ingredient",
          amount: ing.quantity,
          unit: ing.unit,
          category: ing.category,
        };
      } else {
        return {
          inputType: "state",
          ref: ref,
          type: "state",
          name: ref.replace(/_/g, " "),
        };
      }
    });

    const output = step.produces
      ? {
          inputType: "state",
          ref: step.produces,
          type: "state",
          state: step.produces,
          name: step.produces.replace(/_/g, " "),
        }
      : null;

    return {
      id: step.id,
      action: step.action,
      time: step.duration || step.time,
      stepType: step.stepType,
      stepMode: step.isPassive ? "passive" : "active",
      isPassive: step.isPassive || false,
      inputs,
      output,
      uses: step.uses,
      produces: step.produces,
      requires: step.requires,
      tools: step.requires || [],
    };
  };

  const stepsByGroup = {};
  const groupOrder = [];
  (recipe.steps || []).forEach((step) => {
    const group = step.subRecipe || "main";
    if (!stepsByGroup[group]) {
      stepsByGroup[group] = [];
      groupOrder.push(group);
    }
    stepsByGroup[group].push(step);
  });

  const subRecipes = groupOrder.map((groupName) => {
    const groupSteps = stepsByGroup[groupName];
    const transformedSteps = groupSteps.map(transformStep);

    const groupIngredientsByRef = {};
    groupSteps.forEach((step) => {
      (step.uses || []).forEach((ref) => {
        if (ingredientsMap[ref] && !groupIngredientsByRef[ref]) {
          const ing = ingredientsMap[ref];
          groupIngredientsByRef[ref] = {
            inputType: "component",
            ref: ref,
            type: "ingredient",
            amount: ing.quantity,
            unit: ing.unit,
            category: ing.category,
            name: ing.name,
            initialState: ing.preparation || null,
          };
        }
      });
    });

    const title =
      groupName === "main"
        ? recipe.metadata?.title || "Recipe"
        : groupName.charAt(0).toUpperCase() + groupName.slice(1);

    return {
      id: groupName,
      title,
      ingredients: Object.values(groupIngredientsByRef),
      steps: transformedSteps,
    };
  });

  return {
    ...recipe,
    subRecipes,
  };
};

export const transformStepsToSubRecipes = (recipe) => {
  if (recipe.subRecipes) return recipe;

  if (!recipe.steps || !Array.isArray(recipe.steps)) {
    console.error("La recette ne contient pas de steps à transformer");
    return recipe;
  }

  return transformToSubRecipes(recipe);
};

export const correctIngredientAmounts = (recipe) => {
  if (!recipe || !recipe.subRecipes || !recipe.ingredients) return recipe;

  const ingredientsMap = {};
  recipe.ingredients.forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  const correctedSubRecipes = recipe.subRecipes.map((subRecipe) => {
    if (!Array.isArray(subRecipe.ingredients)) return subRecipe;

    const correctedIngredients = subRecipe.ingredients.map((ing) => {
      const originalIngredient = ingredientsMap[ing.ref];
      if (!originalIngredient) return ing;

      let amount = parseFloat(ing.amount);
      if (isNaN(amount)) amount = 0;

      let unit = ing.unit || originalIngredient.unit || null;

      return {
        ...ing,
        amount,
        unit,
        category: ing.category || originalIngredient.category,
        name: originalIngredient.name,
      };
    });

    return {
      ...subRecipe,
      ingredients: correctedIngredients,
    };
  });

  return {
    ...recipe,
    subRecipes: correctedSubRecipes,
  };
};

export const computeRemainingTime = (recipe, completedSteps) => {
  if (!recipe?.subRecipes) return 0;
  let totalTime = 0;
  recipe.subRecipes.forEach((subRecipe) => {
    if (subRecipe.steps) {
      subRecipe.steps.forEach((step) => {
        if (!completedSteps[step.id] && step.time) {
          totalTime += parseTimeToMinutes(step.time);
        }
      });
    }
  });
  return totalTime;
};

export const computeSubRecipeRemainingTime = (recipe, completedSteps, subRecipeId) => {
  if (!recipe?.subRecipes) return 0;
  const subRecipe = recipe.subRecipes.find((sr) => sr.id === subRecipeId);
  if (!subRecipe) return 0;
  return (
    subRecipe.steps.reduce((total, step) => {
      if (!step.time || completedSteps[step.id]) return total;
      return total + parseTimeToMinutes(step.time);
    }, 0) || 0
  );
};
