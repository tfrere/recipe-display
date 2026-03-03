import {
  calculateUnusedItems,
  transformStepsToSubRecipes,
  correctIngredientAmounts,
} from "./recipeHelpers";

export const actions = {
  SET_RECIPE: "SET_RECIPE",
  SET_SELECTED_SUBRECIPE: "SET_SELECTED_SUBRECIPE",
  TOGGLE_STEP_COMPLETION: "TOGGLE_STEP_COMPLETION",
  TOGGLE_SUBRECIPE_COMPLETION: "TOGGLE_SUBRECIPE_COMPLETION",
  SET_LOADING: "SET_LOADING",
  SET_ERROR: "SET_ERROR",
  BATCH_UPDATE: "BATCH_UPDATE",
  UPDATE_UNUSED_ITEMS: "UPDATE_UNUSED_ITEMS",
  SET_SELECTED_VIEW: "SET_SELECTED_VIEW",
  UPDATE_SERVINGS: "UPDATE_SERVINGS",
  RESET_RECIPE_STATE: "RESET_RECIPE_STATE",
  RESET_STEPS: "RESET_STEPS",
  RESET_SERVINGS: "RESET_SERVINGS",
};

export const initialState = {
  recipe: null,
  selectedSubRecipe: null,
  completedSteps: {},
  completedSubRecipes: {},
  unusedIngredients: { bySubRecipe: {} },
  unusedTools: {},
  unusedStates: new Set(),
  loading: false,
  error: null,
  selectedView: "simple",
  servingsMultiplier: 1,
  currentServings: 0,
  tools: [],
};

export const recipeReducer = (state, action) => {
  switch (action.type) {
    case actions.SET_RECIPE: {
      const recipeServings = action.payload?.metadata?.servings || 4;
      const transformedRecipe =
        action.payload.steps && !action.payload.subRecipes
          ? transformStepsToSubRecipes(action.payload)
          : action.payload;

      const safeSubRecipes = transformedRecipe.subRecipes || [];

      const modifiedRecipe = correctIngredientAmounts({
        ...transformedRecipe,
        subRecipes: safeSubRecipes.map((subRecipe) => ({
          ...subRecipe,
          steps: (subRecipe.steps || []).map((step) => ({
            ...step,
            id: `${subRecipe.id}_${step.id}`,
          })),
        })),
      });

      return {
        ...state,
        recipe: modifiedRecipe,
        completedSteps: {},
        completedSubRecipes: {},
        unusedIngredients: { bySubRecipe: {} },
        unusedTools: {},
        unusedStates: new Set(),
        servingsMultiplier: 1,
        currentServings: recipeServings,
        selectedSubRecipe: null,
      };
    }

    case actions.SET_SELECTED_SUBRECIPE:
      return { ...state, selectedSubRecipe: action.payload };

    case actions.TOGGLE_STEP_COMPLETION: {
      const newCompletedSteps = {
        ...state.completedSteps,
        [action.payload.stepId]: action.payload.completed,
      };

      const subRecipeId = action.payload.subRecipeId;
      const subRecipe = (state.recipe?.subRecipes || []).find(
        (sr) => sr.id === subRecipeId
      );

      if (!subRecipe?.steps) {
        return { ...state, completedSteps: newCompletedSteps };
      }

      if (action.payload.completed) {
        const reverseGraph = new Map();
        (subRecipe.steps || []).forEach((step) => {
          reverseGraph.set(step.id, new Set());
          (step.inputs || [])
            .filter((input) => input.type === "state")
            .forEach((input) => {
              const producerStep = subRecipe.steps.find(
                (s) => s.output && s.output.state === input.ref
              );
              if (producerStep) {
                reverseGraph.get(step.id).add(producerStep.id);
              }
            });
          (step.tools || []).forEach((toolRef) => {
            const producerStep = subRecipe.steps.find(
              (s) => s.output && s.output.state === toolRef
            );
            if (producerStep) {
              reverseGraph.get(step.id).add(producerStep.id);
            }
          });
        });

        const visited = new Set();
        const stack = [action.payload.stepId];
        while (stack.length > 0) {
          const currentId = stack.pop();
          if (visited.has(currentId)) continue;
          visited.add(currentId);
          newCompletedSteps[currentId] = true;
          const predecessors = reverseGraph.get(currentId) || new Set();
          for (const predId of predecessors) {
            if (!visited.has(predId)) stack.push(predId);
          }
        }
      }

      const { unusedIngredients, unusedTools, unusedStates } =
        calculateUnusedItems(state.recipe, newCompletedSteps);

      const allStepsCompleted = (subRecipe.steps || []).every(
        (step) => newCompletedSteps[step.id]
      );

      return {
        ...state,
        completedSteps: newCompletedSteps,
        completedSubRecipes: {
          ...state.completedSubRecipes,
          [subRecipeId]: allStepsCompleted,
        },
        unusedIngredients,
        unusedTools,
        unusedStates,
      };
    }

    case actions.TOGGLE_SUBRECIPE_COMPLETION: {
      const { subRecipeId, completed } = action.payload;
      const subRecipe = (state.recipe?.subRecipes || []).find(
        (sr) => sr.id === subRecipeId
      );
      if (!subRecipe?.steps) return state;

      const newCompletedSteps = { ...state.completedSteps };
      (subRecipe.steps || []).forEach((step) => {
        newCompletedSteps[step.id] = completed;
      });

      const { unusedIngredients, unusedTools, unusedStates } =
        calculateUnusedItems(state.recipe, newCompletedSteps);

      return {
        ...state,
        completedSteps: newCompletedSteps,
        completedSubRecipes: {
          ...state.completedSubRecipes,
          [subRecipeId]: completed,
        },
        unusedIngredients,
        unusedTools,
        unusedStates,
      };
    }

    case actions.SET_LOADING:
      return { ...state, loading: action.payload };

    case actions.SET_ERROR:
      return { ...state, error: action.payload };

    case actions.BATCH_UPDATE:
      return { ...state, ...action.payload };

    case actions.SET_SELECTED_VIEW:
      return { ...state, selectedView: action.payload };

    case actions.UPDATE_SERVINGS:
      return {
        ...state,
        servingsMultiplier: action.payload,
        currentServings: Math.round(
          (state.recipe?.metadata?.servings || 4) * action.payload
        ),
      };

    case actions.RESET_RECIPE_STATE:
      return {
        ...state,
        completedSteps: {},
        completedSubRecipes: {},
        unusedIngredients: { bySubRecipe: {} },
        unusedTools: {},
        unusedStates: new Set(),
        servingsMultiplier: 1,
        currentServings: state.recipe?.metadata?.servings || 4,
      };

    case actions.RESET_STEPS:
      return { ...state, completedSteps: {}, completedSubRecipes: {} };

    case actions.RESET_SERVINGS: {
      const originalServings = state.recipe?.metadata?.servings || 4;
      return { ...state, servingsMultiplier: 1, currentServings: originalServings };
    }

    default:
      return state;
  }
};
