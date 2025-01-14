import React, { useState, useEffect, useRef, memo } from "react";
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
} from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import RecipeImage from "../components/common/RecipeImage";
import SearchBarWithResults from "../components/SearchBar/index";
import FilterTags from "../components/FilterTags";
import ResultsLabel from "../components/ResultsLabel";
import { useRecipeList } from "../contexts/RecipeListContext";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import BoltIcon from "@mui/icons-material/Bolt";
import AddIcon from "@mui/icons-material/Add";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import RecipeHeader from "../components/views/SimpleView/RecipeHeader";
import AddRecipeModal from "../components/common/AddRecipe/AddRecipeModal";
import AppTransition from "../components/common/AppTransition";
import useImagesPreloader from "../hooks/useImagesPreloader";
import TimeDisplay from "../components/common/TimeDisplay";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import { useConstants } from "../contexts/ConstantsContext";

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

const RecipeCard = memo(({ recipe, isImageLoaded }) => {
  const navigate = useNavigate();

  return (
    <Card
      component={Link}
      to={`/recipe/${recipe.slug}`}
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
        backgroundColor: "background.paper",
        boxShadow: "rgba(0, 0, 0, 0.04) 0px 3px 5px",
        border: "1px solid",
        borderColor: "divider",
        textDecoration: "none",
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-4px)",
          boxShadow:
            "rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px",
        },
      }}
    >
      <Box
        sx={{
          position: "relative",
          paddingTop: "100%",
          width: "100%",
          overflow: "hidden",
          bgcolor: "grey.100",
        }}
      >
        <RecipeImage
          slug={recipe.slug}
          title={recipe.title}
          size="medium"
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            backgroundColor: "grey.100",
          }}
        />
        {recipe.quick && (
          <Box
            sx={{
              position: "absolute",
              top: 12,
              right: 12,
              display: "flex",
              alignItems: "center",
              padding: "6px",
              borderRadius: "8px",
              backdropFilter: "blur(8px)",
              backgroundColor: "rgba(0, 0, 0, 0.4)",
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
            }}
          >
            <BoltIcon sx={{ fontSize: "1.2rem", color: "white" }} />
          </Box>
        )}
        <Box
          sx={{
            position: "absolute",
            bottom: 12,
            left: 12,
            display: "flex",
            gap: 1,
            alignItems: "center",
            padding: "6px 12px",
            borderRadius: "8px",
            backdropFilter: "blur(8px)",
            backgroundColor: "rgba(0, 0, 0, 0.4)",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
          }}
        >
          {recipe.totalTime && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <AccessTimeIcon fontSize="small" sx={{ color: "white" }} />
              <TimeDisplay
                timeString={recipe.totalTime}
                variant="body2"
                sx={{ color: "white", fontWeight: 500 }}
              />
            </Box>
          )}
        </Box>
      </Box>
      <CardContent
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          p: 2,
          pb: 1,
          "&:last-child": {
            pb: 1, // Override du style par défaut de MUI
          },
        }}
      >
        <Typography
          variant="subtitle1"
          component="h2"
          sx={{
            fontWeight: 600,
            fontSize: "1rem",
            lineHeight: 1.3,
          }}
        >
          {recipe.title}
        </Typography>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            flexWrap: "wrap",
            justifyContent: "flex-end",
            mt: "auto",
            pt: 1,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              fontSize: "0.75rem",
            }}
          >
            {recipe.recipeType || "Main"}
            {" • "}
            {Array.isArray(recipe.seasons)
              ? recipe.seasons[0]
              : recipe.seasons?.[0] || "All Seasons"}
          </Typography>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              ml: "auto",
            }}
          >
            <KitchenOutlinedIcon
              sx={{
                fontSize: "1rem",
                color: "text.secondary",
              }}
            />
            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
                fontSize: "0.875rem",
              }}
            >
              {Object.keys(recipe.ingredients || {}).length}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
});

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
  } = useRecipeList();

  // Vérifier si des filtres sont actifs
  const hasActiveFilters = Boolean(
    searchQuery ||
      selectedDiet ||
      selectedSeason ||
      selectedType ||
      selectedDishType ||
      isQuickOnly
  );

  const isLoading =
    loadingState.recipes ||
    (allRecipes.length > 0 && !loadingState.images.size);

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
            <Box sx={{ mt: 4 }}>
              <ResultsLabel />
            </Box>
          </Container>
        </Box>

        {/* Section de la grille qui défile */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
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
          <Container maxWidth="lg" sx={{ pb: 4 }}>
            <Divider sx={{ mb: 3 }} />
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
              <Grid container spacing={3}>
                {filteredRecipes.map((recipe) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={recipe.id}>
                    <RecipeCard
                      recipe={recipe}
                      isImageLoaded={loadingState.images.get(recipe.slug)}
                    />
                  </Grid>
                ))}
              </Grid>
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
