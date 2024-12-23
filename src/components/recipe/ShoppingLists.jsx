import React, { useState, useCallback, useMemo } from "react";
import { Box, Button, Typography, Stack, Snackbar } from "@mui/material";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import KitchenIcon from "@mui/icons-material/Kitchen";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ListDialog from "./ListDialog";
import { useRecipe } from "../../contexts/RecipeContext";

const ShoppingLists = () => {
  const { recipe } = useRecipe();
  const [dialogState, setDialogState] = useState({
    ingredients: false,
    tools: false,
  });
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
  });

  // Mémoiser les groupements pour éviter les recalculs inutiles
  const { groupedIngredients, groupedTools } = useMemo(() => {
    // Calculer les quantités totales pour chaque ingrédient
    const ingredientTotals = {};
    Object.values(recipe.subRecipes).forEach((subRecipe) => {
      Object.entries(subRecipe.ingredients || {}).forEach(([id, data]) => {
        if (!ingredientTotals[id]) {
          ingredientTotals[id] = 0;
        }
        ingredientTotals[id] += data.amount;
      });
    });

    const ingredients = Object.entries(recipe.ingredients || {}).reduce(
      (acc, [id, ingredient]) => {
        const category = ingredient.category || "Autres";
        if (!acc[category]) {
          acc[category] = [];
        }
        acc[category].push({
          id,
          ...ingredient,
          amount: ingredientTotals[id],
        });
        return acc;
      },
      {}
    );

    const tools = Object.entries(recipe.tools || {}).reduce(
      (acc, [id, tool]) => {
        const type = tool.type || "Autres";
        if (!acc[type]) {
          acc[type] = [];
        }
        acc[type].push({
          id,
          ...tool,
        });
        return acc;
      },
      {}
    );

    return { groupedIngredients: ingredients, groupedTools: tools };
  }, [recipe.ingredients, recipe.tools, recipe.subRecipes]);

  const handleCopy = useCallback(
    (type) => (e) => {
      e.stopPropagation();
      const data = type === "ingredients" ? groupedIngredients : groupedTools;
      const text = Object.entries(data)
        .map(
          ([category, items]) =>
            `${category}:\n${items
              .map((item) =>
                item.amount && item.unit
                  ? `- ${item.name} (${item.amount} ${item.unit})`
                  : `- ${item.name}`
              )
              .join("\n")}`
        )
        .join("\n\n");

      navigator.clipboard.writeText(text).then(
        () => {
          setSnackbar({
            open: true,
            message: `Liste ${
              type === "ingredients" ? "d'ingrédients" : "d'ustensiles"
            } copiée !`,
          });
        },
        (err) => {
          console.error("Erreur lors de la copie :", err);
          setSnackbar({
            open: true,
            message: "Erreur lors de la copie",
          });
        }
      );
    },
    [groupedIngredients, groupedTools]
  );

  const handleCloseSnackbar = useCallback(() => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  }, []);

  const handleToggleDialog = useCallback((type) => {
    setDialogState((prev) => ({
      ...prev,
      [type]: !prev[type],
    }));
  }, []);

  const renderList = useCallback(
    (items, handleCopy) => (
      <Stack spacing={2}>
        <Box sx={{ columnCount: 2, columnGap: 3, mb: 2 }}>
          {Object.entries(items).map(([category, categoryItems]) => (
            <Box
              key={category}
              sx={{
                breakInside: "avoid-column",
                mb: 2,
              }}
            >
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 600,
                  color: "text.primary",
                  mb: 1,
                  borderBottom: 1,
                  borderColor: "divider",
                  pb: 0.5,
                }}
              >
                {category}
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {categoryItems.map((item) => (
                  <Box
                    key={item.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      py: 0.5,
                    }}
                  >
                    <Typography variant="body1" sx={{ color: "text.primary" }}>
                      {item.name}
                    </Typography>
                    {item.amount && item.unit && (
                      <Typography
                        variant="body2"
                        sx={{ color: "text.secondary", ml: 2 }}
                      >
                        {item.amount} {item.unit}
                      </Typography>
                    )}
                  </Box>
                ))}
              </Box>
            </Box>
          ))}
        </Box>
        <Box
          sx={{
            display: "flex",
            justifyContent: "flex-end",
            borderTop: 1,
            borderColor: "divider",
            pt: 2,
          }}
        >
          <Button
            onClick={handleCopy}
            startIcon={<ContentCopyIcon />}
            variant="outlined"
            size="small"
          >
            Copier la liste
          </Button>
        </Box>
      </Stack>
    ),
    []
  );

  const ingredientsContent = useMemo(
    () => renderList(groupedIngredients, handleCopy("ingredients")),
    [groupedIngredients, handleCopy, renderList]
  );

  const toolsContent = useMemo(
    () => renderList(groupedTools, handleCopy("tools")),
    [groupedTools, handleCopy, renderList]
  );

  return (
    <Box sx={{ display: "flex", gap: 2 }}>
      <ListDialog
        open={dialogState.ingredients}
        onClose={() => handleToggleDialog("ingredients")}
        title="Liste de courses"
        content={ingredientsContent}
        buttonIcon={<ShoppingCartIcon />}
        buttonText="Liste de courses"
      />

      <ListDialog
        open={dialogState.tools}
        onClose={() => handleToggleDialog("tools")}
        title="Liste d'ustensiles"
        content={toolsContent}
        buttonIcon={<KitchenIcon />}
        buttonText="Ustensiles"
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={2000}
        onClose={handleCloseSnackbar}
        message={snackbar.message}
      />
    </Box>
  );
};

export default React.memo(ShoppingLists);
