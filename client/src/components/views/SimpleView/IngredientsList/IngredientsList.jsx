import React, { useState } from "react";
import {
  Box,
  Typography,
  Button,
  Snackbar,
  Alert,
  Switch,
  FormControlLabel,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import IngredientsGroup from "./IngredientsGroup";
import { useIngredientsProcessing } from "./useIngredientsProcessing";
import { INGREDIENTS_TEXTS, switchStyle } from "./constants";

/**
 * Main component for displaying recipe ingredients
 */
const IngredientsList = ({ recipe, shoppingMode, setShoppingMode }) => {
  const [checkedIngredients, setCheckedIngredients] = useState(new Set());
  const [openSnackbar, setOpenSnackbar] = useState(false);

  // Get processed ingredients data from custom hook
  const {
    columns,
    allIngredients,
    sortedIngredients,
    hasCompletedSteps,
    remainingIngredients,
  } = useIngredientsProcessing(recipe, shoppingMode);

  // Handle ingredient checkbox state
  const handleIngredientCheck = (ingredient, checked) => {
    const newChecked = new Set(checkedIngredients);
    if (checked) {
      newChecked.add(`${ingredient.subRecipeId}-${ingredient.name}`);
    } else {
      newChecked.delete(`${ingredient.subRecipeId}-${ingredient.name}`);
    }
    setCheckedIngredients(newChecked);
  };

  // Copy ingredients list to clipboard
  const handleCopyIngredients = () => {
    const ingredientsList = sortedIngredients
      .map((ingredient) => {
        return `${ingredient.displayAmount} ${ingredient.name}`;
      })
      .join("\n");

    navigator.clipboard.writeText(ingredientsList);
    setOpenSnackbar(true);
  };

  // Close snackbar notification
  const handleCloseSnackbar = (event, reason) => {
    if (reason === "clickaway") {
      return;
    }
    setOpenSnackbar(false);
  };

  return (
    <>
      {/* Header with title, statistics and mode controls */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          mb: 3,
          gap: 1.5,
        }}
      >
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, flexGrow: 1 }}
        >
          <Typography variant="h5" component="span">
            {INGREDIENTS_TEXTS.TITLE}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: "text.disabled",
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            • {hasCompletedSteps ? `${remainingIngredients}/` : ""}
            {allIngredients.length}
          </Typography>
        </Box>

        {/* Copy button (only in shopping list mode) */}
        {shoppingMode && (
          <Button
            onClick={handleCopyIngredients}
            size="small"
            startIcon={<ContentCopyIcon />}
            variant="outlined"
            sx={{
              borderColor: "divider",
              color: "text.secondary",
              textTransform: "none",
              "&:hover": {
                borderColor: "action.hover",
                backgroundColor: "action.hover",
              },
            }}
          >
            {INGREDIENTS_TEXTS.COPY_BUTTON}
          </Button>
        )}

        {/* Mode switch */}
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={shoppingMode}
              onChange={(e) => setShoppingMode(e.target.checked)}
              sx={switchStyle}
            />
          }
          label={
            <Typography variant="body2" color="text.secondary">
              {INGREDIENTS_TEXTS.SHOPPING_MODE}
            </Typography>
          }
          labelPlacement="start"
          sx={{
            ml: 1,
            mr: 0,
            gap: 1,
          }}
        />
      </Box>

      {/* Ingredients grid display with columns */}
      <Box
        sx={{
          position: "relative",
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "1fr 1fr",
            md: "1fr 1fr 1fr",
          },
          gap: 2,
          "& > *": {
            position: "relative",
            zIndex: 1,
          },
          "&::before, &::after": {
            content: '""',
            position: "absolute",
            top: 0,
            bottom: 0,
            width: "1px",
            backgroundColor: (theme) => theme.palette.divider,
            zIndex: 0,
            display: {
              xs: "none",
              sm: "block",
            },
          },
          "&::before": {
            left: "calc(50% - 1px)",
            display: {
              xs: "none",
              sm: "block",
              md: "none",
            },
          },
          "@media (min-width: 900px)": {
            "&::before": {
              left: "calc(33.33% - 1px)",
              display: "block",
            },
            "&::after": {
              left: "calc(66.66% - 1px)",
              display: "block",
            },
          },
        }}
      >
        {columns.map((columnGroups, columnIndex) => (
          <Box
            key={columnIndex}
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 0,
              px: 2,
              "@media (max-width: 600px)": {
                px: 0,
              },
            }}
          >
            {columnGroups.map((group, groupIndex) => (
              <IngredientsGroup
                key={group.key}
                group={group}
                recipe={recipe}
                sortByCategory={shoppingMode}
                checkedIngredients={checkedIngredients}
                onIngredientCheck={handleIngredientCheck}
              />
            ))}
          </Box>
        ))}
      </Box>

      {/* Success notification for clipboard copy */}
      <Snackbar
        open={openSnackbar}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        sx={{
          mb: 4,
        }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity="success"
          sx={{
            width: "100%",
            minWidth: "400px",
            fontSize: "1.1rem",
            border: 1,
            borderColor: "success.light",
            boxShadow: (theme) => `0 4px 20px ${theme.palette.success.light}25`,
            "& .MuiAlert-message": {
              fontSize: "1.1rem",
              py: 1,
            },
            "& .MuiAlert-icon": {
              fontSize: "1.5rem",
            },
          }}
        >
          {INGREDIENTS_TEXTS.COPY_SUCCESS}
        </Alert>
      </Snackbar>
    </>
  );
};

export default IngredientsList;
