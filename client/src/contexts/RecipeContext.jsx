import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
  useState,
} from "react";
import constants from '@shared/constants.json';
const { volume: { spoons: SPOON_UNITS, containers: CONTAINER_UNITS } } = constants.units;
const FRACTION_UNITS = [...SPOON_UNITS, ...CONTAINER_UNITS];

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';
import useLocalStorage from "../hooks/useLocalStorage";
import { 
  scaleIngredientAmount, 
  getFractionDisplay,
} from '../utils/ingredientScaling';
import { normalizeAmount } from '../utils/unitNormalization';
import { usePreferences, UNIT_SYSTEMS } from './PreferencesContext';
import { convertToImperial } from '../utils/unitConversion';
import { mapUnitToTranslationKey } from '../utils/unitMapping';

const RECIPE_TEXTS = {
  UNITS: {
    GRAMS: 'g',
    KILOGRAMS: 'kg',
    MILLILITERS: 'ml',
    LITERS: 'l',
    TEASPOON: 'tsp',
    TABLESPOON: 'tbsp',
    CUP: 'cup',
    PINCH: 'pinch',
    PIECE: 'pc',
    BUNCH: 'bunch',
    CLOVE: 'clove',
    SLICE: 'slice',
    POUND: 'lb',
    OUNCE: 'oz',
    FLUID_OUNCE: 'fl oz',
    QUART: 'qt',
    PINT: 'pt',
  }
};

const RecipeContext = createContext();

const initialState = {
  recipe: null,
  selectedSubRecipe: null,
  completedSteps: {},
  completedSubRecipes: {},
  unusedIngredients: {
    bySubRecipe: {}
  },
  unusedTools: {},
  unusedStates: new Set(),
  loading: false,
  error: null,
  selectedView: 'simple',
  servingsMultiplier: 1,
  tools: []
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
};

// Fonction utilitaire pour calculer les éléments non utilisés
const calculateUnusedItems = (recipe, completedSteps) => {
  const unusedIngredients = {
    bySubRecipe: {}
  };
  const unusedTools = {};
  const unusedStates = new Set();

  // Traiter toutes les sous-recettes
  Object.entries(recipe.subRecipes || {}).forEach(([subRecipeId, subRecipe]) => {
    // Initialiser le tableau des ingrédients inutilisés pour cette sous-recette
    unusedIngredients.bySubRecipe[subRecipeId] = {};

    // Construire un graphe de dépendances
    const graph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses successeurs)
    const reverseGraph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses prédécesseurs)

    // Initialiser les ensembles pour chaque nœud
    Object.values(subRecipe.steps || {}).forEach((step) => {
      graph.set(step.id, new Set());
      reverseGraph.set(step.id, new Set());

      // Ajouter les liens pour les inputs
      (step.inputs || []).forEach((input) => {
        const inputId =
          input.type === "ingredient" ? `${input.type}-${input.ref}` : input.ref;

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
    Object.values(subRecipe.steps || {}).forEach((step) => {
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
          const isUsedLater = Array.from(graph.get(currentId) || new Set()).some(
            (successorId) => {
              // Si c'est une étape et qu'elle n'est pas complétée, le nœud est encore utilisé
              return Object.values(subRecipe.steps || {}).some(
                (s) => s.id === successorId && !completedSteps[s.id]
              );
            }
          );

          if (!isUsedLater) {
            if (currentId.startsWith("ingredient-")) {
              const ingredientId = currentId.replace("ingredient-", "");
              const ingredient = recipe.ingredients[ingredientId];
              if (ingredient) {
                // Marquer l'ingrédient comme inutilisé uniquement pour cette sous-recette
                unusedIngredients.bySubRecipe[subRecipeId][ingredientId] = true;
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
  Object.values(recipe.subRecipes || {}).forEach(subRecipe => {
    // Parcourir toutes les étapes de la sous-recette
    Object.values(subRecipe.steps || {}).forEach(step => {
      // Ajouter chaque outil à l'ensemble
      (step.tools || []).forEach(tool => toolsSet.add(tool));
    });
  });

  // Convertir l'ensemble en tableau et créer les objets d'outils
  return Array.from(toolsSet).map(toolName => ({
    id: toolName.toLowerCase().replace(/\s+/g, '-'),
    name: toolName
  }));
};

// Reducer
const recipeReducer = (state, action) => {
  switch (action.type) {
    case actions.SET_RECIPE:
      return {
        ...state,
        recipe: action.payload,
        selectedSubRecipe: action.payload?.subRecipes
          ? Object.keys(action.payload.subRecipes)[0]
          : null,
        unusedIngredients: {
          bySubRecipe: {}
        },
        unusedTools: {},
        unusedStates: new Set(),
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
              // Trouver l'étape qui produit cet état
              const producerStep = Object.values(subRecipe.steps || {}).find(
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
      };

    case actions.RESET_RECIPE_STATE:
      return {
        ...state,
        completedSteps: {},
        completedSubRecipes: {},
        unusedIngredients: {
          bySubRecipe: {}
        },
        unusedTools: {},
        unusedStates: new Set(),
        servingsMultiplier: 1,
      };

    default:
      return state;
  }
};

// Fonctions utilitaires pour la gestion du temps
const parseTimeToMinutes = (timeStr) => {
  if (!timeStr) return 0;

  // Format "Xh" ou "XhY"
  const hourMatch = timeStr.match(/(\d+)h(?:(\d+))?/);
  if (hourMatch) {
    const hours = parseInt(hourMatch[1]);
    const minutes = hourMatch[2] ? parseInt(hourMatch[2]) : 0;
    return hours * 60 + minutes;
  }

  // Format "X min"
  const minuteMatch = timeStr.match(/(\d+)\s*min/);
  if (minuteMatch) {
    return parseInt(minuteMatch[1]);
  }

  return 0;
};

const formatMinutesToTime = (minutes) => {
  if (!minutes) return "0 min";

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) {
    return `${remainingMinutes} min`;
  }

  // Format hh:mm
  return `${hours}:${remainingMinutes.toString().padStart(2, "0")}`;
};

export const RecipeProvider = ({ children }) => {
  const { unitSystem } = usePreferences();
  
  // État local pour stocker le slug de la recette actuelle
  const [currentRecipeSlug, setCurrentRecipeSlug] = useState(null);
  
  // Utiliser des clés de stockage basées sur le slug
  const getStorageKey = (key) => currentRecipeSlug ? `recipe-${currentRecipeSlug}-${key}` : null;
  
  const [storedCompletedSteps, setStoredCompletedSteps] = useLocalStorage(
    getStorageKey("completed-steps") || "temp-completed-steps",
    {}
  );
  const [storedCompletedSubRecipes, setStoredCompletedSubRecipes] = useLocalStorage(
    getStorageKey("completed-subrecipes") || "temp-completed-subrecipes",
    {}
  );
  
  const [selectedView, setSelectedView] = useState(() => {
    const savedView = localStorage.getItem('selectedView');
    return savedView || 'simple';
  });
  
  const [tools, setTools] = useState([]);

  const [state, dispatch] = useReducer(recipeReducer, {
    ...initialState,
    completedSteps: storedCompletedSteps,
    completedSubRecipes: storedCompletedSubRecipes,
    selectedView,
  });

  // Réinitialiser les étapes complétées quand on change de recette
  useEffect(() => {
    if (currentRecipeSlug) {
      const completedStepsKey = getStorageKey("completed-steps");
      const completedSubRecipesKey = getStorageKey("completed-subrecipes");
      
      const savedCompletedSteps = JSON.parse(localStorage.getItem(completedStepsKey) || "{}");
      const savedCompletedSubRecipes = JSON.parse(localStorage.getItem(completedSubRecipesKey) || "{}");
      
      dispatch({ 
        type: actions.BATCH_UPDATE, 
        payload: {
          completedSteps: savedCompletedSteps,
          completedSubRecipes: savedCompletedSubRecipes
        }
      });
    }
  }, [currentRecipeSlug]);

  // Synchroniser les changements avec le localStorage de manière optimisée
  useEffect(() => {
    if (!currentRecipeSlug) return;
    
    const timeoutId = setTimeout(() => {
      const completedStepsKey = getStorageKey("completed-steps");
      const completedSubRecipesKey = getStorageKey("completed-subrecipes");
      
      localStorage.setItem(completedStepsKey, JSON.stringify(state.completedSteps));
      localStorage.setItem(completedSubRecipesKey, JSON.stringify(state.completedSubRecipes));
      localStorage.setItem('selectedView', state.selectedView);
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [state.completedSteps, state.completedSubRecipes, state.selectedView, currentRecipeSlug]);

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
      console.log('Fetching recipe from URL:', fullUrl);
      
      const response = await fetch(fullUrl);
      
      if (!response.ok) {
        throw new Error(`Recipe not found. Status: ${response.status}`);
      }
      
      const data = await response.json();
      setCurrentRecipeSlug(slug); // Mettre à jour le slug de la recette actuelle
      dispatch({ type: actions.SET_RECIPE, payload: data });
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
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to generate recipe');
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
      const totalSteps = Object.values(subRecipe.steps || {}).length;
      if (totalSteps === 0) return 0;
      
      const completedSteps = Object.values(subRecipe.steps || {})
        .filter(step => state.completedSteps[step.id])
        .length;
      
      return (completedSteps / totalSteps) * 100;
    },
    [state.recipe, state.completedSteps]
  );

  // Fonction utilitaire pour obtenir le nombre total d'étapes complétées
  const getTotalProgress = useCallback(() => {
    if (!state.recipe) return 0;
    const totalSteps = Object.values(state.recipe.subRecipes).reduce((total, subRecipe) => total + (Object.values(subRecipe.steps || {}).length || 0), 0);
    const completedSteps = Object.keys(state.completedSteps || {}).length;
    return totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
  }, [state.recipe, state.completedSteps]);

  // Fonction utilitaire pour obtenir le temps total restant
  const getRemainingTime = useCallback(() => {
    if (!state.recipe?.subRecipes) return 0;

    let totalTime = 0;
    Object.entries(state.recipe.subRecipes).forEach(([id, subRecipe]) => {
      if (subRecipe.steps) {
        Object.values(subRecipe.steps || {}).forEach((step) => {
          if (!state.completedSteps[step.id] && step.time) {
            totalTime += parseTimeToMinutes(step.time);
          }
        });
      }
    });

    return totalTime;
  }, [state.recipe, state.completedSteps]);

  const getSubRecipeRemainingTime = useCallback((subRecipeId) => {
    if (!state.recipe || !state.recipe.subRecipes[subRecipeId]) return 0;
    const subRecipe = state.recipe.subRecipes[subRecipeId];
    return (
      Object.values(subRecipe.steps || {}).reduce((total, step) => {
        if (!step.time || state.completedSteps[step.id]) return total;
        return total + parseTimeToMinutes(step.time);
      }, 0) || 0
    );
  }, [state.recipe, state.completedSteps]);

  const getSubRecipeStats = useCallback((subRecipeId) => {
    const subRecipe = state.recipe?.subRecipes?.[subRecipeId];
    if (!subRecipe) return null;
    
    const totalSteps = Object.keys(subRecipe.steps || {}).length;
    const completedStepsCount = Object.values(subRecipe.steps || {})
      .filter(step => state.completedSteps[step.id])
      .length;
    return { totalSteps, completedStepsCount };
  }, [state.recipe, state.completedSteps]);

  const getCompletedSubRecipesCount = useCallback(() => {
    return Object.entries(state.recipe?.subRecipes || {})
      .filter(([id]) => state.completedSubRecipes[id])
      .length;
  }, [state.recipe, state.completedSubRecipes]);

  const updateServings = useCallback((newServings) => {
    if (!state.recipe) return;
    
    const originalServings = state.recipe.servings;
    const multiplier = newServings / originalServings;
    
    dispatch({
      type: actions.UPDATE_SERVINGS,
      payload: multiplier,
    });
  }, [state.recipe]);

  const getAdjustedAmount = useCallback((amount, unit, category) => {
    if (!state.recipe || !amount) return amount;
    return scaleIngredientAmount(amount, unit, category, state.servingsMultiplier);
  }, [state.recipe, state.servingsMultiplier]);

  const formatAmount = useCallback((amount, unit) => {
    if (!amount && amount !== 0) return '-';
    if (unit && amount === '') return '-';
    if (!unit) return '-';
    
    // Conversion si nécessaire
    if (unitSystem === UNIT_SYSTEMS.IMPERIAL) {
      const { value: convertedAmount, unit: convertedUnit } = convertToImperial(amount, unit);
      amount = convertedAmount;
      unit = convertedUnit;
    }

    // Formatage existant
    let formattedAmount;
    if (amount >= 1000) {
      formattedAmount = (amount / 1000).toFixed(2);
      unit = unit === 'g' ? 'kg' : unit === 'ml' ? 'l' : unit;
    } else {
      formattedAmount = Math.round(amount * 100) / 100;
    }

    // Suppression des zéros inutiles après la virgule
    formattedAmount = Number(formattedAmount).toString();

    // Get the unit from our constants
    const translatedUnit = RECIPE_TEXTS.UNITS[mapUnitToTranslationKey(unit).toUpperCase()] || unit;

    return `${formattedAmount}${translatedUnit ? ' ' + translatedUnit : ''}`;
  }, [unitSystem]);

  const getTotalProgressPercentage = useCallback(() => {
    if (!state.recipe) return 0;
    const totalSteps = Object.values(state.recipe.subRecipes).reduce((total, subRecipe) => total + (Object.values(subRecipe.steps || {}).length || 0), 0);
    const completedSteps = Object.keys(state.completedSteps || {}).length;
    return totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
  }, [state.recipe, state.completedSteps]);

  const isIngredientUnused = useCallback((ingredientId, subRecipeId) => {
    if (!state.recipe) return false;
    const { unusedIngredients } = calculateUnusedItems(state.recipe, state.completedSteps);
    return unusedIngredients.bySubRecipe[subRecipeId] && unusedIngredients.bySubRecipe[subRecipeId][ingredientId] || false;
  }, [state.recipe, state.completedSteps]);

  const isToolUnused = useCallback((toolId) => {
    if (!state.recipe) return false;
    const { unusedTools } = calculateUnusedItems(state.recipe, state.completedSteps);
    return unusedTools[toolId] || false;
  }, [state.recipe, state.completedSteps]);

  const calculateTotalTime = useCallback((recipe) => {
    if (!recipe || !recipe.subRecipes) return '0min';

    let totalMinutes = 0;
    // Iterate over subRecipes object
    Object.values(recipe.subRecipes).forEach(subRecipe => {
      if (!subRecipe.steps) return;
      
      subRecipe.steps.forEach(step => {
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
  }, []);

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
    formatMinutesToTime,
    updateServings,
    getAdjustedAmount,
    formatAmount,
    getRemainingTime,
    getSubRecipeRemainingTime,
    getSubRecipeStats,
    getCompletedSubRecipesCount,
    currentServings: state.recipe ? Math.round((state.recipe.servings || 4) * state.servingsMultiplier) : 0,
    calculateUnusedItems: () => calculateUnusedItems(state.recipe, state.completedSteps),
    getTotalProgress,
    getTotalProgressPercentage,
    isIngredientUnused,
    isToolUnused,
    parseTimeToMinutes,
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
    calculateTotalTime,
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
