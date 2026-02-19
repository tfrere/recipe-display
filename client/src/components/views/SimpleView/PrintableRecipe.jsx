import React from "react";
import { Box, Typography } from "@mui/material";

const PrintableRecipe = ({ recipe }) => {
  // Build ingredients map for quick lookup (recipe.ingredients is an array)
  const ingredientsMap = {};
  (recipe.ingredients || []).forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  const subRecipes = recipe.subRecipes || [];

  return (
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
        {recipe.metadata?.title || recipe.title}
      </Typography>

      {(recipe.metadata?.description || recipe.description) && (
        <Typography sx={{ mb: 2 }}>
          {recipe.metadata?.description || recipe.description}
        </Typography>
      )}

      <Typography variant="body2" sx={{ mb: 3 }}>
        Pour {recipe.metadata?.servings || recipe.servings} personnes
        {recipe.metadata?.difficulty && ` • ${recipe.metadata.difficulty}`}
        {recipe.metadata?.totalTimeMinutes &&
          ` • ${recipe.metadata.totalTimeMinutes} min`}
      </Typography>

      {/* Ingrédients */}
      <Typography variant="h2" component="h2">
        Ingrédients
      </Typography>
      {subRecipes.map((subRecipe) => (
        <Box key={subRecipe.id} sx={{ mb: 3 }}>
          {subRecipes.length > 1 && subRecipe.title && (
            <Typography variant="h6" sx={{ mb: 1 }}>
              {subRecipe.title}
            </Typography>
          )}
          <ul>
            {(subRecipe.ingredients || []).map((data) => {
              const ingredient = ingredientsMap[data.ref];
              if (!ingredient) return null;

              return (
                <li key={data.ref}>
                  {data.amount != null ? `${data.amount} ` : ""}
                  {ingredient.unit ? `${ingredient.unit} ` : ""}
                  {ingredient.name}
                </li>
              );
            })}
          </ul>
        </Box>
      ))}

      {/* Étapes */}
      <Typography variant="h2" component="h2">
        Préparation
      </Typography>
      {subRecipes.map((subRecipe) => (
        <Box key={subRecipe.id} sx={{ mb: 3 }}>
          {subRecipes.length > 1 && subRecipe.title && (
            <Typography variant="h6" sx={{ mb: 1 }}>
              {subRecipe.title}
            </Typography>
          )}
          <ol>
            {(subRecipe.steps || []).map((step) =>
              step ? (
                <li key={step.id}>
                  {step.action}
                  {step.time && ` (${step.time})`}
                </li>
              ) : null
            )}
          </ol>
        </Box>
      ))}
    </Box>
  );
};

export default PrintableRecipe;
