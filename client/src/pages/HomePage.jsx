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
import { FixedSizeGrid as VirtualGrid } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";
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

    // Nous utilisons directement les recettes filtrées fournies par le contexte
    const filteredRecipes = recipes;

    const getColumnCount = () => {
      if (isMobile) return 1; // xs
      if (isTablet) return 2; // sm
      if (isDesktop) return 3; // md
      return 4; // lg et plus
    };

    const columnCount = getColumnCount();
    const rowCount = Math.ceil(filteredRecipes.length / columnCount);
    const GAP = 24; // 16px de gap entre les éléments

    // Utilisation de useCallback avec des dépendances minimales pour éviter
    // que cette fonction ne soit recréée trop souvent
    const cellRenderer = useCallback(
      ({ columnIndex, rowIndex, style }) => {
        const index = rowIndex * columnCount + columnIndex;
        if (index >= filteredRecipes.length) return null;

        const recipe = filteredRecipes[index];

        // Calculer une clé unique pour éviter les re-rendus inutiles
        const key = `recipe-${recipe.id || recipe.slug}`;

        return (
          <Box key={key}>
            <RecipeCard
              recipe={recipe}
              style={{
                ...style,
                height: "auto",
                margin: 0,
                left: style.left + columnIndex * GAP,
                top: style.top,
              }}
            />
          </Box>
        );
      },
      [filteredRecipes, columnCount]
    );

    // Mémoiser la grille pour éviter les re-rendus inutiles
    const gridComponent = useMemo(() => {
      return (
        <Box sx={{ height: "100%", width: "100%" }}>
          <AutoSizer>
            {({ height, width }) => {
              const availableWidth = width - GAP * (columnCount - 1);
              const columnWidth = availableWidth / columnCount;

              return (
                <VirtualGrid
                  key={`${columnCount}-${filteredRecipes.length}`}
                  columnCount={columnCount}
                  columnWidth={columnWidth}
                  height={height}
                  rowCount={rowCount}
                  rowHeight={400} // Hauteur minimale pour éviter les problèmes de rendu
                  width={width}
                >
                  {cellRenderer}
                </VirtualGrid>
              );
            }}
          </AutoSizer>
        </Box>
      );
    }, [filteredRecipes, columnCount, rowCount, cellRenderer]);

    return gridComponent;
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
