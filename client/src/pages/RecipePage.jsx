import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import { useParams } from "react-router-dom";
import { useRecipe } from "../contexts/RecipeContext";
import SimpleView from "../components/views/SimpleView/index";
import AppTransition from "../components/common/AppTransition";
import useImagesPreloader from "../hooks/useImagesPreloader";
import RecipeNotFound from "../components/common/RecipeNotFound";

const RecipePage = () => {
  const { slug } = useParams();
  const { recipe, loadRecipe, error, resetRecipeState } = useRecipe();
  const { allLoaded } = useImagesPreloader(recipe ? [recipe.slug] : []);
  // État local pour contrôler l'affichage pendant la transition
  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    if (slug) {
      // Indiquer que nous sommes en transition
      setIsTransitioning(true);

      // Réinitialiser l'état de la recette avant de charger la nouvelle
      resetRecipeState();

      // Charger la nouvelle recette
      loadRecipe(slug).finally(() => {
        // Fin de la transition après un court délai pour permettre le rendu
        setTimeout(() => {
          setIsTransitioning(false);
        }, 100);
      });
    }
  }, [slug, loadRecipe, resetRecipeState]);

  return (
    <AppTransition
      type="page"
      // N'afficher la recette que lorsque les images sont chargées ET que nous ne sommes pas en transition
      isVisible={allLoaded && !isTransitioning}
    >
      <Box
        sx={{
          height: "calc(100vh - 64px)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.default",
          position: "relative",
        }}
      >
        {error ? <RecipeNotFound /> : recipe && <SimpleView />}
      </Box>
    </AppTransition>
  );
};

export default RecipePage;
