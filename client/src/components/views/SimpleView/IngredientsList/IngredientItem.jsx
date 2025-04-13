import React from "react";
import { Box, Typography, Checkbox } from "@mui/material";

/**
 * Component for rendering a single ingredient item
 */
const IngredientItem = ({
  ingredient,
  sortByCategory,
  isChecked,
  onCheckChange,
}) => {
  return (
    <Box
      key={`${ingredient.subRecipeId}-${ingredient.id}`}
      sx={{
        display: "grid",
        gridTemplateColumns: sortByCategory
          ? "0.3fr 0.7fr auto" // With checkbox
          : "0.3fr 0.7fr", // Without checkbox
        gap: 2,
        alignItems: "start",
        py: 0.25,
        mb: 0.75,
        opacity: sortByCategory ? 1 : ingredient.isUnused ? 0.5 : 1,
        textDecoration: sortByCategory
          ? "none"
          : ingredient.isUnused
          ? "line-through"
          : "none",
      }}
    >
      {/* Amount with unit */}
      <Typography
        variant="body1"
        sx={{
          color: "text.secondary",
          textAlign: "left",
        }}
      >
        {ingredient.displayAmount}
      </Typography>

      {/* Ingredient name and state */}
      <Box sx={{ textAlign: "right" }}>
        <Typography variant="body1" component="span">
          {ingredient.name}
          {ingredient.displayState && (
            <span style={{ fontStyle: "italic", marginLeft: "4px" }}>
              ({ingredient.displayState})
            </span>
          )}
        </Typography>
        {ingredient.initialState && !sortByCategory && (
          <Typography
            variant="body2"
            component="div"
            sx={{
              fontStyle: "italic",
              color: "text.secondary",
              fontSize: "0.85em",
              mt: 0,
              opacity: 0.8,
            }}
          >
            {ingredient.initialState}
          </Typography>
        )}
      </Box>

      {/* Checkbox (only in shopping list mode) */}
      {sortByCategory && (
        <Box sx={{ textAlign: "right" }}>
          <Checkbox
            checked={isChecked}
            onChange={(e) => onCheckChange(ingredient, e.target.checked)}
            size="small"
            sx={{ p: 0.2 }}
          />
        </Box>
      )}
    </Box>
  );
};

export default IngredientItem;
