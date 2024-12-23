import React from "react";
import { Box, Typography, Chip, Grid } from "@mui/material";
import { useRecipe } from "../../contexts/RecipeContext";

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
      {/* Titre */}
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

      {/* Listes */}
      <Box sx={{ px: 3, pb: 3 }}>
        <Grid container spacing={3}>
          {/* Ingrédients */}
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
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {Object.entries(subRecipe.ingredients || {}).map(
                ([id, details]) => {
                  const ingredient = recipe.ingredients[id];
                  const isUnused = isIngredientUnused(id);
                  if (!ingredient) return null;
                  return (
                    <Chip
                      key={id}
                      label={`${ingredient.name} (${details.amount}${ingredient.unit})`}
                      size="small"
                      variant="outlined"
                      color={isUnused ? "default" : "primary"}
                      sx={{
                        mb: 0.5,
                        opacity: isUnused ? 0.6 : 1,
                        "& .MuiChip-label": {
                          px: 2,
                          py: 2,
                        },
                        borderRadius: "6px",
                      }}
                    />
                  );
                }
              )}
            </Box>
          </Grid>

          {/* Ustensiles */}
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
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {Array.from(uniqueTools).map((toolId) => {
                const tool = recipe.tools[toolId];
                const isUnused = isToolUnused(toolId);
                if (!tool) return null;
                return (
                  <Chip
                    key={toolId}
                    label={tool.name}
                    size="small"
                    variant="outlined"
                    color={isUnused ? "default" : "warning"}
                    sx={{
                      mb: 0.5,
                      opacity: isUnused ? 0.6 : 1,
                      "& .MuiChip-label": {
                        px: 2,
                        py: 2,
                      },
                      borderRadius: "6px",
                    }}
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
