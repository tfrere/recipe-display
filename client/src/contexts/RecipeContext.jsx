import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useReducer,
  useCallback,
  useMemo,
} from "react";
import { useConstants } from "./ConstantsContext";
import useLocalStorage from "../hooks/useLocalStorage";
import {
  scaleIngredientAmount,
  getFractionDisplay,
} from "../utils/ingredientScaling";
import { normalizeAmount } from "../utils/unitNormalization";
import { mapUnitToTranslationKey } from "../utils/unitMapping";
import { parseTimeToMinutes, formatTimeCompact } from "../utils/timeUtils";

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

// Fonction utilitaire pour extraire les outils des steps
const extractToolsFromSteps = (recipe) => {
  const toolsSet = new Set();

  // Also add recipe-level tools
  if (recipe.tools && Array.isArray(recipe.tools)) {
    recipe.tools.forEach((tool) => toolsSet.add(tool));
  }

  // Parcourir toutes les sous-recettes
  (recipe.subRecipes || []).forEach((subRecipe) => {
    // Parcourir toutes les étapes de la sous-recette
    (subRecipe.steps || []).forEach((step) => {
      // requires[] contains tool names
      (step.requires || []).forEach((tool) => toolsSet.add(tool));
      // tools[] contains tool names
      (step.tools || []).forEach((tool) => toolsSet.add(tool));
    });
  });

  // Convertir l'ensemble en tableau et créer les objets d'outils
  return Array.from(toolsSet).map((toolName) => ({
    id: toolName.toLowerCase().replace(/\s+/g, "-"),
    name: toolName,
  }));
};

// Transforme une recette (uses/produces) en format subRecipes interne
const transformToSubRecipes = (recipe) => {

  const ingredientsMap = {};
  (recipe.ingredients || []).forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  // Build set of all produced state IDs for distinguishing ingredients vs states in "uses"
  const producedStates = new Set();
  (recipe.steps || []).forEach((step) => {
    if (step.produces) {
      producedStates.add(step.produces);
    }
  });

  // Helper: transform a single step to internal format
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

  // Group steps by subRecipe field
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

  // Build subRecipes array, one per group
  const subRecipes = groupOrder.map((groupName) => {
    const groupSteps = stepsByGroup[groupName];
    const transformedSteps = groupSteps.map(transformStep);

    // Collect ingredients used in this sub-recipe's steps
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

    // Capitalize group name for display
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

// Transforme une recette du format steps vers le format subRecipes
const transformStepsToSubRecipes = (recipe) => {
  if (recipe.subRecipes) {
    return recipe;
  }

  if (!recipe.steps || !Array.isArray(recipe.steps)) {
    console.error("La recette ne contient pas de steps à transformer");
    return recipe;
  }

  return transformToSubRecipes(recipe);
};

// Fonction pour vérifier et corriger les quantités des ingrédients
const correctIngredientAmounts = (recipe) => {
  if (!recipe || !recipe.subRecipes || !recipe.ingredients) {
    return recipe;
  }

  // Créer une map des ingrédients originaux avec leurs unités
  const ingredientsMap = {};
  recipe.ingredients.forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  // Vérifier et corriger les ingrédients de chaque sous-recette
  const correctedSubRecipes = recipe.subRecipes.map((subRecipe) => {
    if (!Array.isArray(subRecipe.ingredients)) {
      return subRecipe;
    }

    // Corriger les ingrédients
    const correctedIngredients = subRecipe.ingredients.map((ing) => {
      const originalIngredient = ingredientsMap[ing.ref];
      if (!originalIngredient) {
        return ing;
      }

      // Assurons-nous que les quantités sont numériques
      let amount = parseFloat(ing.amount);
      if (isNaN(amount)) {
        amount = 0;
      }

      // Déterminer l'unité à utiliser
      // null = item comptable (2 échalotes, 1 feuille de laurier) — on ne devine PAS
      let unit = ing.unit || originalIngredient.unit || null;

      // Créer un ingrédient corrigé avec toutes les informations nécessaires
      const correctedIngredient = {
        ...ing,
        amount,
        // S'assurer que l'unité est présente (prendre celle de l'ingrédient original si nécessaire)
        unit,
        // S'assurer que la catégorie est présente
        category: ing.category || originalIngredient.category,
        // Conserver le nom pour faciliter le débogage et l'identification
        name: originalIngredient.name,
      };

      return correctedIngredient;
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

// Reducer
const recipeReducer = (state, action) => {
  switch (action.type) {
    case actions.SET_RECIPE:
      const recipeServings = action.payload?.metadata?.servings || 4;
      // Vérifier si la recette a besoin d'être transformée (format avec steps)
      const transformedRecipe =
        action.payload.steps && !action.payload.subRecipes
          ? transformStepsToSubRecipes(action.payload)
          : action.payload;

      const safeSubRecipes = transformedRecipe.subRecipes || [];

      // Préfixer les IDs des steps avec leur subRecipeId et vérifier les quantités des ingrédients
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
      const subRecipe = (state.recipe?.subRecipes || []).find(
        (sr) => sr.id === subRecipeId
      );

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
        (subRecipe.steps || []).forEach((step) => {
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

      if (!subRecipe?.steps) {
        return state;
      }

      // Mettre à jour toutes les étapes de la sous-recette
      const newCompletedSteps = { ...state.completedSteps };
      (subRecipe.steps || []).forEach((step) => {
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
      return {
        ...state,
        completedSteps: {},
        completedSubRecipes: {},
      };

    case actions.RESET_SERVINGS:
      const originalServings = state.recipe?.metadata?.servings || 4;
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
  const [state, dispatch] = useReducer(recipeReducer, initialState);
  // Définir unitSystem directement comme "metric" au lieu d'utiliser useLocalStorage
  const unitSystem = "metric";

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

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

  const UNIT_CONVERSIONS = {
    // Ajouter vos conversions d'unités ici si nécessaire
  };

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
      if (!state.recipe || !state.recipe.subRecipes) return 0;
      const subRecipe = state.recipe.subRecipes.find((sr) => sr.id === subRecipeId);
      if (!subRecipe) return 0;
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
      setCurrentRecipeSlug(slug); // Mettre à jour le slug de la recette actuelle
      dispatch({ type: actions.SET_RECIPE, payload: recipe });
      dispatch({ type: actions.SET_ERROR, payload: null });
      return recipe; // Retourner la recette pour permettre l'enchaînement de promesses
    } catch (error) {
      console.error("Error loading recipe:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
      throw error; // Propager l'erreur pour permettre la gestion dans .catch()
    } finally {
      dispatch({ type: actions.SET_LOADING, payload: false });
    }
  }, []);

  // Fonction pour charger directement une recette au format avec steps
  const loadRecipeWithSteps = useCallback(async (recipeData) => {
    dispatch({ type: actions.SET_LOADING, payload: true });
    try {
      if (!recipeData.steps) {
        throw new Error("La recette fournie ne contient pas de steps");
      }

      // Utilisera automatiquement le transformateur dans le reducer
      dispatch({ type: actions.SET_RECIPE, payload: recipeData });
      dispatch({ type: actions.SET_ERROR, payload: null });

      // Définir le slug si présent
      if (recipeData.metadata?.slug) {
        setCurrentRecipeSlug(recipeData.metadata.slug);
      }
    } catch (error) {
      console.error("Error loading recipe with steps:", error);
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
      const subRecipe = (state.recipe?.subRecipes || []).find(
        (sr) => sr.id === subRecipeId
      );
      if (!subRecipe) return 0;
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

      // Convertir en nombre si c'est une chaîne
      const numericAmount =
        typeof amount === "string" ? parseFloat(amount) : amount;

      if (isNaN(numericAmount)) {
        console.warn(`Quantité invalide: ${amount}`);
        return amount;
      }

      // Appliquer le multiplicateur de portions
      const scaledAmount = scaleIngredientAmount(
        numericAmount,
        unit,
        category,
        state.servingsMultiplier,
        constants
      );

      return scaledAmount;
    },
    [state.recipe, state.servingsMultiplier, constants]
  );

  const formatAmount = useCallback(
    (amount, unit) => {
      // Null, undefined, empty string, or zero → dash (ingredient "to taste")
      if (amount == null || amount === "" || amount === 0) return "-";

      // Si pas d'unité, essayer de faire au mieux
      if (!unit) {
        // Pour les nombres entiers ou très proches d'entiers, les afficher tels quels
        if (Math.abs(Math.round(amount) - amount) < 0.01) {
          return Math.round(amount).toString();
        }
        // Pour les fractions, tenter de les formater comme telles
        return amount.toString();
      }

      // Conversion impériale désactivée, toujours utiliser le système métrique
      // Formatage existant
      let formattedAmount;
      if (amount >= 1000 && (unit === "g" || unit === "ml")) {
        formattedAmount = (amount / 1000).toFixed(2);
        unit = unit === "g" ? "kg" : unit === "ml" ? "l" : unit;
      } else {
        formattedAmount = Math.round(amount * 100) / 100;
      }

      // Suppression des zéros inutiles après la virgule
      formattedAmount = Number(formattedAmount).toString();

      // Obtenir l'unité traduite si disponible
      let translatedUnit = unit;
      try {
        // Normaliser l'unité pour la recherche dans UNITS
        const normalizedUnit = mapUnitToTranslationKey(unit).toUpperCase();
        if (UNITS[normalizedUnit]) {
          translatedUnit = UNITS[normalizedUnit];
        }
      } catch (e) {
        console.warn(`Erreur lors de la traduction de l'unité ${unit}:`, e);
      }

      // S'assurer que l'unité est bien jointe au montant avec un espace
      return `${formattedAmount}${translatedUnit ? " " + translatedUnit : ""}`;
    },
    [UNITS]
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

  // Fonction pour normaliser l'accès aux ingrédients des sous-recettes
  const getSubRecipeIngredients = useCallback(
    (subRecipeId) => {
      if (!state.recipe?.subRecipes) return [];

      const subRecipe = state.recipe.subRecipes.find(
        (sr) => sr.id === subRecipeId
      );

      if (!subRecipe) return [];

      // Si la sous-recette a une propriété "ingredients"
      if (Array.isArray(subRecipe.ingredients)) {
        return subRecipe.ingredients
          .map((ingredient) => {
            // Trouver l'ingrédient original dans la liste principale
            const originalIngredient = state.recipe.ingredients.find(
              (ing) => ing.id === ingredient.ref
            );

            if (!originalIngredient) {
              console.warn(`Ingredient ${ingredient.ref} not found in recipe`);
              return null;
            }

            // Vérifier la quantité et l'unité
            const amount = parseFloat(ingredient.amount);
            if (isNaN(amount)) {
              console.warn(
                `Quantité invalide pour l'ingrédient ${ingredient.ref}: ${ingredient.amount}`
              );
            }

            // Déterminer l'unité à utiliser
            // 1. Priorité à l'unité définie dans l'ingrédient de la sous-recette
            let unit = ingredient.unit;

            // 2. Si pas d'unité, utiliser celle de l'ingrédient original
            if (!unit) {
              unit = originalIngredient.unit;
            }

            // null = item comptable (2 échalotes, 1 feuille de laurier) — on ne devine PAS

            // Créer un objet ingrédient complet avec les informations des deux sources
            return {
              ...originalIngredient,
              amount: amount,
              inputType: ingredient.inputType,
              type: ingredient.type,
              unit: unit,
              category: ingredient.category || originalIngredient.category,
              subRecipeId,
            };
          })
          .filter(Boolean);
      }

      // Si la sous-recette n'a pas d'ingrédients, retourner une liste vide
      return [];
    },
    [state.recipe]
  );

  // Fonction pour formater un ingrédient du format step
  const formatStepIngredient = useCallback(
    (ingredient, subRecipeId) => {
      if (!ingredient || !state.recipe) return null;

      // Trouver l'ingrédient original
      const originalIngredient = state.recipe.ingredients.find(
        (ing) => ing.id === (ingredient.ref_id || ingredient.ref)
      );

      if (!originalIngredient) return null;

      // Calculer la quantité ajustée avec le multiplicateur de portions
      const adjustedAmount = getAdjustedAmount(
        ingredient.amount,
        originalIngredient.unit,
        originalIngredient.category
      );

      // Formater la quantité pour l'affichage
      const formattedAmount = formatAmount(
        adjustedAmount,
        originalIngredient.unit
      );

      return {
        ...originalIngredient,
        amount: adjustedAmount,
        formattedAmount,
        subRecipeId,
      };
    },
    [state.recipe, getAdjustedAmount, formatAmount]
  );

  // Fonction pour obtenir les ingrédients d'une sous-recette avec quantités formatées
  const getFormattedSubRecipeIngredients = useCallback(
    (subRecipeId) => {
      const ingredients = getSubRecipeIngredients(subRecipeId);

      return ingredients
        .map((ingredient) => {
          try {
            // Vérification des données nécessaires
            if (!ingredient) {
              console.warn(
                `Ingrédient null trouvé dans la sous-recette ${subRecipeId}`
              );
              return null;
            }

            // Assurons-nous que la quantité est un nombre
            let amount = parseFloat(ingredient.amount);
            if (isNaN(amount)) {
              console.warn(
                `Quantité invalide pour l'ingrédient ${ingredient.id} (${ingredient.name}): ${ingredient.amount}`
              );
              amount = 0;
            }

            // null = item comptable (2 échalotes, 1 feuille de laurier) — on ne devine PAS
            let unit = ingredient.unit || null;

            // Calculer la quantité ajustée avec le multiplicateur de portions
            const adjustedAmount = getAdjustedAmount(
              amount,
              unit,
              ingredient.category
            );

            // Formater la quantité pour l'affichage avec l'unité
            const formattedAmount = formatAmount(adjustedAmount, unit);

            return {
              ...ingredient,
              amount: adjustedAmount,
              formattedAmount: formattedAmount,
              unit,
              _initialAmount: amount,
              _unit: unit,
            };
          } catch (error) {
            console.error(
              `Erreur lors du formatage de l'ingrédient ${
                ingredient?.id || "inconnu"
              }:`,
              error,
              ingredient
            );

            // Retourner une version minimale utilisable en cas d'erreur
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
    [
      getSubRecipeIngredients,
      getAdjustedAmount,
      formatAmount,
      state.servingsMultiplier,
    ]
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
        if (!state.recipe || !state.recipe.subRecipes) return 0;
        const subRecipe = state.recipe.subRecipes.find((sr) => sr.id === subRecipeId);
        if (!subRecipe) return 0;
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
