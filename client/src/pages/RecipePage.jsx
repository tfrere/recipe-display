import React, { useEffect } from "react";
import { Box } from "@mui/material";
import { useParams } from "react-router-dom";
import { useRecipe } from "../contexts/RecipeContext";
import SimpleView from "../components/views/SimpleView/index";
import AppTransition from '../components/common/AppTransition';
import useImagesPreloader from '../hooks/useImagesPreloader';
import RecipeNotFound from '../components/common/RecipeNotFound';

const RecipePage = () => {
  const { slug } = useParams();
  const { recipe, loadRecipe, error } = useRecipe();
  const { allLoaded } = useImagesPreloader(recipe ? [recipe.slug] : []);

  useEffect(() => {
    if (slug) {
      loadRecipe(slug);
    }
  }, [slug, loadRecipe]);

  return (
    <AppTransition type="page" isVisible={allLoaded}>
      <Box sx={{ 
        height: 'calc(100vh - 64px)', 
        overflow: "hidden",
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.default',
        position: 'relative'
      }}>
        {error ? <RecipeNotFound /> : recipe && <SimpleView />}
      </Box>
    </AppTransition>
  );
};

export default RecipePage;
