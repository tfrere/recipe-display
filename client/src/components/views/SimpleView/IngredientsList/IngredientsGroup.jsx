import React from "react";
import { Box, Typography } from "@mui/material";
import IngredientItem from "./IngredientItem";

/**
 * Component for rendering a group of ingredients (by category or sub-recipe)
 */
const IngredientsGroup = ({
  group,
  recipe,
  sortByCategory,
  checkedIngredients,
  onIngredientCheck,
}) => {
  // En mode normal, on affiche toujours le titre du groupe si showTitle est true
  // En mode liste de courses, on affiche toujours le titre de la catégorie
  const shouldShowTitle = sortByCategory || group.showTitle;

  // Réduire la marge inférieure lorsqu'il n'y a pas de titre affiché
  const marginBottom = shouldShowTitle ? 3 : 1;

  return (
    <Box key={group.key} sx={{ mb: marginBottom }}>
      {/* Group title (category or sub-recipe) */}
      {shouldShowTitle && (
        <Typography
          variant="body1"
          sx={{
            color: "text.primary",
            mb: 1.5,
            fontStyle: "italic",
            textTransform: "capitalize",
            fontWeight: 600,
          }}
        >
          {group.title}
        </Typography>
      )}

      {/* Ingredient items */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
        {group.items.map((ingredient) => (
          <IngredientItem
            key={`${ingredient.subRecipeId}-${ingredient.id}`}
            ingredient={ingredient}
            sortByCategory={sortByCategory}
            isChecked={checkedIngredients.has(
              `${ingredient.subRecipeId}-${ingredient.name}`
            )}
            onCheckChange={onIngredientCheck}
          />
        ))}
      </Box>
    </Box>
  );
};

export default IngredientsGroup;
