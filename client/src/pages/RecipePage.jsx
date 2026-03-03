import React, { useCallback, useEffect, useState } from "react";
import { Box } from "@mui/material";
import { useParams, useNavigate } from "react-router-dom";
import { useRecipe } from "../contexts/RecipeContext";
import SimpleView from "../components/views/SimpleView/index";
import AppTransition from "../components/common/AppTransition";
import useImagesPreloader from "../hooks/useImagesPreloader";
import RecipeNotFound from "../components/common/RecipeNotFound";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

const RecipePage = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { recipe, loadRecipe, error, resetRecipeState } = useRecipe();
  const { allLoaded } = useImagesPreloader(recipe ? [recipe.slug] : []);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const goToRandomRecipe = useCallback(async () => {
    try {
      const headers = {};
      const token = import.meta.env.VITE_PRIVATE_TOKEN;
      if (token) headers["X-Private-Token"] = token;

      const res = await fetch(`${API_BASE_URL}/api/recipes/random`, { headers });
      if (!res.ok) return;
      const { slug: randomSlug } = await res.json();
      if (randomSlug && randomSlug !== slug) {
        navigate(`/recipe/${randomSlug}`);
      }
    } catch {
      /* silently ignore network errors */
    }
  }, [slug, navigate]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = e.target.tagName;
      const isEditable = tag === "INPUT" || tag === "TEXTAREA" || e.target.isContentEditable;
      if (e.key === "r" && !isEditable && !e.ctrlKey && !e.metaKey && !e.altKey) {
        goToRandomRecipe();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goToRandomRecipe]);

  useEffect(() => {
    if (slug) {
      setIsTransitioning(true);
      resetRecipeState();
      loadRecipe(slug).finally(() => {
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
