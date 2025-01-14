import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { useNavigate } from "react-router-dom";
import { usePreferences } from "./PreferencesContext";
import { useTheme } from "./ThemeContext";
import { useConstants } from "./ConstantsContext";
import { getRecipes } from "../services/recipeService";
import useCheatCode from "../hooks/useCheatCode";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

const RecipeListContext = createContext();

export const useRecipeList = () => {
  const context = useContext(RecipeListContext);
  if (!context) {
    throw new Error("useRecipeList must be used within a RecipeListProvider");
  }
  return context;
};

// État initial pour le chargement
const initialLoadingState = {
  recipes: false,
  images: new Map(),
  filters: false,
  error: null,
};

const normalizeText = (text) => {
  if (!text) return "";
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
};

export const RecipeListProvider = ({ children }) => {
  const { constants } = useConstants();
  const { sortByCategory } = usePreferences();
  const { hasPrivateAccess } = useCheatCode();
  const DEBUG = false; // Flag pour activer/désactiver les logs de débogage
  const seasonalRecipesOrder = useRef(new Map());

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  // État des recettes
  const [allRecipes, setAllRecipes] = useState([]);
  const [loadingState, setLoadingState] = useState(initialLoadingState);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDiet, setSelectedDiet] = useState(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [selectedDishType, setSelectedDishType] = useState(null);
  const [isQuickOnly, setIsQuickOnly] = useState(false);
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);

  // Précharger une image
  const preloadImage = useCallback((slug) => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        setLoadingState((prev) => ({
          ...prev,
          images: new Map(prev.images).set(slug, true),
        }));
        resolve();
      };
      img.onerror = () => {
        setLoadingState((prev) => ({
          ...prev,
          images: new Map(prev.images).set(slug, true), // On considère comme chargé même en cas d'erreur
        }));
        resolve();
      };
      img.src = `${API_BASE_URL}/api/images/medium/${slug}`;
    });
  }, []);

  // Charger toutes les recettes et leurs images
  const fetchRecipes = useCallback(async () => {
    setLoadingState((prev) => ({ ...prev, recipes: true, error: null }));
    try {
      const data = await getRecipes(hasPrivateAccess);
      setAllRecipes(data);

      // Précharger les images en parallèle
      const imagePromises = data.map((recipe) => preloadImage(recipe.slug));
      await Promise.all(imagePromises);
    } catch (err) {
      setLoadingState((prev) => ({ ...prev, error: err.message }));
    } finally {
      setLoadingState((prev) => ({
        ...prev,
        recipes: false,
        filters: false,
      }));
    }
  }, [preloadImage, hasPrivateAccess]);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  // État de chargement global
  const isLoading = useMemo(() => {
    return (
      loadingState.recipes ||
      loadingState.filters ||
      (allRecipes.length > 0 &&
        Array.from(loadingState.images.values()).some((status) => !status))
    );
  }, [loadingState, allRecipes]);

  // Indique si toutes les images sont chargées
  const areImagesLoaded = useMemo(() => {
    return (
      allRecipes.length === 0 ||
      (allRecipes.length > 0 &&
        loadingState.images.size === allRecipes.length &&
        Array.from(loadingState.images.values()).every((status) => status))
    );
  }, [allRecipes, loadingState.images]);

  // Déterminer la saison actuelle
  const getCurrentSeason = () => {
    const month = new Date().getMonth();
    if (month >= 2 && month <= 4) return "spring";
    if (month >= 5 && month <= 7) return "summer";
    if (month >= 8 && month <= 10) return "autumn";
    return "winter";
  };

  // Convertisseurs de labels en IDs avec gestion de la casse
  const createLabelToIdMap = useMemo(
    () => (items) => {
      const map = new Map();
      items.forEach((item) => {
        map.set(item.label.toLowerCase(), item.id);
        map.set(item.id.toLowerCase(), item.id);
      });
      return map;
    },
    []
  );

  // Hooks mémorisés pour les convertisseurs
  const labelConverters = useMemo(
    () => ({
      seasonLabelToId: createLabelToIdMap(constants.seasons),
      typeLabelToId: createLabelToIdMap(constants.recipe_types),
    }),
    [createLabelToIdMap, constants]
  );

  // Fonction générique pour filtrer les recettes
  const filterRecipes = useMemo(
    () =>
      (recipes, filters, excludeFilter = null) => {
        if (!recipes) return [];

        if (DEBUG) {
          console.log("Filtering recipes with:", {
            filters,
            excludeFilter,
            recipesCount: recipes.length,
          });
        }

        return recipes.filter((recipe) => {
          // Filtre par régime si actif et non exclu
          if (filters.selectedDiet && excludeFilter !== "diet") {
            if (!recipe.diets?.includes(filters.selectedDiet)) {
              if (DEBUG) {
                console.log("Recipe filtered out by diet:", recipe.title, {
                  recipeDiets: recipe.diets,
                  selectedDiet: filters.selectedDiet,
                });
              }
              return false;
            }
          }

          // Filtre par saison si active et non exclue
          if (filters.selectedSeason && excludeFilter !== "season") {
            // Si la recette est pour toutes les saisons ou si la saison sélectionnée est dans la liste
            if (
              !recipe.seasons?.includes("all") &&
              !recipe.seasons?.includes(filters.selectedSeason)
            ) {
              if (DEBUG) {
                console.log("Recipe filtered out by season:", recipe.title, {
                  recipeSeasons: recipe.seasons,
                  selectedSeason: filters.selectedSeason,
                });
              }
              return false;
            }
          }

          // Filtre par type si actif et non exclu
          if (filters.selectedType && excludeFilter !== "type") {
            if (recipe.recipeType !== filters.selectedType) {
              if (DEBUG) {
                console.log("Recipe filtered out by type:", recipe.title, {
                  recipeType: recipe.recipeType,
                  selectedType: filters.selectedType,
                });
              }
              return false;
            }
          }

          // Filtre par type de plat si actif et non exclu
          if (filters.selectedDishType && excludeFilter !== "dishType") {
            if (recipe.recipeType !== filters.selectedDishType) {
              if (DEBUG) {
                console.log("Recipe filtered out by dish type:", recipe.title, {
                  recipeType: recipe.recipeType,
                  selectedDishType: filters.selectedDishType,
                });
              }
              return false;
            }
          }

          // Filtre rapide si actif et non exclu
          if (filters.isQuickOnly && excludeFilter !== "quick") {
            if (!recipe.quick) {
              if (DEBUG) {
                console.log("Recipe filtered out by quick:", recipe.title);
              }
              return false;
            }
          }

          // Filtre par recherche si active et non exclue
          if (filters.searchQuery && excludeFilter !== "search") {
            const searchTerms = filters.searchQuery
              .toLowerCase()
              .split(" ")
              .map((term) => term.trim())
              .filter((term) => term.length >= 3);

            if (searchTerms.length === 0) return true;

            return searchTerms.every((searchTerm) => {
              const normalizedSearchTerm = normalizeText(searchTerm);

              // Recherche dans le titre, l'auteur et le livre
              const title = normalizeText(recipe.title || "");
              const author = normalizeText(recipe.author || "");
              const bookTitle = normalizeText(recipe.bookTitle || "");
              const description = normalizeText(recipe.description || "");

              // Recherche dans les ingrédients
              const hasIngredient = recipe.ingredients?.some((ingredient) => {
                if (!ingredient?.name) return false;
                const ingredientText = normalizeText(ingredient.name);
                return ingredientText.includes(normalizedSearchTerm);
              });

              // Recherche dans les notes
              const hasNoteMatch =
                recipe.notes?.some((note) => {
                  if (!note) return false;
                  const normalizedNote = normalizeText(note);
                  return normalizedNote.includes(normalizedSearchTerm);
                }) || false;

              const matches =
                title.includes(normalizedSearchTerm) ||
                author.includes(normalizedSearchTerm) ||
                bookTitle.includes(normalizedSearchTerm) ||
                description.includes(normalizedSearchTerm) ||
                hasIngredient ||
                hasNoteMatch;

              if (!matches) {
                if (DEBUG) {
                  console.log("Recipe filtered out by search:", recipe.title);
                }
              }

              return matches;
            });
          }

          return true;
        });
      },
    [normalizeText]
  );

  // Fonction pour calculer les statistiques
  const computeStats = useMemo(
    () => (recipes, currentFilters) => {
      if (!recipes || recipes.length === 0) {
        return {
          diet: constants.diets.map((diet) => ({ key: diet.id, count: 0 })),
          season: constants.seasons.map((season) => ({
            key: season.id,
            count: 0,
          })),
          dishType: constants.recipe_types.map((type) => ({
            key: type.id,
            count: 0,
          })),
          quick: { count: 0, total: 0 },
        };
      }

      const stats = {
        type: new Map(),
        diet: new Map(),
        season: new Map(),
      };

      // Initialiser les compteurs
      constants.recipe_types.forEach((type) => stats.type.set(type.id, 0));
      constants.diets.forEach((diet) => stats.diet.set(diet.id, 0));
      constants.seasons.forEach((season) => stats.season.set(season.id, 0));

      // Compter les recettes en excluant le filtre en cours
      recipes.forEach((recipe) => {
        // Pour chaque type de filtre, on compte seulement si la recette passe les autres filtres
        const countForDiet =
          filterRecipes(
            [recipe],
            { ...currentFilters, selectedDiet: null },
            "diet"
          ).length > 0;
        const countForSeason =
          filterRecipes(
            [recipe],
            { ...currentFilters, selectedSeason: null },
            "season"
          ).length > 0;
        const countForType =
          filterRecipes(
            [recipe],
            { ...currentFilters, selectedDishType: null },
            "dishType"
          ).length > 0;

        if (countForDiet && recipe.diets) {
          // Pour chaque régime de la recette
          recipe.diets.forEach((diet) => {
            stats.diet.set(diet, (stats.diet.get(diet) || 0) + 1);
          });
        }

        if (countForSeason && recipe.seasons) {
          // Pour chaque saison de la recette
          recipe.seasons.forEach((season) => {
            stats.season.set(season, (stats.season.get(season) || 0) + 1);
          });
        }

        if (countForType) {
          stats.type.set(
            recipe.recipeType,
            (stats.type.get(recipe.recipeType) || 0) + 1
          );
        }
      });

      const mapToArray = (map, items) =>
        items.map((item) => ({
          key: item.id,
          count: map.get(item.id) || 0,
        }));

      const quickRecipes = filterRecipes(
        recipes,
        { ...currentFilters, isQuickOnly: null },
        "quick"
      ).filter((recipe) => recipe.quick);

      return {
        diet: mapToArray(stats.diet, constants.diets),
        season: mapToArray(stats.season, constants.seasons),
        dishType: mapToArray(stats.type, constants.recipe_types),
        quick: {
          count: quickRecipes.length,
          total: recipes.length,
        },
      };
    },
    [filterRecipes, constants]
  );

  // Mémoriser les filtres actuels
  const currentFilters = useMemo(
    () => ({
      searchQuery,
      selectedDiet,
      selectedDifficulty,
      selectedSeason,
      selectedType,
      selectedDishType,
      isQuickOnly,
    }),
    [
      searchQuery,
      selectedDiet,
      selectedDifficulty,
      selectedSeason,
      selectedType,
      selectedDishType,
      isQuickOnly,
    ]
  );

  // Mémoriser les recettes filtrées
  const filteredRecipes = useMemo(() => {
    if (DEBUG) {
      console.log("Filtering recipes with filters:", {
        searchQuery,
        selectedDiet,
        selectedDifficulty,
        selectedSeason,
        selectedType,
        selectedDishType,
        isQuickOnly,
        totalRecipes: allRecipes.length,
      });
    }

    // Si aucun filtre n'est actif, afficher les recettes de la saison en cours de manière aléatoire
    if (
      !searchQuery &&
      !selectedDiet &&
      !selectedDifficulty &&
      !selectedSeason &&
      !selectedType &&
      !selectedDishType &&
      !isQuickOnly
    ) {
      const currentSeason = getCurrentSeason();

      // Ne garder que les recettes de la saison actuelle
      const currentSeasonRecipes = allRecipes.filter((recipe) => {
        const matches =
          recipe.seasons?.includes(currentSeason) ||
          recipe.seasons?.includes("all");
        if (!matches) {
          if (DEBUG) {
            console.log(
              "Recipe filtered out by current season:",
              recipe.title,
              {
                recipeSeasons: recipe.seasons,
                currentSeason,
              }
            );
          }
        }
        return matches;
      });

      // Vérifier si on a déjà un ordre pour cette saison
      if (!seasonalRecipesOrder.current.has(currentSeason)) {
        // Si non, créer un nouvel ordre aléatoire
        const order = [...currentSeasonRecipes]
          .sort(() => Math.random() - 0.5)
          .map((recipe) => recipe.id);
        seasonalRecipesOrder.current.set(currentSeason, order);
      }

      // Utiliser l'ordre mémorisé
      const order = seasonalRecipesOrder.current.get(currentSeason);
      const orderedRecipes = [...currentSeasonRecipes].sort((a, b) => {
        const indexA = order.indexOf(a.id);
        const indexB = order.indexOf(b.id);
        return indexA - indexB;
      });

      if (DEBUG) {
        console.log("Selected recipes for current season:", {
          currentSeason,
          fromCurrentSeason: orderedRecipes.length,
          titles: orderedRecipes.map((r) => r.title),
        });
      }

      return orderedRecipes;
    }

    // Sinon, appliquer les filtres normalement
    const filtered = filterRecipes(allRecipes, currentFilters);
    if (DEBUG) {
      console.log("Filtered recipes:", {
        count: filtered.length,
        titles: filtered.map((r) => r.title),
      });
    }
    return filtered;
  }, [
    allRecipes,
    currentFilters,
    filterRecipes,
    searchQuery,
    selectedDiet,
    selectedDifficulty,
    selectedSeason,
    selectedType,
    selectedDishType,
    isQuickOnly,
    getCurrentSeason,
  ]);

  // Calculer les stats
  const stats = useMemo(() => {
    return computeStats(allRecipes, currentFilters);
  }, [allRecipes, currentFilters, computeStats]);

  // Mémoriser la valeur du contexte
  const value = useMemo(
    () => ({
      allRecipes,
      loadingState,
      error: loadingState.error,
      filteredRecipes,
      searchQuery,
      setSearchQuery,
      selectedDiet,
      setSelectedDiet,
      selectedDifficulty,
      setSelectedDifficulty,
      selectedSeason,
      setSelectedSeason,
      selectedType,
      setSelectedType,
      selectedDishType,
      setSelectedDishType,
      isQuickOnly,
      setIsQuickOnly,
      isAddRecipeModalOpen,
      setIsAddRecipeModalOpen,
      fetchRecipes,
      getCurrentSeason,
      stats,
      resultsType:
        !searchQuery &&
        !selectedDiet &&
        !selectedDifficulty &&
        !selectedSeason &&
        !selectedType &&
        !selectedDishType &&
        !isQuickOnly
          ? "random_seasonal"
          : "filtered",
      openAddRecipeModal: () => setIsAddRecipeModalOpen(true),
      closeAddRecipeModal: () => setIsAddRecipeModalOpen(false),
      resetFilters: () => {
        setSearchQuery("");
        setSelectedDiet(null);
        setSelectedSeason(null);
        setSelectedType(null);
        setSelectedDishType(null);
        setIsQuickOnly(false);
      },
    }),
    [
      allRecipes,
      loadingState,
      filteredRecipes,
      searchQuery,
      selectedDiet,
      selectedDifficulty,
      selectedSeason,
      selectedType,
      selectedDishType,
      isQuickOnly,
      isAddRecipeModalOpen,
      stats,
    ]
  );

  return (
    <RecipeListContext.Provider value={value}>
      {children}
    </RecipeListContext.Provider>
  );
};

export default RecipeListProvider;
