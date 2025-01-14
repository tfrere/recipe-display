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
import {
  scaleIngredientAmount,
  getFractionDisplay,
} from "../utils/ingredientScaling";
import { normalizeAmount } from "../utils/unitNormalization";
import { convertToImperial } from "../utils/unitConversion";
import { mapUnitToTranslationKey } from "../utils/unitMapping";
import { parseTimeToMinutes, calculateTotalTime } from "../utils/timeUtils";
import { usePreferences } from "./PreferencesContext";

const RecipeContext = createContext();

const initialState = {
  recipe: null,
  selectedSubRecipe: null,
  completedSteps: {},
  completedSubRecipes: {},
  unusedIngredients: {
    bySubRecipe: {},
  },
  unusedTools: {},
  unusedStates: new Set(),
  loading: false,
  error: null,
  selectedView: "simple",
  servingsMultiplier: 1,
  currentServings: 0,
  tools: [],
};

// Actions
const actions = {
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

// Fonction utilitaire pour calculer les éléments non utilisés
const calculateUnusedItems = (recipe, completedSteps) => {
  const unusedIngredients = {
    bySubRecipe: {},
  };
  const unusedTools = {};
  const unusedStates = new Set();

  // Traiter toutes les sous-recettes
  recipe.subRecipes.forEach((subRecipe) => {
    // Initialiser le tableau des ingrédients inutilisés pour cette sous-recette
    unusedIngredients.bySubRecipe[subRecipe.id] = {};

    // Construire un graphe de dépendances
    const graph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses successeurs)
    const reverseGraph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses prédécesseurs)

    // Initialiser les ensembles pour chaque nœud
    (subRecipe.steps || []).forEach((step) => {
      graph.set(step.id, new Set());
      reverseGraph.set(step.id, new Set());

      // Ajouter les liens pour les inputs
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

      // Ajouter les liens pour les outils
      if (step.tools) {
        step.tools.forEach((toolId) => {
          const toolNodeId = `tool-${toolId}`;
          if (!graph.has(toolNodeId)) {
            graph.set(toolNodeId, new Set());
            reverseGraph.set(toolNodeId, new Set());
          }
          graph.get(toolNodeId).add(step.id);
          reverseGraph.get(step.id).add(toolNodeId);
        });
      }

      // Ajouter les liens pour l'output
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

    // Pour chaque étape complétée
    (subRecipe.steps || []).forEach((step) => {
      if (completedSteps[step.id]) {
        // Marquer tous les nœuds qui précèdent cette étape comme potentiellement inutilisés
        const visited = new Set();
        const stack = [step.id];

        while (stack.length > 0) {
          const currentId = stack.pop();
          if (visited.has(currentId)) continue;
          visited.add(currentId);

          // Ajouter tous les prédécesseurs à la pile
          const predecessors = reverseGraph.get(currentId) || new Set();
          for (const predId of predecessors) {
            if (!visited.has(predId)) {
              stack.push(predId);
            }
          }

          // Marquer le nœud comme inutilisé s'il n'est pas utilisé plus tard
          const isUsedLater = Array.from(
            graph.get(currentId) || new Set()
          ).some((successorId) => {
            // Si c'est une étape de la sous-recette actuelle et qu'elle n'est pas complétée, le nœud est encore utilisé
            if (subRecipe.steps?.some((s) => s.id === successorId)) {
              return !completedSteps[successorId];
            }
            // Si c'est une étape d'une autre sous-recette, on considère que le nœud est toujours utilisé
            return true;
          });

          if (!isUsedLater) {
            if (currentId.startsWith("ingredient-")) {
              const ingredientId = currentId.replace("ingredient-", "");
              const ingredient = recipe.ingredients?.find(
                (ing) => ing.id === ingredientId
              );
              if (ingredient) {
                // Marquer l'ingrédient comme inutilisé uniquement pour cette sous-recette
                unusedIngredients.bySubRecipe[subRecipe.id][
                  ingredientId
                ] = true;
              }
            } else if (currentId.startsWith("tool-")) {
              unusedTools[currentId.replace("tool-", "")] = true;
            } else {
              // Si ce n'est ni un ingrédient ni un outil, c'est un état
              const isState = Object.values(subRecipe.steps || {}).some(
                (s) => s.output && s.output.state === currentId
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

// Fonction utilitaire pour extraire les outils des steps
const extractToolsFromSteps = (recipe) => {
  const toolsSet = new Set();

  // Parcourir toutes les sous-recettes
  recipe.subRecipes.forEach((subRecipe) => {
    // Parcourir toutes les étapes de la sous-recette
    (subRecipe.steps || []).forEach((step) => {
      // Ajouter chaque outil à l'ensemble
      (step.tools || []).forEach((tool) => toolsSet.add(tool));
    });
  });

  // Convertir l'ensemble en tableau et créer les objets d'outils
  return Array.from(toolsSet).map((toolName) => ({
    id: toolName.toLowerCase().replace(/\s+/g, "-"),
    name: toolName,
  }));
};

// Reducer
const recipeReducer = (state, action) => {
  switch (action.type) {
    case actions.SET_RECIPE:
      const recipeServings = action.payload?.servings || 4;
      // Préfixer les IDs des steps avec leur subRecipeId
      const modifiedRecipe = {
        ...action.payload,
        subRecipes: action.payload.subRecipes.map((subRecipe) => ({
          ...subRecipe,
          steps: subRecipe.steps.map((step) => ({
            ...step,
            id: `${subRecipe.id}_${step.id}`,
          })),
        })),
      };
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

    case actions.SET_SELECTED_SUBRECIPE:
      return {
        ...state,
        selectedSubRecipe: action.payload,
      };

    case actions.TOGGLE_STEP_COMPLETION: {
      const newCompletedSteps = {
        ...state.completedSteps,
        [action.payload.stepId]: action.payload.completed,
      };

      const subRecipeId = action.payload.subRecipeId;
      const subRecipe = state.recipe?.subRecipes?.[subRecipeId];

      if (!subRecipe?.steps) {
        return {
          ...state,
          completedSteps: newCompletedSteps,
        };
      }

      // Si on coche une étape, on doit cocher toutes les étapes précédentes
      if (action.payload.completed) {
        // Construire le graphe de dépendances
        const reverseGraph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses prédécesseurs)

        // Initialiser les ensembles pour chaque nœud
        Object.values(subRecipe.steps || {}).forEach((step) => {
          reverseGraph.set(step.id, new Set());

          // Ajouter les liens pour les inputs de type "state"
          (step.inputs || [])
            .filter((input) => input.type === "state")
            .forEach((input) => {
              // Trouver l'étape qui produit cet état dans la même sous-recette
              const producerStep = subRecipe.steps.find(
                (s) => s.output && s.output.state === input.ref
              );
              if (producerStep) {
                reverseGraph.get(step.id).add(producerStep.id);
              }
            });
        });

        // Parcourir le graphe en remontant pour marquer toutes les étapes précédentes
        const visited = new Set();
        const stack = [action.payload.stepId];

        while (stack.length > 0) {
          const currentId = stack.pop();
          if (visited.has(currentId)) continue;
          visited.add(currentId);

          // Marquer l'étape comme complétée
          newCompletedSteps[currentId] = true;

          // Ajouter tous les prédécesseurs à la pile
          const predecessors = reverseGraph.get(currentId) || new Set();
          for (const predId of predecessors) {
            if (!visited.has(predId)) {
              stack.push(predId);
            }
          }
        }
      }

      // Calculer les éléments non utilisés après la mise à jour
      const { unusedIngredients, unusedTools, unusedStates } =
        calculateUnusedItems(state.recipe, newCompletedSteps);

      // Vérifier si toutes les étapes de la sous-recette sont complétées
      const allStepsCompleted = Object.values(subRecipe.steps || {}).every(
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
      const subRecipe = state.recipe?.subRecipes?.[subRecipeId];

      if (!subRecipe?.steps) {
        return state;
      }

      // Mettre à jour toutes les étapes de la sous-recette
      const newCompletedSteps = { ...state.completedSteps };
      Object.values(subRecipe.steps || {}).forEach((step) => {
        newCompletedSteps[step.id] = completed;
      });

      // Calculer les éléments non utilisés après la mise à jour
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
      return {
        ...state,
        loading: action.payload,
      };

    case actions.SET_ERROR:
      return {
        ...state,
        error: action.payload,
      };

    case actions.BATCH_UPDATE:
      return {
        ...state,
        ...action.payload,
      };

    case actions.SET_SELECTED_VIEW:
      return {
        ...state,
        selectedView: action.payload,
      };

    case actions.UPDATE_SERVINGS:
      return {
        ...state,
        servingsMultiplier: action.payload,
        currentServings: Math.round(
          state.recipe.metadata.servings * action.payload
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
        currentServings: state.recipe?.servings || 4,
      };

    case actions.RESET_STEPS:
      return {
        ...state,
        completedSteps: {},
        completedSubRecipes: {},
      };

    case actions.RESET_SERVINGS:
      const originalServings = state.recipe?.servings || 4;
      return {
        ...state,
        servingsMultiplier: 1,
        currentServings: originalServings,
      };

    default:
      return state;
  }
};

export const RecipeProvider = ({ children }) => {
  const { constants } = useConstants();
  const { preferences } = usePreferences();
  const [state, dispatch] = useReducer(recipeReducer, initialState);
  const [unitSystem, setUnitSystem] = useLocalStorage(
    "unitSystem",
    constants?.units?.systems?.METRIC || "metric"
  );

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  // Mise à jour du système d'unités en fonction des préférences
  useEffect(() => {
    if (preferences?.unitSystem) {
      setUnitSystem(preferences.unitSystem);
    }
  }, [preferences?.unitSystem, setUnitSystem]);

  // Définir UNITS et UNIT_CONVERSIONS à partir des données reçues
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

  // Log pour debug
  console.log("Constants:", constants);
  console.log("UNITS:", UNITS);

  const UNIT_CONVERSIONS = {
    // Ajouter vos conversions d'unités ici si nécessaire
  };

  console.log("Constants loaded:", { UNITS, UNIT_CONVERSIONS });

  const FRACTION_UNITS = [
    ...(constants.units.volume?.spoons || []),
    ...(constants.units.volume?.containers || []),
  ];

  const API_BASE_URL =
    import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

  // État local pour stocker le slug de la recette actuelle
  const [currentRecipeSlug, setCurrentRecipeSlug] = useState(null);

  // Utiliser des clés de stockage basées sur le slug
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

  // Fonction utilitaire pour obtenir le temps total restant
  const getRemainingTime = useCallback(() => {
    if (!state.recipe?.subRecipes) return 0;

    let totalTime = 0;
    state.recipe.subRecipes.forEach((subRecipe) => {
      if (subRecipe.steps) {
        subRecipe.steps.forEach((step) => {
          if (!state.completedSteps[step.id] && step.time) {
            totalTime += parseTimeToMinutes(step.time);
          }
        });
      }
    });

    return totalTime;
  }, [state.recipe, state.completedSteps]);

  const getSubRecipeRemainingTime = useCallback(
    (subRecipeId) => {
      if (!state.recipe || !state.recipe.subRecipes[subRecipeId]) return 0;
      const subRecipe = state.recipe.subRecipes[subRecipeId];
      return (
        subRecipe.steps.reduce((total, step) => {
          if (!step.time || state.completedSteps[step.id]) return total;
          return total + parseTimeToMinutes(step.time);
        }, 0) || 0
      );
    },
    [state.recipe, state.completedSteps]
  );

  // Réinitialiser les étapes complétées quand on change de recette
  useEffect(() => {
    if (currentRecipeSlug) {
      const completedStepsKey = getStorageKey("completed-steps");
      const completedSubRecipesKey = getStorageKey("completed-subrecipes");

      const savedCompletedSteps = JSON.parse(
        localStorage.getItem(completedStepsKey) || "{}"
      );
      const savedCompletedSubRecipes = JSON.parse(
        localStorage.getItem(completedSubRecipesKey) || "{}"
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

  // Synchroniser les changements avec le localStorage de manière optimisée
  useEffect(() => {
    if (!currentRecipeSlug) return;

    const timeoutId = setTimeout(() => {
      const completedStepsKey = getStorageKey("completed-steps");
      const completedSubRecipesKey = getStorageKey("completed-subrecipes");

      localStorage.setItem(
        completedStepsKey,
        JSON.stringify(state.completedSteps)
      );
      localStorage.setItem(
        completedSubRecipesKey,
        JSON.stringify(state.completedSubRecipes)
      );
      localStorage.setItem("selectedView", state.selectedView);
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [
    state.completedSteps,
    state.completedSubRecipes,
    state.selectedView,
    currentRecipeSlug,
  ]);

  useEffect(() => {
    if (state.recipe) {
      const extractedTools = extractToolsFromSteps(state.recipe);
      setTools(extractedTools);
    }
  }, [state.recipe]);

  const loadRecipe = useCallback(async (slug) => {
    dispatch({ type: actions.SET_LOADING, payload: true });
    try {
      const fullUrl = `${API_BASE_URL}/api/recipes/${slug}`;

      const response = await fetch(fullUrl);
      if (!response.ok) {
        throw new Error("Failed to fetch recipe");
      }
      const recipe = await response.json();
      console.log("Recipe received by client:", recipe);
      setCurrentRecipeSlug(slug); // Mettre à jour le slug de la recette actuelle
      dispatch({ type: actions.SET_RECIPE, payload: recipe });
      dispatch({ type: actions.SET_ERROR, payload: null });
    } catch (error) {
      console.error("Error loading recipe:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
    } finally {
      dispatch({ type: actions.SET_LOADING, payload: false });
    }
  }, []);

  // Réinitialiser l'état quand on change de recette
  const resetRecipeState = useCallback(() => {
    setCurrentRecipeSlug(null);
    dispatch({ type: actions.RESET_RECIPE_STATE });
  }, []);

  const generateRecipe = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/recipes/generate`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to generate recipe");
      }
      const data = await response.json();
      dispatch({ type: actions.SET_RECIPE, payload: data });
      dispatch({ type: actions.SET_ERROR, payload: null });
    } catch (error) {
      console.error("Error generating recipe:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
    }
  }, []);

  const setSelectedSubRecipe = useCallback((subRecipeId) => {
    dispatch({ type: actions.SET_SELECTED_SUBRECIPE, payload: subRecipeId });
  }, []);

  const toggleStepCompletion = useCallback((stepId, completed, subRecipeId) => {
    dispatch({
      type: actions.TOGGLE_STEP_COMPLETION,
      payload: { stepId, completed, subRecipeId },
    });
  }, []);

  const toggleSubRecipeCompletion = useCallback((subRecipeId, completed) => {
    dispatch({
      type: actions.TOGGLE_SUBRECIPE_COMPLETION,
      payload: { subRecipeId, completed },
    });
  }, []);

  // Fonction utilitaire pour obtenir le nombre d'étapes complétées pour une sous-recette
  const getSubRecipeProgress = useCallback(
    (subRecipeId) => {
      if (!state.recipe || !state.recipe.subRecipes[subRecipeId]) return 0;
      const subRecipe = state.recipe.subRecipes[subRecipeId];
      const totalSteps = subRecipe.steps.length;
      if (totalSteps === 0) return 0;

      const completedSteps = subRecipe.steps.filter(
        (step) => state.completedSteps[step.id]
      ).length;

      return (completedSteps / totalSteps) * 100;
    },
    [state.recipe, state.completedSteps]
  );

  // Fonction utilitaire pour obtenir le nombre total d'étapes complétées
  const getTotalProgress = useCallback(() => {
    if (!state.recipe) return 0;
    const totalSteps = state.recipe.subRecipes.reduce(
      (total, subRecipe) => total + subRecipe.steps.length,
      0
    );
    const completedSteps = Object.keys(state.completedSteps || {}).length;
    return totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
  }, [state.recipe, state.completedSteps]);

  const getAdjustedAmount = useCallback(
    (amount, unit, category) => {
      if (!state.recipe || !amount) return amount;
      return scaleIngredientAmount(
        amount,
        unit,
        category,
        state.servingsMultiplier,
        constants
      );
    },
    [state.recipe, state.servingsMultiplier, constants]
  );

  const formatAmount = useCallback(
    (amount, unit) => {
      if (!amount && amount !== 0) return "-";
      if (unit && amount === "") return "-";
      if (!unit) return "-";

      // Conversion si nécessaire
      if (unitSystem === "imperial") {
        const { value: convertedAmount, unit: convertedUnit } =
          convertToImperial(amount, unit);
        amount = convertedAmount;
        unit = convertedUnit;
      }

      // Formatage existant
      let formattedAmount;
      if (amount >= 1000) {
        formattedAmount = (amount / 1000).toFixed(2);
        unit = unit === "g" ? "kg" : unit === "ml" ? "l" : unit;
      } else {
        formattedAmount = Math.round(amount * 100) / 100;
      }

      // Suppression des zéros inutiles après la virgule
      formattedAmount = Number(formattedAmount).toString();

      // Get the unit from our constants
      const translatedUnit =
        UNITS[mapUnitToTranslationKey(unit).toUpperCase()] || unit;

      return `${formattedAmount}${translatedUnit ? " " + translatedUnit : ""}`;
    },
    [unitSystem, UNITS] // Ajout de UNITS aux dépendances
  );

  const getTotalProgressPercentage = useCallback(() => {
    if (!state.recipe) return 0;
    const totalSteps = state.recipe.subRecipes.reduce(
      (total, subRecipe) => total + subRecipe.steps.length,
      0
    );
    const completedSteps = Object.keys(state.completedSteps || {}).length;
    return totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
  }, [state.recipe, state.completedSteps]);

  const isIngredientUnused = useCallback(
    (ingredientId, subRecipeId) => {
      if (!state.recipe) return false;
      const { unusedIngredients } = calculateUnusedItems(
        state.recipe,
        state.completedSteps
      );
      return (
        (unusedIngredients.bySubRecipe[subRecipeId] &&
          unusedIngredients.bySubRecipe[subRecipeId][ingredientId]) ||
        false
      );
    },
    [state.recipe, state.completedSteps]
  );

  const isToolUnused = useCallback(
    (toolId) => {
      if (!state.recipe) return false;
      const { unusedTools } = calculateUnusedItems(
        state.recipe,
        state.completedSteps
      );
      return unusedTools[toolId] || false;
    },
    [state.recipe, state.completedSteps]
  );

  // Fonction pour formater un ingrédient
  const formatIngredient = useCallback(
    (ingredient, multiplier = 1) => {
      const amount = ingredient.amount * multiplier;
      const unit = ingredient.unit;
      const name = ingredient.name;

      const formattedAmount = unit
        ? normalizeAmount(amount, unit, constants)
        : getFractionDisplay(amount);

      return unit
        ? `${formattedAmount} de ${name}`
        : `${formattedAmount} ${name}`;
    },
    [constants]
  );

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
    getSubRecipeStats: useCallback(
      (subRecipeId) => {
        const subRecipe = state.recipe?.subRecipes?.[subRecipeId];
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

        const originalServings = state.recipe.metadata.servings;
        const multiplier = newServings / originalServings;

        dispatch({
          type: actions.UPDATE_SERVINGS,
          payload: multiplier,
        });
      },
      [state.recipe]
    ),
    getAdjustedAmount,
    formatAmount,
    getTotalProgress,
    getTotalProgressPercentage,
    isIngredientUnused,
    isToolUnused,
    getSubRecipeProgress: useCallback(
      (subRecipeId) => {
        if (!state.recipe || !state.recipe.subRecipes[subRecipeId]) return 0;
        const subRecipe = state.recipe.subRecipes[subRecipeId];
        const totalSteps = subRecipe.steps.length;
        if (totalSteps === 0) return 0;

        const completedSteps = subRecipe.steps.filter(
          (step) => state.completedSteps[step.id]
        ).length;

        return (completedSteps / totalSteps) * 100;
      },
      [state.recipe, state.completedSteps]
    ),
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
    calculateTotalTime: useCallback((recipe) => {
      if (!recipe || !recipe.subRecipes) return "0min";

      let totalMinutes = 0;
      // Iterate over subRecipes object
      recipe.subRecipes.forEach((subRecipe) => {
        if (!subRecipe.steps) return;

        subRecipe.steps.forEach((step) => {
          const time = step.time;
          if (!time) return;

          // Parse hours if present
          const hourMatch = time.match(/(\d+)h/);
          if (hourMatch) {
            totalMinutes += parseInt(hourMatch[1]) * 60;
          }

          // Parse minutes if present
          const minuteMatch = time.match(/(\d+)min/);
          if (minuteMatch) {
            totalMinutes += parseInt(minuteMatch[1]);
          }
        });
      });

      // Format the total time
      if (totalMinutes >= 60) {
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return minutes > 0 ? `${hours}h${minutes}min` : `${hours}h`;
      }
      return `${totalMinutes}min`;
    }, []),
    resetAllSteps: () => dispatch({ type: actions.RESET_STEPS }),
    resetServings: () => dispatch({ type: actions.RESET_SERVINGS }),
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
