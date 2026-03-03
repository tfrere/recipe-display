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
import { useTheme } from "./ThemeContext";
import { useConstants } from "./ConstantsContext";
import { usePantry } from "./PantryContext";
import { getRecipes } from "../services/recipeService";
import useLongPress, { PRIVATE_ACCESS_CHANGED } from "../hooks/useLongPress";
import { getCurrentSeason } from "../utils/seasonUtils";

const FILTERS_STORAGE_KEY = "recipe-list-filters";

const DEFAULT_FILTERS = {
  selectedDiet: null,
  selectedDifficulty: null,
  selectedSeason: [],
  selectedType: null,
  selectedDishType: null,
  isQuickOnly: false,
  isLowIngredientsOnly: false,
  isLowCalorie: false,
  isPantrySort: false,
};

const loadPersistedFilters = () => {
  try {
    const stored = localStorage.getItem(FILTERS_STORAGE_KEY);
    return stored ? { ...DEFAULT_FILTERS, ...JSON.parse(stored) } : DEFAULT_FILTERS;
  } catch {
    return DEFAULT_FILTERS;
  }
};

const persistFilters = (filters) => {
  try {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
  } catch { /* quota exceeded — ignore */ }
};

const PANTRY_MIN_RATIO = 0.6;
const PANTRY_MIN_MATCHED = 2;

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
  const sortByCategory = true;
  const { hasPrivateAccess, onPrivateAccessChange } = useLongPress();
  const { getPantryStats, pantrySize } = usePantry();
  const [shuffleSeed, setShuffleSeed] = useState(Date.now);

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  // État des recettes
  const [allRecipes, setAllRecipes] = useState([]);
  const [loadingState, setLoadingState] = useState(initialLoadingState);
  const [error, setError] = useState(null);
  const persisted = useRef(loadPersistedFilters()).current;
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDiet, setSelectedDiet] = useState(persisted.selectedDiet);
  const [selectedDifficulty, setSelectedDifficulty] = useState(persisted.selectedDifficulty);
  const [selectedSeason, setSelectedSeason] = useState(persisted.selectedSeason);
  const [selectedType, setSelectedType] = useState(persisted.selectedType);
  const [selectedDishType, setSelectedDishType] = useState(persisted.selectedDishType);
  const [isQuickOnly, setIsQuickOnly] = useState(persisted.isQuickOnly);
  const [isLowIngredientsOnly, setIsLowIngredientsOnly] = useState(persisted.isLowIngredientsOnly);
  const [isLowCalorie, setIsLowCalorie] = useState(persisted.isLowCalorie);
  const [isPantrySort, setIsPantrySort] = useState(persisted.isPantrySort);
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    persistFilters({
      selectedDiet,
      selectedDifficulty,
      selectedSeason,
      selectedType,
      selectedDishType,
      isQuickOnly,
      isLowIngredientsOnly,
      isLowCalorie,
      isPantrySort,
    });
  }, [selectedDiet, selectedDifficulty, selectedSeason, selectedType, selectedDishType, isQuickOnly, isLowIngredientsOnly, isLowCalorie, isPantrySort]);

  // Charger toutes les recettes
  const fetchRecipes = useCallback(async () => {
    setLoadingState((prev) => ({ ...prev, recipes: true, error: null }));
    try {
      const data = await getRecipes(hasPrivateAccess);

      const QUICK_THRESHOLD_MINUTES = 30;

      const processedData = data.map((recipe) => {
        const totalTimeInMinutes = recipe.totalTimeMinutes || 0;

        return {
          ...recipe,
          totalTimeInMinutes,
          quick: totalTimeInMinutes > 0 && totalTimeInMinutes <= QUICK_THRESHOLD_MINUTES,
        };
      });

      setAllRecipes(processedData);
    } catch (err) {
      setLoadingState((prev) => ({ ...prev, error: err.message }));
    } finally {
      setLoadingState((prev) => ({
        ...prev,
        recipes: false,
      }));
    }
  }, [hasPrivateAccess]);

  // Écouter les changements d'état d'accès privé
  useEffect(() => {
    const unsubscribe = onPrivateAccessChange(() => {
      setAllRecipes([]);
      fetchRecipes();
    });

    return () => {
      unsubscribe();
    };
  }, [onPrivateAccessChange, fetchRecipes]);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  // État de chargement global
  const isLoading = useMemo(() => {
    return loadingState.recipes;
  }, [loadingState]);

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

        return recipes.filter((recipe) => {
          // Filtre par régime si actif et non exclu
          if (filters.selectedDiet && excludeFilter !== "diet") {
            if (!recipe.diets?.includes(filters.selectedDiet)) {
              return false;
            }
          }

          // Filtre par saison si active et non exclue
          if (filters.selectedSeason?.length > 0 && excludeFilter !== "season") {
            const seasons = Array.isArray(filters.selectedSeason)
              ? filters.selectedSeason
              : [filters.selectedSeason];
            if (!seasons.some((s) => recipe.seasons?.includes(s))) {
              return false;
            }
          }

          // Filtre par type si actif et non exclu
          if (filters.selectedType && excludeFilter !== "type") {
            if (recipe.recipeType !== filters.selectedType) {
              return false;
            }
          }

          // Filtre par type de plat si actif et non exclu
          if (
            filters.selectedDishType &&
            excludeFilter !== "dishType" &&
            !filters.selectedType
          ) {
            if (recipe.recipeType !== filters.selectedDishType) {
              return false;
            }
          }

          // Filtre rapide si actif et non exclu
          if (filters.isQuickOnly && excludeFilter !== "quick") {
            if (!recipe.quick) {
              return false;
            }
          }

          // Filtre peu d'ingrédients si actif et non exclu
          if (
            filters.isLowIngredientsOnly &&
            excludeFilter !== "lowIngredients"
          ) {
            const ingredientsCount = Array.isArray(recipe.ingredients)
              ? recipe.ingredients.length
              : Object.keys(recipe.ingredients || {}).length;

            if (ingredientsCount >= 6) {
              return false;
            }
          }

          // Filtre low calorie si actif et non exclu
          if (filters.isLowCalorie && excludeFilter !== "lowCalorie") {
            if (!recipe.nutritionTags?.includes("low-calorie")) {
              return false;
            }
          }

          // Filtre pantry si actif et non exclu
          if (filters.isPantrySort && excludeFilter !== "pantry") {
            const s = getPantryStats(recipe);
            if (s.ratio < PANTRY_MIN_RATIO || s.matched < PANTRY_MIN_MATCHED) {
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

              const title = normalizeText(recipe.title || "");
              const author = normalizeText(recipe.author || "");
              const bookTitle = normalizeText(recipe.bookTitle || "");
              const description = normalizeText(recipe.description || "");

              const hasIngredient = recipe.ingredients?.some((ingredient) => {
                if (!ingredient?.name) return false;
                const ingredientText = normalizeText(ingredient.name);
                return ingredientText.includes(normalizedSearchTerm);
              });

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

              return matches;
            });
          }

          return true;
        });
      },
    [normalizeText, getPantryStats]
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
          lowIngredients: { count: 0, total: 0 },
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
            { ...currentFilters, selectedSeason: [] },
            "season"
          ).length > 0;
        const countForType =
          filterRecipes(
            [recipe],
            {
              ...currentFilters,
              selectedDishType: null,
              selectedType: null,
            },
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
        items
          .filter((item) => item.id !== "omnivorous") // Exclude omnivorous from stats
          .map((item) => ({
            key: item.id,
            count: map.get(item.id) || 0,
          }));

      const quickRecipes = filterRecipes(
        recipes,
        { ...currentFilters, isQuickOnly: null },
        "quick"
      ).filter((recipe) => recipe.quick);

      const lowIngredientsRecipes = filterRecipes(
        recipes,
        { ...currentFilters, isLowIngredientsOnly: null },
        "lowIngredients"
      ).filter((recipe) => {
        const ingredientsCount = Array.isArray(recipe.ingredients)
          ? recipe.ingredients.length
          : Object.keys(recipe.ingredients || {}).length;
        return ingredientsCount < 6;
      });

      const lowCalorieRecipes = filterRecipes(
        recipes,
        { ...currentFilters, isLowCalorie: false },
        "lowCalorie"
      ).filter((recipe) => recipe.nutritionTags?.includes("low-calorie"));

      const pantryRecipes = filterRecipes(
        recipes,
        { ...currentFilters, isPantrySort: false },
        "pantry"
      ).filter((recipe) => {
        const s = getPantryStats(recipe);
        return s.ratio >= PANTRY_MIN_RATIO && s.matched >= PANTRY_MIN_MATCHED;
      });

      return {
        diet: mapToArray(stats.diet, constants.diets),
        season: mapToArray(stats.season, constants.seasons),
        dishType: mapToArray(stats.type, constants.recipe_types),
        quick: {
          count: quickRecipes.length,
          total: recipes.length,
        },
        lowIngredients: {
          count: lowIngredientsRecipes.length,
          total: recipes.length,
        },
        lowCalorie: {
          count: lowCalorieRecipes.length,
          total: recipes.length,
        },
        pantry: {
          count: pantryRecipes.length,
          total: recipes.length,
        },
      };
    },
    [filterRecipes, constants, getPantryStats]
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
      isLowIngredientsOnly,
      isLowCalorie,
      isPantrySort,
    }),
    [
      searchQuery,
      selectedDiet,
      selectedDifficulty,
      selectedSeason,
      selectedType,
      selectedDishType,
      isQuickOnly,
      isLowIngredientsOnly,
      isLowCalorie,
      isPantrySort,
    ]
  );

  const shuffleSeasonalRecipes = useCallback(() => {
    setShuffleSeed(Date.now());
  }, []);

  // Mémoriser les recettes filtrées
  const filteredRecipes = useMemo(() => {
    let result;

    // Si aucun filtre n'est actif, afficher toutes les recettes avec celles de la saison en cours en premier
    if (
      !searchQuery &&
      !selectedDiet &&
      !selectedDifficulty &&
      (!selectedSeason || selectedSeason.length === 0) &&
      !selectedType &&
      !selectedDishType &&
      !isQuickOnly &&
      !isLowIngredientsOnly &&
      !isLowCalorie &&
      !isPantrySort
    ) {
      const currentSeason = getCurrentSeason();

      const currentSeasonRecipes = allRecipes.filter((recipe) =>
        recipe.seasons?.includes(currentSeason)
      );

      const otherRecipes = allRecipes.filter(
        (recipe) => !recipe.seasons?.includes(currentSeason)
      );

      // Fisher-Yates shuffle using a seeded PRNG so the order is
      // stable for a given shuffleSeed but changes when it increments.
      const seededShuffle = (arr) => {
        const copy = [...arr];
        let seed = shuffleSeed * 2654435761 + copy.length;
        const rand = () => {
          seed = (seed * 16807 + 0) % 2147483647;
          return (seed - 1) / 2147483646;
        };
        for (let i = copy.length - 1; i > 0; i--) {
          const j = Math.floor(rand() * (i + 1));
          [copy[i], copy[j]] = [copy[j], copy[i]];
        }
        return copy;
      };

      result = [
        ...seededShuffle(currentSeasonRecipes),
        ...seededShuffle(otherRecipes),
      ];
    } else {
      // Sinon, appliquer les filtres normalement
      result = filterRecipes(allRecipes, currentFilters);
    }

    // Low-calorie sort: lowest calories first
    if (isLowCalorie) {
      result.sort((a, b) => {
        const calA = a.nutritionPerServing?.calories ?? Infinity;
        const calB = b.nutritionPerServing?.calories ?? Infinity;
        return calA - calB;
      });
    }

    // Pantry sort: order filtered results by total ingredient coverage descending
    if (isPantrySort && pantrySize > 0) {
      const decorated = result.map((recipe, i) => {
        const stats = getPantryStats(recipe);
        const totalIngredients = Array.isArray(recipe.ingredients)
          ? recipe.ingredients.length
          : 0;
        return {
          recipe,
          totalRatio:
            totalIngredients === 0 ? 0 : stats.matched / totalIngredients,
          ratio: stats.ratio,
          i,
        };
      });
      decorated.sort(
        (a, b) => b.totalRatio - a.totalRatio || b.ratio - a.ratio || a.i - b.i
      );
      result = decorated.map((d) => d.recipe);
    }

    return result;
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
    isLowIngredientsOnly,
    isLowCalorie,
    isPantrySort,
    pantrySize,
    getPantryStats,
    shuffleSeed,
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
      isLowIngredientsOnly,
      setIsLowIngredientsOnly,
      isLowCalorie,
      setIsLowCalorie,
      isPantrySort,
      setIsPantrySort,
      isAddRecipeModalOpen,
      setIsAddRecipeModalOpen,
      fetchRecipes,
      getCurrentSeason,
      stats,
      resultsType:
        isPantrySort
          ? "pantry_sorted"
          : !searchQuery &&
            !selectedDiet &&
            !selectedDifficulty &&
            (!selectedSeason || selectedSeason.length === 0) &&
            !selectedType &&
            !selectedDishType &&
            !isQuickOnly &&
            !isLowIngredientsOnly &&
            !isLowCalorie
          ? "random_seasonal"
          : "filtered",
      shuffleSeasonalRecipes,
      openAddRecipeModal: () => setIsAddRecipeModalOpen(true),
      closeAddRecipeModal: () => setIsAddRecipeModalOpen(false),
      resetFilters: () => {
        setSearchQuery("");
        setSelectedDiet(null);
        setSelectedSeason([]);
        setSelectedType(null);
        setSelectedDishType(null);
        setIsQuickOnly(false);
        setIsLowIngredientsOnly(false);
        setIsLowCalorie(false);
        setIsPantrySort(false);
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
      isLowIngredientsOnly,
      isLowCalorie,
      isPantrySort,
      isAddRecipeModalOpen,
      shuffleSeasonalRecipes,
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
