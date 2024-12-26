import React, { useEffect } from "react";
import { Box } from "@mui/material";
import { useParams } from "react-router-dom";
import { useRecipe } from "../contexts/RecipeContext";
import GraphView from "../components/views/GraphView";
import SimpleView from "../components/views/SimpleView/index";

const VIEWS = {
  GRAPH: 'graph',
  SIMPLE: 'simple'
};

const RecipePage = ({ currentView }) => {
  const { recipeId } = useParams();
  const { recipe, loadRecipe } = useRecipe();

  useEffect(() => {
    loadRecipe(recipeId);
  }, [recipeId, loadRecipe]);

  const renderView = () => {
    switch (currentView) {
      case VIEWS.GRAPH:
        return <GraphView />;
      default:
        return <SimpleView />;
    }
  };

  return (
    <Box sx={{ 
      height: 'calc(100vh - 64px)', // hauteur totale moins la hauteur de la navbar
      overflow: "hidden",
      display: 'flex',
      flexDirection: 'column'
    }}>
      {recipe && renderView()}
    </Box>
  );
};

export default RecipePage;
