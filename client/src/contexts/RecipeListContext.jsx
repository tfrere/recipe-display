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
  const { getPantryMatchRatio, pantrySize } = usePantry();
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
  const [selectedSeason, setSelectedSeason] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const [selectedDishType, setSelectedDishType] = useState(null);
  const [isQuickOnly, setIsQuickOnly] = useState(false);
  const [isLowIngredientsOnly, setIsLowIngredientsOnly] = useState(false);
  const [isPantrySort, setIsPantrySort] = useState(false);
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Charger toutes les recettes
  const fetchRecipes = useCallback(async () => {
    setLoadingState((prev) => ({ ...prev, recipes: true, error: null }));
    try {
      const data = await getRecipes(hasPrivateAccess);

      // Ajouter le traitement pour définir la propriété quick en fonction du temps total
      const processedData = data.map((recipe) => {
        // Prefer DAG-computed totalTimeMinutes, fall back to legacy totalTime
        const totalTimeInMinutes =
          recipe.metadata?.totalTimeMinutes ||
          (typeof recipe.totalTime === "number"
            ? recipe.totalTime
            : parseFloat(recipe.totalTime) || 0);

        // Une recette est considérée rapide si elle prend 46 minutes ou moins
        return {
          ...recipe,
          quick: recipe.quick || totalTimeInMinutes <= 46,
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
    const unsubscribe = onPrivateAccessChange((newValue) => {
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
            // Compter le nombre d'ingrédients - ils peuvent être dans un tableau ou dans un objet
            const ingredientsCount = Array.isArray(recipe.ingredients)
              ? recipe.ingredients.length
              : Object.keys(recipe.ingredients || {}).length;

            if (ingredientsCount >= 6) {
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
      isLowIngredientsOnly,
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
      isPantrySort,
    ]
  );

  // Mémoriser les recettes filtrées
  const filteredRecipes = useMemo(() => {
    let result;

    // Si aucun filtre n'est actif (hors pantry), afficher toutes les recettes avec celles de la saison en cours en premier
    if (
      !searchQuery &&
      !selectedDiet &&
      !selectedDifficulty &&
      (!selectedSeason || selectedSeason.length === 0) &&
      !selectedType &&
      !selectedDishType &&
      !isQuickOnly &&
      !isLowIngredientsOnly
    ) {
      const currentSeason = getCurrentSeason();

      // Identifier les recettes de la saison actuelle
      const currentSeasonRecipes = allRecipes.filter((recipe) =>
        recipe.seasons?.includes(currentSeason)
      );

      // Identifier les recettes qui ne sont pas de la saison actuelle
      const otherRecipes = allRecipes.filter(
        (recipe) => !recipe.seasons?.includes(currentSeason)
      );

      // Vérifier si on a déjà un ordre pour cette saison
      if (!seasonalRecipesOrder.current.has(currentSeason)) {
        // Si non, créer un nouvel ordre aléatoire
        const order = [...currentSeasonRecipes]
          .sort(() => Math.random() - 0.5)
          .map((recipe) => recipe.id);
        seasonalRecipesOrder.current.set(currentSeason, order);
      }

      // Utiliser l'ordre mémorisé pour les recettes de la saison actuelle
      const order = seasonalRecipesOrder.current.get(currentSeason);
      const orderedSeasonalRecipes = [...currentSeasonRecipes].sort((a, b) => {
        const indexA = order.indexOf(a.id);
        const indexB = order.indexOf(b.id);
        return indexA - indexB;
      });

      // Mélanger les autres recettes de façon aléatoire mais stable
      const orderedOtherRecipes = [...otherRecipes].sort(
        () => 0.5 - Math.random()
      );

      // Combiner les deux listes: d'abord les recettes de saison, puis les autres
      result = [
        ...orderedSeasonalRecipes,
        ...orderedOtherRecipes,
      ];
    } else {
      // Sinon, appliquer les filtres normalement
      result = filterRecipes(allRecipes, currentFilters);
    }

    // Pantry sort: re-order by pantry match ratio (matched / pantry-type ingredients) descending
    if (isPantrySort && pantrySize > 0) {
      result = [...result].sort((a, b) => {
        const ratioA = getPantryMatchRatio(a);
        const ratioB = getPantryMatchRatio(b);
        return ratioB - ratioA;
      });
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
    isPantrySort,
    pantrySize,
    getPantryMatchRatio,
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
            !isLowIngredientsOnly
          ? "random_seasonal"
          : "filtered",
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
      isPantrySort,
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
