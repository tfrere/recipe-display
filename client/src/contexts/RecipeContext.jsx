import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useReducer,
  useCallback,
} from "react";
import { useConstants } from "./ConstantsContext";
import useLocalStorage from "../hooks/useLocalStorage";
import { scaleIngredientAmount } from "../utils/ingredientScaling";
import { mapUnitToTranslationKey } from "../utils/unitMapping";
import { convertIngredient, formatConvertedQuantity } from "../utils/unitConversion";
import { recipeReducer, actions, initialState } from "./recipeReducer";
import {
  calculateUnusedItems,
  extractToolsFromSteps,
  transformStepsToSubRecipes,
  computeRemainingTime,
  computeSubRecipeRemainingTime,
} from "./recipeHelpers";

const RecipeContext = createContext();

export const RecipeProvider = ({ children }) => {
  const { constants } = useConstants();
  const [state, dispatch] = useReducer(recipeReducer, initialState);
  const [unitSystem, setUnitSystem] = useLocalStorage("unit_system", "metric");

  if (!constants) return null;

  const UNITS = {
    ...constants.units.weight,
    ...constants.units.integer.reduce(
      (acc, unit) => ({ ...acc, [unit]: unit }),
      {}
    ),
    tablespoon: "tablespoon",
    teaspoon: "teaspoon",
    cup: "cup",
    pinch: "pinch",
  };

  const API_BASE_URL =
    import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";
  const getPrivateToken = () => {
    try {
      return JSON.parse(localStorage.getItem("privateToken") || "null");
    } catch {
      return null;
    }
  };

  const [currentRecipeSlug, setCurrentRecipeSlug] = useState(null);

  const getStorageKey = (key) =>
    currentRecipeSlug ? `recipe-${currentRecipeSlug}-${key}` : null;

  const [storedCompletedSteps, setStoredCompletedSteps] = useLocalStorage(
    getStorageKey("completed-steps") || "temp-completed-steps",
    {}
  );
  const [storedCompletedSubRecipes, setStoredCompletedSubRecipes] =
    useLocalStorage(
      getStorageKey("completed-subrecipes") || "temp-completed-subrecipes",
      {}
    );

  const [selectedView, setSelectedView] = useState(() => {
    const savedView = localStorage.getItem("selectedView");
    return savedView || "simple";
  });

  const [tools, setTools] = useState([]);

  // ── Time helpers ──

  const getRemainingTime = useCallback(
    () => computeRemainingTime(state.recipe, state.completedSteps),
    [state.recipe, state.completedSteps]
  );

  const getSubRecipeRemainingTime = useCallback(
    (subRecipeId) =>
      computeSubRecipeRemainingTime(state.recipe, state.completedSteps, subRecipeId),
    [state.recipe, state.completedSteps]
  );

  // ── LocalStorage sync ──

  useEffect(() => {
    if (currentRecipeSlug) {
      const savedCompletedSteps = JSON.parse(
        localStorage.getItem(getStorageKey("completed-steps")) || "{}"
      );
      const savedCompletedSubRecipes = JSON.parse(
        localStorage.getItem(getStorageKey("completed-subrecipes")) || "{}"
      );
      dispatch({
        type: actions.BATCH_UPDATE,
        payload: {
          completedSteps: savedCompletedSteps,
          completedSubRecipes: savedCompletedSubRecipes,
        },
      });
    }
  }, [currentRecipeSlug]);

  useEffect(() => {
    if (!currentRecipeSlug) return;
    const timeoutId = setTimeout(() => {
      localStorage.setItem(
        getStorageKey("completed-steps"),
        JSON.stringify(state.completedSteps)
      );
      localStorage.setItem(
        getStorageKey("completed-subrecipes"),
        JSON.stringify(state.completedSubRecipes)
      );
      localStorage.setItem("selectedView", state.selectedView);
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [state.completedSteps, state.completedSubRecipes, state.selectedView, currentRecipeSlug]);

  useEffect(() => {
    if (state.recipe) {
      setTools(extractToolsFromSteps(state.recipe));
    }
  }, [state.recipe]);

  // ── API ──

  const loadRecipe = useCallback(async (slug) => {
    dispatch({ type: actions.SET_LOADING, payload: true });
    try {
      const headers = {};
      const hasAccess = JSON.parse(localStorage.getItem("hasPrivateAccess") || "false");
      const token = getPrivateToken();
      if (hasAccess && token) {
        headers["X-Private-Token"] = token;
      }
      const response = await fetch(`${API_BASE_URL}/api/recipes/${slug}`, { headers });
      if (!response.ok) throw new Error("Failed to fetch recipe");
      const recipe = await response.json();
      setCurrentRecipeSlug(slug);
      dispatch({ type: actions.SET_RECIPE, payload: recipe });
      dispatch({ type: actions.SET_ERROR, payload: null });
      return recipe;
    } catch (error) {
      console.error("Error loading recipe:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
      throw error;
    } finally {
      dispatch({ type: actions.SET_LOADING, payload: false });
    }
  }, []);

  const loadRecipeWithSteps = useCallback(async (recipeData) => {
    dispatch({ type: actions.SET_LOADING, payload: true });
    try {
      if (!recipeData.steps) throw new Error("La recette fournie ne contient pas de steps");
      dispatch({ type: actions.SET_RECIPE, payload: recipeData });
      dispatch({ type: actions.SET_ERROR, payload: null });
      if (recipeData.metadata?.slug) setCurrentRecipeSlug(recipeData.metadata.slug);
    } catch (error) {
      console.error("Error loading recipe with steps:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
    } finally {
      dispatch({ type: actions.SET_LOADING, payload: false });
    }
  }, []);

  const generateRecipe = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/recipes/generate`, { method: "POST" });
      if (!response.ok) throw new Error("Failed to generate recipe");
      const data = await response.json();
      dispatch({ type: actions.SET_RECIPE, payload: data });
      dispatch({ type: actions.SET_ERROR, payload: null });
    } catch (error) {
      console.error("Error generating recipe:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
    }
  }, []);

  const resetRecipeState = useCallback(() => {
    setCurrentRecipeSlug(null);
    dispatch({ type: actions.RESET_RECIPE_STATE });
  }, []);

  // ── Dispatchers ──

  const setSelectedSubRecipe = useCallback((id) => {
    dispatch({ type: actions.SET_SELECTED_SUBRECIPE, payload: id });
  }, []);

  const toggleStepCompletion = useCallback((stepId, completed, subRecipeId) => {
    dispatch({ type: actions.TOGGLE_STEP_COMPLETION, payload: { stepId, completed, subRecipeId } });
  }, []);

  const toggleSubRecipeCompletion = useCallback((subRecipeId, completed) => {
    dispatch({ type: actions.TOGGLE_SUBRECIPE_COMPLETION, payload: { subRecipeId, completed } });
  }, []);

  // ── Scaling & formatting ──

  const getAdjustedAmount = useCallback(
    (amount, unit, category) => {
      if (!state.recipe || !amount) return amount;
      const numericAmount = typeof amount === "string" ? parseFloat(amount) : amount;
      if (isNaN(numericAmount)) {
        console.warn(`Quantité invalide: ${amount}`);
        return amount;
      }
      return scaleIngredientAmount(numericAmount, unit, category, state.servingsMultiplier, constants);
    },
    [state.recipe, state.servingsMultiplier, constants]
  );

  const formatAmount = useCallback(
    (amount, unit, ingredient = null) => {
      if (amount == null || amount === "" || amount === 0) return "-";

      if (ingredient) {
        const result = convertIngredient(ingredient, unitSystem, amount, unit);
        if (result.converted) return formatConvertedQuantity(result.quantity, result.unit);
      }

      if (!unit) {
        if (Math.abs(Math.round(amount) - amount) < 0.01) return Math.round(amount).toString();
        return amount.toString();
      }

      let formattedAmount;
      if (amount >= 1000 && (unit === "g" || unit === "ml")) {
        formattedAmount = (amount / 1000).toFixed(2);
        unit = unit === "g" ? "kg" : unit === "ml" ? "l" : unit;
      } else {
        formattedAmount = Math.round(amount * 100) / 100;
      }
      formattedAmount = Number(formattedAmount).toString();

      let translatedUnit = unit;
      try {
        const normalizedUnit = mapUnitToTranslationKey(unit).toUpperCase();
        if (UNITS[normalizedUnit]) translatedUnit = UNITS[normalizedUnit];
      } catch (e) {
        console.warn(`Erreur lors de la traduction de l'unité ${unit}:`, e);
      }

      return `${formattedAmount}${translatedUnit ? " " + translatedUnit : ""}`;
    },
    [UNITS, unitSystem]
  );

  // ── Progress ──

  const getTotalProgress = useCallback(() => {
    if (!state.recipe) return 0;
    const totalSteps = state.recipe.subRecipes.reduce((t, sr) => t + sr.steps.length, 0);
    const completed = Object.keys(state.completedSteps || {}).length;
    return totalSteps > 0 ? (completed / totalSteps) * 100 : 0;
  }, [state.recipe, state.completedSteps]);

  const getTotalProgressPercentage = getTotalProgress;

  const getSubRecipeProgress = useCallback(
    (subRecipeId) => {
      if (!state.recipe?.subRecipes) return 0;
      const subRecipe = state.recipe.subRecipes.find((sr) => sr.id === subRecipeId);
      if (!subRecipe || subRecipe.steps.length === 0) return 0;
      const completed = subRecipe.steps.filter((step) => state.completedSteps[step.id]).length;
      return (completed / subRecipe.steps.length) * 100;
    },
    [state.recipe, state.completedSteps]
  );

  // ── Ingredient helpers ──

  const isIngredientUnused = useCallback(
    (ingredientId, subRecipeId) => {
      if (!state.recipe) return false;
      const { unusedIngredients } = calculateUnusedItems(state.recipe, state.completedSteps);
      return unusedIngredients.bySubRecipe[subRecipeId]?.[ingredientId] || false;
    },
    [state.recipe, state.completedSteps]
  );

  const isToolUnused = useCallback(
    (toolId) => {
      if (!state.recipe) return false;
      const { unusedTools } = calculateUnusedItems(state.recipe, state.completedSteps);
      return unusedTools[toolId] || false;
    },
    [state.recipe, state.completedSteps]
  );

  const getSubRecipeIngredients = useCallback(
    (subRecipeId) => {
      if (!state.recipe?.subRecipes) return [];
      const subRecipe = state.recipe.subRecipes.find((sr) => sr.id === subRecipeId);
      if (!subRecipe || !Array.isArray(subRecipe.ingredients)) return [];

      return subRecipe.ingredients
        .map((ingredient) => {
          const originalIngredient = state.recipe.ingredients.find(
            (ing) => ing.id === ingredient.ref
          );
          if (!originalIngredient) {
            console.warn(`Ingredient ${ingredient.ref} not found in recipe`);
            return null;
          }
          const amount = parseFloat(ingredient.amount);
          if (isNaN(amount)) {
            console.warn(`Quantité invalide pour l'ingrédient ${ingredient.ref}: ${ingredient.amount}`);
          }
          let unit = ingredient.unit || originalIngredient.unit;

          return {
            ...originalIngredient,
            amount,
            inputType: ingredient.inputType,
            type: ingredient.type,
            unit,
            category: ingredient.category || originalIngredient.category,
            subRecipeId,
          };
        })
        .filter(Boolean);
    },
    [state.recipe]
  );

  const formatStepIngredient = useCallback(
    (ingredient, subRecipeId) => {
      if (!ingredient || !state.recipe) return null;
      const originalIngredient = state.recipe.ingredients.find(
        (ing) => ing.id === (ingredient.ref_id || ingredient.ref)
      );
      if (!originalIngredient) return null;

      const adjustedAmount = getAdjustedAmount(
        ingredient.amount,
        originalIngredient.unit,
        originalIngredient.category
      );
      const formattedAmount = formatAmount(adjustedAmount, originalIngredient.unit, originalIngredient);

      return { ...originalIngredient, amount: adjustedAmount, formattedAmount, subRecipeId };
    },
    [state.recipe, getAdjustedAmount, formatAmount]
  );

  const getFormattedSubRecipeIngredients = useCallback(
    (subRecipeId) => {
      const ingredients = getSubRecipeIngredients(subRecipeId);
      return ingredients
        .map((ingredient) => {
          try {
            if (!ingredient) return null;
            let amount = parseFloat(ingredient.amount);
            if (isNaN(amount)) amount = 0;
            let unit = ingredient.unit || null;

            const adjustedAmount = getAdjustedAmount(amount, unit, ingredient.category);
            const formattedAmount = formatAmount(adjustedAmount, unit, ingredient);

            return {
              ...ingredient,
              amount: adjustedAmount,
              formattedAmount,
              unit,
              _initialAmount: amount,
              _unit: unit,
            };
          } catch (error) {
            console.error(`Erreur lors du formatage de l'ingrédient ${ingredient?.id || "inconnu"}:`, error);
            return {
              ...ingredient,
              amount: ingredient.amount || 0,
              formattedAmount: ingredient.amount ? `${ingredient.amount}` : "-",
              _error: error.message,
            };
          }
        })
        .filter(Boolean);
    },
    [getSubRecipeIngredients, getAdjustedAmount, formatAmount, state.servingsMultiplier]
  );

  // ── Context value ──

  const value = {
    ...state,
    recipe: state.recipe,
    loading: state.loading,
    error: state.error,
    selectedView: state.selectedView,
    tools,
    loadRecipe,
    generateRecipe,
    setSelectedSubRecipe,
    toggleStepCompletion,
    toggleSubRecipeCompletion,
    getRemainingTime,
    getSubRecipeRemainingTime,
    transformStepsToSubRecipes,
    loadRecipeWithSteps,
    getSubRecipeIngredients,
    formatStepIngredient,
    getFormattedSubRecipeIngredients,
    getSubRecipeStats: useCallback(
      (subRecipeId) => {
        const subRecipe = state.recipe?.subRecipes?.find((sr) => sr.id === subRecipeId);
        if (!subRecipe) return null;
        const totalSteps = subRecipe.steps.length;
        const completedStepsCount = subRecipe.steps.filter(
          (step) => state.completedSteps[step.id]
        ).length;
        return { totalSteps, completedStepsCount };
      },
      [state.recipe, state.completedSteps]
    ),
    getCompletedSubRecipesCount: useCallback(() => {
      return state.recipe.subRecipes.filter(
        (subRecipe) => state.completedSubRecipes[subRecipe.id]
      ).length;
    }, [state.recipe, state.completedSubRecipes]),
    updateServings: useCallback(
      (newServings) => {
        if (!state.recipe) return;
        const originalServings = state.recipe.metadata.servings || 4;
        dispatch({ type: actions.UPDATE_SERVINGS, payload: newServings / originalServings });
      },
      [state.recipe]
    ),
    getAdjustedAmount,
    formatAmount,
    getTotalProgress,
    getTotalProgressPercentage,
    isIngredientUnused,
    isToolUnused,
    getSubRecipeProgress,
    resetRecipeState,
    isRecipePristine: () => {
      if (!state.recipe) return true;
      return (
        Object.keys(state.completedSteps).length === 0 &&
        Object.keys(state.completedSubRecipes).length === 0 &&
        Object.keys(state.unusedIngredients.bySubRecipe).length === 0 &&
        Object.keys(state.unusedTools).length === 0 &&
        state.unusedStates.size === 0 &&
        state.servingsMultiplier === 1
      );
    },
    resetAllSteps: () => dispatch({ type: actions.RESET_STEPS }),
    resetServings: () => dispatch({ type: actions.RESET_SERVINGS }),
    unitSystem,
    setUnitSystem,
  };

  return (
    <RecipeContext.Provider value={value}>{children}</RecipeContext.Provider>
  );
};

export const useRecipe = () => {
  const context = useContext(RecipeContext);
  if (!context) {
    throw new Error("useRecipe must be used within a RecipeProvider");
  }
  return context;
};

export default RecipeContext;
