import React from "react";
import { Box, Typography, Grid } from "@mui/material";
import { useRecipe } from "../../contexts/RecipeContext";
import RecipeChip, { CHIP_TYPES } from "../common/RecipeChip";

const SubRecipeHeader = () => {
  const { recipe, selectedSubRecipe, isIngredientUnused, isToolUnused } =
    useRecipe();

  if (!recipe || !selectedSubRecipe) return null;

  const subRecipe = recipe.subRecipes[selectedSubRecipe];

  // Récupérer tous les outils uniques utilisés dans les étapes
  const uniqueTools = new Set();
  subRecipe.steps.forEach((step) => {
    if (step.tools) {
      step.tools.forEach((toolId) => uniqueTools.add(toolId));
    }
  });

  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Box sx={{ p: 3, pb: 0 }}>
        <Typography
          variant="h4"
          sx={{
            fontWeight: 700,
            color: "text.primary",
            mb: 3,
          }}
        >
          {subRecipe.title}
        </Typography>
      </Box>

      <Box sx={{ px: 3, pb: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={6}>
            <Typography
              variant="subtitle2"
              sx={{
                mb: 1,
                color: "text.secondary",
                fontWeight: 500,
              }}
            >
              Ingrédients nécessaires
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
              {Object.entries(subRecipe.ingredients || {}).map(
                ([id, details]) => {
                  const ingredient = recipe.ingredients[id];
                  const isUnused = isIngredientUnused(id);
                  if (!ingredient) return null;
                  return (
                    <RecipeChip
                      key={id}
                      label={`${ingredient.name} (${details.amount}${ingredient.unit})`}
                      type={CHIP_TYPES.INGREDIENT}
                      isUnused={isUnused}
                    />
                  );
                }
              )}
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Typography
              variant="subtitle2"
              sx={{
                mb: 1,
                color: "text.secondary",
                fontWeight: 500,
              }}
            >
              Ustensiles nécessaires
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
              {Array.from(uniqueTools).map((toolId) => {
                const tool = recipe.tools[toolId];
                const isUnused = isToolUnused(toolId);
                if (!tool) return null;
                return (
                  <RecipeChip
                    key={toolId}
                    label={tool.name}
                    type={CHIP_TYPES.TOOL}
                    isUnused={isUnused}
                  />
                );
              })}
            </Box>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default SubRecipeHeader;
