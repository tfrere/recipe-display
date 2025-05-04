import React, {
  useState,
  useEffect,
  useRef,
  memo,
  useCallback,
  useMemo,
} from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Container,
  CircularProgress,
  Alert,
  Paper,
  Button,
  TextField,
  Stack,
  Chip,
  Divider,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import SearchBarWithResults from "../components/SearchBar/index";
import FilterTags from "../components/FilterTags";
import { useRecipeList } from "../contexts/RecipeListContext";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import AddIcon from "@mui/icons-material/Add";
import AddRecipeModal from "../components/common/AddRecipe/AddRecipeModal";
import AppTransition from "../components/common/AppTransition";
import { useConstants } from "../contexts/ConstantsContext";
import { useVirtualizer } from "@tanstack/react-virtual";
import RecipeCard from "../components/RecipeCard";

const HOME_TEXTS = {
  NO_RECIPES: {
    TITLE: "No recipes found",
    DESCRIPTION:
      "Try adding a new recipe by clicking the + button in the top right corner",
  },
  NO_RESULTS: {
    TITLE: "No recipes found for your search",
    DESCRIPTION: "Try adjusting your filters or search criteria",
  },
  COMMON: {
    LOADING: "Loading...",
    ERROR: "An error occurred while loading recipes",
  },
};

const NoRecipes = memo(({ hasActiveFilters }) => {
  const { openAddRecipeModal } = useRecipeList();

  return (
    <Paper
      elevation={0}
      sx={{
        py: 8,
        px: 4,
        textAlign: "center",
        bgcolor: "background.paper",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 2,
      }}
    >
      <RestaurantIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
      <Typography variant="h4" component="h2" gutterBottom>
        {hasActiveFilters
          ? HOME_TEXTS.NO_RESULTS.TITLE
          : HOME_TEXTS.NO_RECIPES.TITLE}
      </Typography>
      <Typography variant="body1" color="text.secondary">
        {hasActiveFilters
          ? HOME_TEXTS.NO_RESULTS.DESCRIPTION
          : HOME_TEXTS.NO_RECIPES.DESCRIPTION}
      </Typography>
      {!hasActiveFilters && (
        <Box sx={{ mt: 2 }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={openAddRecipeModal}
          >
            Add Recipe
          </Button>
        </Box>
      )}
    </Paper>
  );
});

const VirtualizedRecipeGrid = memo(
  ({
    recipes,
    loadingState,
    isLoading,
    // Ces props ne sont plus utilisées pour le filtrage mais sont conservées
    // pour la fonction de comparaison React.memo
    searchQuery,
    selectedDiet,
    selectedSeason,
    selectedType,
    selectedDishType,
    isQuickOnly,
    isFewIngredients,
  }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
    const isTablet = useMediaQuery(theme.breakpoints.down("md"));
    const isDesktop = useMediaQuery(theme.breakpoints.down("lg"));

    // Référence au conteneur parent
    const parentRef = useRef(null);

    // État pour stocker la largeur du conteneur (mise à jour au redimensionnement)
    const [containerWidth, setContainerWidth] = useState(0);

    // Nous utilisons directement les recettes filtrées fournies par le contexte
    const filteredRecipes = recipes;

    const getColumnCount = () => {
      if (isMobile) return 1; // xs
      if (isTablet) return 2; // sm
      if (isDesktop) return 3; // md
      return 4; // lg et plus
    };

    const columnCount = getColumnCount();
    const GAP = 24; // 24px de gap entre les éléments

    // Calculer le nombre de lignes nécessaires
    const rowCount = Math.ceil(filteredRecipes.length / columnCount);

    // Configurer le virtualiseur pour les lignes
    const rowVirtualizer = useVirtualizer({
      count: rowCount,
      getScrollElement: () => parentRef.current,
      estimateSize: () => 350, // Estimation initiale de la hauteur de chaque ligne
      overscan: 3, // Précharger quelques lignes au-dessus et en-dessous
    });

    // Observer les redimensionnements du conteneur parent
    useEffect(() => {
      // Fonction pour mettre à jour la largeur du conteneur
      const updateContainerWidth = () => {
        if (parentRef.current) {
          setContainerWidth(parentRef.current.offsetWidth);
        }
      };

      // Observer initial
      updateContainerWidth();

      // Créer un ResizeObserver pour détecter les changements de taille
      const resizeObserver = new ResizeObserver(() => {
        updateContainerWidth();
      });

      // Observer le conteneur parent
      if (parentRef.current) {
        resizeObserver.observe(parentRef.current);
      }

      // Nettoyage
      return () => {
        if (parentRef.current) {
          resizeObserver.unobserve(parentRef.current);
        }
        resizeObserver.disconnect();
      };
    }, []);

    // Calculer la largeur des colonnes
    const columnWidth =
      containerWidth > 0
        ? (containerWidth - GAP * (columnCount + 1)) / columnCount
        : 0;

    // Générer les éléments virtualisés (lignes)
    const virtualRows = rowVirtualizer.getVirtualItems();

    return (
      <div
        ref={parentRef}
        style={{
          height: "100%",
          width: "100%",
          overflow: "auto",
          position: "relative",
        }}
      >
        {/* Créer un div pour définir la hauteur totale du scroll */}
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: "100%",
            position: "relative",
          }}
        >
          {/* Rendre les lignes virtualisées */}
          {virtualRows.map((virtualRow) => {
            const rowIndex = virtualRow.index;

            return (
              <div
                ref={rowVirtualizer.measureElement}
                key={virtualRow.key}
                data-index={virtualRow.index}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${virtualRow.start}px)`,
                  padding: `${GAP / 2}px`,
                  display: "grid",
                  gridTemplateColumns: `repeat(${columnCount}, 1fr)`,
                  gap: `${GAP}px`,
                }}
              >
                {/* Générer les cartes dans cette ligne */}
                {Array.from({ length: columnCount }).map((_, colIndex) => {
                  const recipeIndex = rowIndex * columnCount + colIndex;

                  // Vérifier si l'index est valide
                  if (recipeIndex >= filteredRecipes.length) {
                    return <div key={`empty-${colIndex}`} />;
                  }

                  const recipe = filteredRecipes[recipeIndex];

                  return (
                    <div key={`recipe-${recipe.id || recipe.slug}`}>
                      <RecipeCard recipe={recipe} />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    );
  },
  (prevProps, nextProps) => {
    // Comparaison personnalisée pour éviter les re-rendus inutiles
    // Ne re-rendre que si les recettes ou l'état de chargement changent
    const areRecipesEqual = prevProps.recipes === nextProps.recipes;
    const isLoadingEqual = prevProps.isLoading === nextProps.isLoading;

    return areRecipesEqual && isLoadingEqual;
  }
);

const HomePage = () => {
  const { constants } = useConstants();

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  // Convert arrays to lookup objects for easy access
  const RECIPE_TYPE_LABELS = Object.freeze(
    Object.fromEntries(
      constants.recipe_types.map((type) => [type.id, type.label])
    )
  );
  const SEASON_LABELS = Object.freeze(
    Object.fromEntries(
      constants.seasons.map((season) => [season.id, season.label])
    )
  );

  const {
    allRecipes,
    filteredRecipes,
    loadingState,
    error,
    isAddRecipeModalOpen,
    closeAddRecipeModal,
    fetchRecipes,
    searchQuery,
    selectedDiet,
    selectedSeason,
    selectedType,
    selectedDishType,
    isQuickOnly,
    isFewIngredients,
  } = useRecipeList();

  // Vérifier si des filtres sont actifs
  const hasActiveFilters = Boolean(
    searchQuery ||
      selectedDiet ||
      selectedSeason ||
      selectedType ||
      selectedDishType ||
      isQuickOnly ||
      isFewIngredients
  );

  const isLoading = loadingState.recipes;

  return (
    <AppTransition type="fade" isVisible={!isLoading}>
      <Box
        sx={{
          height: "calc(100vh - 64px)",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "background.default",
        }}
      >
        {/* Section de recherche avec Container */}
        <Box sx={{ pt: 4, pb: 2 }}>
          <Container maxWidth="lg">
            <SearchBarWithResults
              sx={{
                backgroundColor: "background.paper",
                borderRadius: 1,
                "& .MuiOutlinedInput-root": {
                  borderRadius: 1,
                },
              }}
            />
            <FilterTags
              sx={{
                backgroundColor: "background.paper",
                borderRadius: 1,
                "& .MuiChip-root": {
                  backgroundColor: "background.paper",
                  "&:hover": {
                    backgroundColor: "background.paper",
                    opacity: 0.9,
                  },
                },
              }}
            />
          </Container>
        </Box>

        {/* Section de la grille qui défile */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            mt: 1,
            overflowY: "scroll",
            overflowX: "hidden",
            "&::-webkit-scrollbar": {
              width: "8px",
            },
            "&::-webkit-scrollbar-track": {
              background: "transparent",
            },
            "&::-webkit-scrollbar-thumb": {
              background: (theme) =>
                theme.palette.mode === "dark" ? "#555" : "#ddd",
              borderRadius: "4px",
            },
            "&::-webkit-scrollbar-thumb:hover": {
              background: (theme) =>
                theme.palette.mode === "dark" ? "#666" : "#ccc",
            },
          }}
        >
          <Container maxWidth="lg" sx={{ pb: 4, height: "100%" }}>
            {error ? (
              <Alert severity="error" sx={{ m: 4 }}>
                Une erreur est survenue lors du chargement des recettes.
              </Alert>
            ) : isLoading ? (
              <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
                <CircularProgress />
              </Box>
            ) : filteredRecipes?.length === 0 ? (
              <NoRecipes hasActiveFilters={hasActiveFilters} />
            ) : (
              <VirtualizedRecipeGrid
                recipes={filteredRecipes}
                loadingState={loadingState}
                isLoading={isLoading}
                searchQuery={searchQuery}
                selectedDiet={selectedDiet}
                selectedSeason={selectedSeason}
                selectedType={selectedType}
                selectedDishType={selectedDishType}
                isQuickOnly={isQuickOnly}
                isFewIngredients={isFewIngredients}
              />
            )}
          </Container>
        </Box>
      </Box>

      <AddRecipeModal
        open={isAddRecipeModalOpen}
        onClose={closeAddRecipeModal}
        onRecipeAdded={fetchRecipes}
      />
    </AppTransition>
  );
};

export default HomePage;
