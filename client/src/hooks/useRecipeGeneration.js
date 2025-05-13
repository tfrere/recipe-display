import { useReducer, useEffect, useRef } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

// Actions
const actions = {
  START_GENERATION: "START_GENERATION",
  GENERATION_SUCCESS: "GENERATION_SUCCESS",
  GENERATION_ERROR: "GENERATION_ERROR",
  UPDATE_PROGRESS: "UPDATE_PROGRESS",
  GENERATION_COMPLETE: "GENERATION_COMPLETE",
  RESET: "RESET",
};

// Initial state
const initialState = {
  isLoading: false,
  error: null,
  success: false,
  progressId: null,
  progress: null,
  loadingMessage: null,
};

// Reducer
function reducer(state, action) {
  switch (action.type) {
    case actions.START_GENERATION:
      return {
        ...state,
        isLoading: true,
        error: null,
        loadingMessage: "Starting generation...",
      };
    case actions.GENERATION_SUCCESS:
      return {
        ...state,
        isLoading: true,
        progressId: action.payload.progressId,
        progress: {
          id: action.payload.progressId,
          status: "in_progress",
          steps: [],
          currentStep: null,
          createdAt: new Date().toISOString(),
        },
        loadingMessage: "Generation started...",
      };
    case actions.GENERATION_ERROR:
      return {
        ...initialState,
        error: action.payload,
      };
    case actions.UPDATE_PROGRESS:
      return {
        ...state,
        progress: action.payload,
        loadingMessage: `Step ${
          action.payload.currentStep || "unknown"
        } in progress...`,
      };
    case actions.GENERATION_COMPLETE:
      return {
        ...initialState,
        success: true,
        loadingMessage: "Generation completed!",
      };
    case actions.RESET:
      return initialState;
    default:
      return state;
  }
}

export function useRecipeGeneration(onRecipeAdded) {
  const navigate = useNavigate();
  const [state, dispatch] = useReducer(reducer, initialState);
  let pollingIntervalRef = useRef(null);

  useEffect(() => {
    const pollProgress = async () => {
      if (!state.progressId) {
        return;
      }

      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/recipes/progress/${state.progressId}`
        );

        if (response.data) {
          console.log(`[Debug] Progress data:`, response.data);
          dispatch({ type: actions.UPDATE_PROGRESS, payload: response.data });

          // Vérifier si une erreur s'est produite durant la progression
          if (response.data.status === "error") {
            console.error(
              `[Error] Recipe generation failed:`,
              response.data.error
            );

            // Arrêter le polling
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }

            // Dispatch l'erreur
            dispatch({
              type: actions.GENERATION_ERROR,
              payload:
                response.data.error ||
                "Une erreur est survenue lors de la génération de la recette",
            });

            return;
          }

          if (response.data.status === "completed") {
            console.log(
              `[Debug] Recipe generation completed. Full response:`,
              JSON.stringify(response.data)
            );

            // Essayer de récupérer le slug de plusieurs manières possibles
            let recipeSlug = null;

            // 1. Essayer de récupérer depuis la structure metadata standard
            if (response.data.recipe?.metadata?.slug) {
              recipeSlug = response.data.recipe.metadata.slug;
              console.log(
                `[Debug] Recipe slug found in metadata: ${recipeSlug}`
              );
            }
            // 2. Essayer de récupérer depuis result.slug si disponible
            else if (response.data.result?.slug) {
              recipeSlug = response.data.result.slug;
              console.log(`[Debug] Recipe slug found in result: ${recipeSlug}`);
            }
            // 3. Essayer d'extraire d'un autre endroit si nécessaire (custom)
            else if (response.data.recipe?.slug) {
              recipeSlug = response.data.recipe.slug;
              console.log(
                `[Debug] Recipe slug found directly in recipe: ${recipeSlug}`
              );
            }

            if (recipeSlug) {
              // Clear polling interval first
              if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
              }

              // Set success state immediately
              dispatch({ type: actions.GENERATION_COMPLETE });

              // Call onRecipeAdded callback
              if (onRecipeAdded) {
                onRecipeAdded();
              }

              // Add a short delay before navigation to allow modal to close
              setTimeout(() => {
                // Navigate to the new recipe
                navigate(`/recipe/${recipeSlug}`);

                // Reset states
                dispatch({ type: actions.RESET });
              }, 100);
            } else {
              console.error(
                "[Error] Recipe generation is marked as completed but no slug was found:",
                response.data
              );
              // La génération est terminée mais nous n'avons pas de slug
              if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
              }

              // Set success state immediately
              dispatch({ type: actions.GENERATION_COMPLETE });

              // Puisque le serveur indique que la génération est terminée,
              // considérons cela comme un succès et retournons à la page d'accueil
              if (onRecipeAdded) {
                onRecipeAdded();
              }

              // Notification simple via console
              console.log("Recette importée avec succès!");

              // Add a short delay before navigation
              setTimeout(() => {
                // Naviguer vers la page d'accueil
                navigate("/");

                // Reset states
                dispatch({ type: actions.RESET });
              }, 100);
            }
          }
        }
      } catch (error) {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        dispatch({
          type: actions.GENERATION_ERROR,
          payload: "Could not fetch progress",
        });
      }
    };

    if (state.progressId) {
      pollProgress();
      pollingIntervalRef.current = setInterval(pollProgress, 500);
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [state.progressId, onRecipeAdded, navigate]);

  const reset = () => {
    // Clear any ongoing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    // Reset all states
    dispatch({ type: actions.RESET });
  };

  const generateRecipe = async (data) => {
    dispatch({ type: actions.START_GENERATION });

    try {
      const response = await axios.post(`${API_BASE_URL}/api/recipes`, data);

      const progressId = response.data?.progressId;
      if (!progressId) {
        throw new Error("Aucun ID de progression reçu");
      }

      dispatch({
        type: actions.GENERATION_SUCCESS,
        payload: {
          progressId,
          type: data.type,
        },
      });
    } catch (error) {
      if (error.response?.status === 409) {
        dispatch({
          type: actions.GENERATION_ERROR,
          payload: error.response.data?.detail || "Cette recette existe déjà",
        });
        return;
      }

      dispatch({
        type: actions.GENERATION_ERROR,
        payload:
          error.response?.data?.detail ||
          error.message ||
          "Impossible de démarrer la génération",
      });
    }
  };

  return {
    isLoading: state.isLoading,
    error: state.error,
    success: state.success,
    progress: state.progress,
    loadingMessage: state.loadingMessage,
    generateRecipe,
    reset,
  };
}
