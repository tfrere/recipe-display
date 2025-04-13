import React from "react";
import { Box, Typography } from "@mui/material";

const PrintableRecipe = ({ recipe }) => (
  <Box
    className="printable-recipe"
    sx={{
      display: "none",
      "@media print": {
        display: "block",
        padding: "0",
        maxWidth: "100%",
        "& h1": { fontSize: "24px", marginBottom: "16px" },
        "& h2": { fontSize: "20px", marginTop: "24px", marginBottom: "12px" },
        "& p": { fontSize: "14px", lineHeight: 1.5 },
        "& ul": {
          padding: 0,
          margin: 0,
          listStyle: "none",
          display: "inline",
        },
        "& li": {
          display: "inline",
          "&:after": {
            content: '" • "',
            marginRight: "8px",
          },
          "&:last-child:after": {
            content: '""',
          },
        },
        "& ol": { paddingLeft: "20px" },
        "& ol li": {
          display: "list-item",
          marginBottom: "8px",
        },
        "@page": {
          margin: "1cm",
          size: "auto",
          marks: "none",
        },
      },
    }}
  >
    {/* En-tête */}
    <Typography variant="h1" component="h1">
      {recipe.title}
    </Typography>

    {recipe.description && (
      <Typography sx={{ mb: 2 }}>{recipe.description}</Typography>
    )}

    <Typography variant="body2" sx={{ mb: 3 }}>
      Pour {recipe.servings} personnes
      {recipe.metadata?.difficulty && ` • ${recipe.metadata.difficulty}`}
      {recipe.totalTime && ` • ${recipe.totalTime}`}
    </Typography>

    {/* Ingrédients */}
    <Typography variant="h2" component="h2">
      Ingrédients
    </Typography>
    {Object.entries(recipe.subRecipes || {}).map(
      ([subRecipeId, subRecipe]) =>
        subRecipe && (
          <Box key={subRecipeId} sx={{ mb: 3 }}>
            {Object.keys(recipe.subRecipes || {}).length > 1 &&
              subRecipe.title && (
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {subRecipe.title}
                </Typography>
              )}
            <ul>
              {Object.entries(subRecipe.ingredients || {}).map(
                ([ingredientId, data]) => {
                  const ingredient = recipe.ingredients?.[ingredientId];
                  if (!ingredient) return null;

                  return (
                    <li key={ingredientId}>
                      {data.amount} {ingredient.unit} {ingredient.name}
                    </li>
                  );
                }
              )}
            </ul>
          </Box>
        )
    )}

    {/* Étapes */}
    <Typography variant="h2" component="h2">
      Préparation
    </Typography>
    {Object.entries(recipe.subRecipes || {}).map(
      ([subRecipeId, subRecipe]) =>
        subRecipe && (
          <Box key={subRecipeId} sx={{ mb: 3 }}>
            {Object.keys(recipe.subRecipes || {}).length > 1 &&
              subRecipe.title && (
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {subRecipe.title}
                </Typography>
              )}
            <ol>
              {Object.values(subRecipe.steps || {}).map(
                (step) =>
                  step && (
                    <li key={step.id}>
                      {step.action}
                      {step.time && ` (${step.time})`}
                    </li>
                  )
              )}
            </ol>
          </Box>
        )
    )}
  </Box>
);

export default PrintableRecipe;
