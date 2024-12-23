import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  FormControl,
  Select,
  MenuItem,
  AppBar,
  Toolbar,
  Tabs,
  Tab,
} from "@mui/material";
import GraphView from "./components/visualization/GraphView";
import TimelineView from "./components/visualization/TimelineView";
import StepByStepView from "./components/visualization/StepByStepView";
import RecipeSidebar from "./components/layout/RecipeSidebar";
import BarChartIcon from "@mui/icons-material/BarChart";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import KitchenIcon from "@mui/icons-material/Kitchen";
import { RecipeProvider, useRecipe } from "./contexts/RecipeContext";
import SubRecipeHeader from "./components/recipe/SubRecipeHeader";
import RecipeTabs from "./components/recipe/RecipeTabs";

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

const AppContent = () => {
  const {
    recipe,
    loading,
    error,
    loadRecipe,
    selectedSubRecipe,
    getSubRecipeProgress,
  } = useRecipe();
  const [selectedRecipe, setSelectedRecipe] = useState(RECIPES[0]);
  const [viewMode, setViewMode] = useState(0);

  useEffect(() => {
    loadRecipe(selectedRecipe.file);
  }, [selectedRecipe, loadRecipe]);

  const handleRecipeChange = (event) => {
    const newRecipe = RECIPES.find((r) => r.id === event.target.value);
    if (newRecipe) {
      setSelectedRecipe(newRecipe);
    }
  };

  const renderView = () => {
    switch (viewMode) {
      case 0:
        return <StepByStepView />;
      case 1:
        return <GraphView />;
      case 2:
        return <TimelineView />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Box sx={{ height: "100vh", display: "flex", flexDirection: "column" }}>
        <AppBar
          position="static"
          elevation={0}
          sx={{
            bgcolor: "grey.50",
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Toolbar>
            <Typography
              variant="h6"
              component="div"
              sx={{
                flexGrow: 1,
                color: "grey.800",
                fontWeight: 500,
              }}
            >
              Recettes
            </Typography>
            <FormControl sx={{ minWidth: 200 }}>
              <Select
                value={selectedRecipe.id}
                onChange={handleRecipeChange}
                sx={{
                  bgcolor: "background.paper",
                  "& .MuiSelect-select": { color: "grey.800" },
                  "& .MuiSelect-icon": { color: "grey.600" },
                }}
              >
                {RECIPES.map((recipe) => (
                  <MenuItem key={recipe.id} value={recipe.id}>
                    {recipe.title}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Toolbar>
        </AppBar>
        <Box
          sx={{
            p: LAYOUT.spacing,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography>Chargement de la recette...</Typography>
        </Box>
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
      <AppBar
        position="static"
        elevation={0}
        sx={{
          bgcolor: "grey.50",
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Toolbar>
          <Typography
            variant="h6"
            component="div"
            sx={{
              flexGrow: 1,
              color: "grey.800",
              fontWeight: 500,
            }}
          >
            Recettes
          </Typography>
          <FormControl sx={{ minWidth: 200 }}>
            <Select
              value={selectedRecipe.id}
              onChange={handleRecipeChange}
              sx={{
                bgcolor: "background.paper",
                "& .MuiSelect-select": { color: "grey.800" },
                "& .MuiSelect-icon": { color: "grey.600" },
              }}
            >
              {RECIPES.map((recipe) => (
                <MenuItem key={recipe.id} value={recipe.id}>
                  {recipe.title}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Toolbar>
      </AppBar>

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
            activeTab={
              viewMode === 0 ? "steps" : viewMode === 1 ? "graph" : "timeline"
            }
            onTabChange={(e, value) =>
              setViewMode(value === "steps" ? 0 : value === "graph" ? 1 : 2)
            }
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

function App() {
  return (
    <RecipeProvider>
      <AppContent />
    </RecipeProvider>
  );
}

export default App;
