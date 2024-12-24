import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Box, IconButton, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import GraphView from "../components/visualization/GraphView";
import StepByStepView from "../components/visualization/StepByStepView";
import RecipeSidebar from "../components/layout/RecipeSidebar";
import { useRecipe } from "../contexts/RecipeContext";
import SubRecipeHeader from "../components/recipe/SubRecipeHeader";
import RecipeTabs from "../components/recipe/RecipeTabs";

const RECIPES = [
  {
    id: "buche-noel",
    title: "Bûche de Noël",
    file: "/data/buche-noel.recipe.json",
  },
  {
    id: "laap-thailandais",
    title: "Laap Thailandais",
    file: "/data/laap-thailandais.recipe.json",
  },
];

const LAYOUT = {
  leftColumn: {
    minWidth: "400px",
    width: "30%",
    maxWidth: "600px",
  },
  spacing: 2,
};

const RecipePage = () => {
  const { recipeId } = useParams();
  const navigate = useNavigate();
  const { recipe, loading, error, loadRecipe } = useRecipe();
  const [viewMode, setViewMode] = useState(0);

  useEffect(() => {
    const selectedRecipe = RECIPES.find((r) => r.id === recipeId);
    if (selectedRecipe) {
      loadRecipe(selectedRecipe.file);
    }
  }, [recipeId, loadRecipe]);

  const renderView = () => {
    switch (viewMode) {
      case 0:
        return <StepByStepView />;
      case 1:
        return <GraphView />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Box
        sx={{ height: "100vh", display: "flex", flexDirection: "column", p: 3 }}
      >
        <Typography>Chargement de la recette...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">Erreur: {error}</Typography>
      </Box>
    );
  }

  if (!recipe) {
    return null;
  }

  return (
    <Box sx={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Box
        id="tooltip"
        sx={{
          position: "fixed",
          visibility: "hidden",
          bgcolor: "background.paper",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          p: 1,
          boxShadow: 1,
          maxWidth: 200,
          zIndex: 1000,
          pointerEvents: "none",
        }}
      />

      <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
        <IconButton onClick={() => navigate("/")} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography
          variant="h6"
          component="span"
          sx={{ color: "text.primary" }}
        >
          {recipe.title}
        </Typography>
      </Box>

      <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <RecipeSidebar layout={LAYOUT} />

        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            bgcolor: "grey.50",
          }}
        >
          <SubRecipeHeader />
          <RecipeTabs
            activeTab={viewMode === 0 ? "steps" : "graph"}
            onTabChange={(e, value) => setViewMode(value === "steps" ? 0 : 1)}
          />
          <Box
            sx={{
              flex: 1,
              overflow: "auto",
            }}
          >
            {renderView()}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default RecipePage;
