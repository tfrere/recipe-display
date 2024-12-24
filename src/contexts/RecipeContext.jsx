import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
} from "react";
import useLocalStorage from "../hooks/useLocalStorage";

const RecipeContext = createContext();

const initialState = {
  recipe: null,
  selectedSubRecipe: null,
  completedSteps: {},
  completedSubRecipes: {},
  unusedIngredients: {},
  unusedTools: {},
  unusedStates: new Set(),
  loading: false,
  error: null,
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
};

// Fonction utilitaire pour calculer les éléments non utilisés
const calculateUnusedItems = (recipe, completedSteps, selectedSubRecipeId) => {
  const unusedIngredients = {};
  const unusedTools = {};
  const unusedStates = new Set();

  // Ne traiter que la sous-recette sélectionnée
  const subRecipe = recipe.subRecipes[selectedSubRecipeId];
  if (!subRecipe) return { unusedIngredients, unusedTools, unusedStates };

  // Construire un graphe de dépendances
  const graph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses successeurs)
  const reverseGraph = new Map(); // Map<nodeId, Set<nodeId>> (nodeId -> ses prédécesseurs)

  // Initialiser les ensembles pour chaque nœud
  subRecipe.steps.forEach((step) => {
    graph.set(step.id, new Set());
    reverseGraph.set(step.id, new Set());

    // Ajouter les liens pour les inputs
    step.inputs.forEach((input) => {
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
  subRecipe.steps.forEach((step) => {
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
            return subRecipe.steps.some(
              (s) => s.id === successorId && !completedSteps[s.id]
            );
          }
        );

        if (!isUsedLater) {
          if (currentId.startsWith("ingredient-")) {
            unusedIngredients[currentId.replace("ingredient-", "")] = true;
          } else if (currentId.startsWith("tool-")) {
            unusedTools[currentId.replace("tool-", "")] = true;
          } else {
            // Si ce n'est ni un ingrédient ni un outil, c'est un état
            const isState = subRecipe.steps.some(
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

  return { unusedIngredients, unusedTools, unusedStates };
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
        unusedIngredients: {},
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
        subRecipe.steps.forEach((step) => {
          reverseGraph.set(step.id, new Set());

          // Ajouter les liens pour les inputs de type "state"
          step.inputs
            .filter((input) => input.type === "state")
            .forEach((input) => {
              // Trouver l'étape qui produit cet état
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
        calculateUnusedItems(
          state.recipe,
          newCompletedSteps,
          state.selectedSubRecipe
        );

      // Vérifier si toutes les étapes de la sous-recette sont complétées
      const allStepsCompleted = subRecipe.steps.every(
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
      subRecipe.steps.forEach((step) => {
        newCompletedSteps[step.id] = completed;
      });

      // Calculer les éléments non utilisés après la mise à jour
      const { unusedIngredients, unusedTools, unusedStates } =
        calculateUnusedItems(
          state.recipe,
          newCompletedSteps,
          state.selectedSubRecipe
        );

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
  const [storedCompletedSteps, setStoredCompletedSteps] = useLocalStorage(
    "recipe-completed-steps",
    {}
  );
  const [storedCompletedSubRecipes, setStoredCompletedSubRecipes] =
    useLocalStorage("recipe-completed-subrecipes", {});

  const [state, dispatch] = useReducer(recipeReducer, {
    ...initialState,
    completedSteps: storedCompletedSteps,
    completedSubRecipes: storedCompletedSubRecipes,
  });

  // Synchroniser les changements avec le localStorage de manière optimisée
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setStoredCompletedSteps(state.completedSteps);
      setStoredCompletedSubRecipes(state.completedSubRecipes);
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [state.completedSteps, state.completedSubRecipes]);

  const loadRecipe = useCallback(async (recipeFile) => {
    dispatch({ type: actions.SET_LOADING, payload: true });
    try {
      const response = await fetch(recipeFile);
      const data = await response.json();
      dispatch({ type: actions.SET_RECIPE, payload: data });
      dispatch({ type: actions.SET_ERROR, payload: null });
    } catch (error) {
      console.error("Error loading recipe:", error);
      dispatch({ type: actions.SET_ERROR, payload: error.message });
    } finally {
      dispatch({ type: actions.SET_LOADING, payload: false });
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
      if (!state.recipe?.subRecipes[subRecipeId]?.steps)
        return { completed: 0, total: 0 };

      const steps = state.recipe.subRecipes[subRecipeId].steps;
      const completed = steps.filter(
        (step) => state.completedSteps[step.id]
      ).length;

      return {
        completed,
        total: steps.length,
      };
    },
    [state.recipe, state.completedSteps]
  );

  // Fonction utilitaire pour obtenir le nombre total d'étapes complétées
  const getTotalProgress = useCallback(() => {
    if (!state.recipe?.subRecipes) return { completed: 0, total: 0 };

    let totalCompleted = 0;
    let totalSteps = 0;

    Object.values(state.recipe.subRecipes).forEach((subRecipe) => {
      if (subRecipe.steps) {
        totalSteps += subRecipe.steps.length;
        totalCompleted += subRecipe.steps.filter(
          (step) => state.completedSteps[step.id]
        ).length;
      }
    });

    return {
      completed: totalCompleted,
      total: totalSteps,
    };
  }, [state.recipe, state.completedSteps]);

  // Fonction utilitaire pour obtenir le temps total restant
  const getRemainingTime = useCallback(() => {
    if (!state.recipe?.subRecipes) return 0;

    let totalTime = 0;
    Object.entries(state.recipe.subRecipes).forEach(([id, subRecipe]) => {
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

  const getSubRecipeRemainingTime = (subRecipeId) => {
    if (!state.recipe || !state.recipe.subRecipes[subRecipeId]) return 0;
    const subRecipe = state.recipe.subRecipes[subRecipeId];
    return (
      subRecipe.steps?.reduce((total, step) => {
        if (!step.time || state.completedSteps[step.id]) return total;
        return total + parseTimeToMinutes(step.time);
      }, 0) || 0
    );
  };

  const value = React.useMemo(
    () => ({
      ...state,
      dispatch,
      actions,
      loadRecipe,
      setSelectedSubRecipe,
      toggleStepCompletion,
      toggleSubRecipeCompletion,
      getSubRecipeProgress,
      getTotalProgress,
      getRemainingTime,
      parseTimeToMinutes,
      formatMinutesToTime,
      isIngredientUnused: (ingredientId) =>
        state.unusedIngredients[ingredientId],
      isToolUnused: (toolId) => state.unusedTools[toolId],
      getUnusedIngredients: () => Object.keys(state.unusedIngredients),
      getUnusedTools: () => Object.keys(state.unusedTools),
      calculateUnusedItems: () =>
        calculateUnusedItems(
          state.recipe,
          state.completedSteps,
          state.selectedSubRecipe
        ),
      getSubRecipeRemainingTime,
    }),
    [
      state,
      loadRecipe,
      setSelectedSubRecipe,
      toggleStepCompletion,
      toggleSubRecipeCompletion,
      getSubRecipeProgress,
      getTotalProgress,
      getRemainingTime,
      getSubRecipeRemainingTime,
    ]
  );

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
