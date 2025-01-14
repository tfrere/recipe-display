import React, { useState, useMemo } from "react";
import {
  Box,
  Typography,
  Button,
  Tooltip,
  Snackbar,
  Alert,
  Switch,
  Checkbox,
  FormControlLabel,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { useRecipe } from "../../../contexts/RecipeContext";
import { useConstants } from "../../../contexts/ConstantsContext";

const INGREDIENTS_TEXTS = {
  TITLE: "Ingredients",
  COPY_SUCCESS: "Ingredients copied to clipboard!",
  SHOPPING_MODE: "Shopping list",
  COPY_BUTTON: "Copy list",
};

const switchStyle = {
  "& .MuiSwitch-track": {
    bgcolor: "background.paper",
    border: "1px solid",
    borderColor: "divider",
    opacity: "1 !important",
  },
  "& .MuiSwitch-thumb": {
    bgcolor: "background.paper",
    border: "1px solid",
    borderColor: "text.secondary",
  },
  "&.Mui-checked": {
    "& .MuiSwitch-thumb": {
      bgcolor: "background.paper",
      borderColor: "text.primary",
    },
    "& + .MuiSwitch-track": {
      bgcolor: "background.paper !important",
      borderColor: "text.primary",
      opacity: "1 !important",
    },
  },
};

const IngredientsList = ({ recipe, sortByCategory, setSortByCategory }) => {
  const { constants } = useConstants();

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  const {
    units: {
      weight: { gram: GRAM_UNITS },
    },
  } = constants;
  const CATEGORY_ORDER = constants.ingredients.categories.map((cat) => cat.id);
  const CATEGORY_LABELS = Object.fromEntries(
    constants.ingredients.categories.map((cat) => [cat.id, cat.label])
  );

  const {
    getAdjustedAmount,
    formatAmount,
    isIngredientUnused,
    completedSteps,
  } = useRecipe();

  // 1. Ordre des sous-recettes tel que défini dans la recette
  const subRecipeOrder = useMemo(() => {
    return recipe.subRecipes.map((subRecipe) => subRecipe.id);
  }, [recipe.subRecipes]);

  // 2. Ordre des catégories pour le tri
  const categoryOrder = useMemo(() => CATEGORY_ORDER, []);

  // 3. Construction de la liste complète des ingrédients avec leurs propriétés
  const allIngredients = useMemo(() => {
    if (!recipe.subRecipes || !recipe.ingredients) return [];

    return recipe.subRecipes.reduce((acc, subRecipe) => {
      if (!subRecipe.ingredients) return acc;

      subRecipe.ingredients.forEach((data) => {
        const ingredient = recipe.ingredients.find(
          (ing) => ing.id === data.ref
        );
        if (!ingredient) return;

        acc.push({
          id: data.ref,
          name: ingredient.name,
          amount: getAdjustedAmount(
            data.amount,
            ingredient.unit,
            ingredient.category
          ),
          unit: ingredient.unit,
          state: data.state,
          subRecipeId: subRecipe.id,
          subRecipeTitle: subRecipe.title,
          category: ingredient.category || "other",
        });
      });
      return acc;
    }, []);
  }, [recipe.subRecipes, recipe.ingredients, getAdjustedAmount]);

  // 4. Formatage des ingrédients (quantités, états, etc.)
  const formattedIngredients = useMemo(() => {
    return allIngredients.map((ingredient) => ({
      ...ingredient,
      displayAmount: formatAmount(ingredient.amount, ingredient.unit),
      isUnused: isIngredientUnused(ingredient.id, ingredient.subRecipeId),
      displayState: ingredient.state,
    }));
  }, [allIngredients, formatAmount, isIngredientUnused]);

  // 5. Tri des ingrédients selon le mode (shopping list ou sous-recettes)
  const sortedIngredients = useMemo(() => {
    if (!formattedIngredients.length) return [];

    if (sortByCategory) {
      // Mode shopping list : grouper par catégorie
      // 5.a. Agréger les ingrédients identiques
      const aggregatedIngredients = formattedIngredients.reduce(
        (acc, ingredient) => {
          const key = `${ingredient.name}|${ingredient.unit || ""}|${
            ingredient.category
          }`;
          if (!acc[key]) {
            acc[key] = { ...ingredient };
          } else {
            acc[key].amount += ingredient.amount;
            acc[key].displayAmount = formatAmount(
              acc[key].amount,
              acc[key].unit
            );
          }
          return acc;
        },
        {}
      );

      // 5.b. Grouper par catégorie
      const groupedByCategory = Object.values(aggregatedIngredients).reduce(
        (acc, ingredient) => {
          const category = ingredient.category || "other";
          if (!acc[category]) acc[category] = [];
          acc[category].push(ingredient);
          return acc;
        },
        {}
      );

      // 5.c. Trier les ingrédients dans chaque catégorie
      Object.values(groupedByCategory).forEach((ingredients) => {
        ingredients.sort((a, b) => a.name.localeCompare(b.name));
      });

      // 5.d. Trier les catégories et aplatir la liste
      return Object.entries(groupedByCategory)
        .sort(([catA], [catB]) => {
          const indexA = categoryOrder.indexOf(catA || "other");
          const indexB = categoryOrder.indexOf(catB || "other");
          return indexA - indexB;
        })
        .flatMap(([_, ingredients]) => ingredients);
    }

    // Mode sous-recettes : grouper par sous-recette
    const groupedBySubRecipe = formattedIngredients.reduce(
      (acc, ingredient) => {
        const subRecipeId = ingredient.subRecipeId;
        if (!acc[subRecipeId]) acc[subRecipeId] = [];
        acc[subRecipeId].push(ingredient);
        return acc;
      },
      {}
    );

    // Trier les sous-recettes selon l'ordre défini
    return subRecipeOrder
      .filter((id) => groupedBySubRecipe[id])
      .flatMap((id) => groupedBySubRecipe[id]);
  }, [
    formattedIngredients,
    sortByCategory,
    subRecipeOrder,
    categoryOrder,
    formatAmount,
  ]);

  // 6. Distribution des ingrédients en colonnes pour l'affichage
  const distributeInColumns = (items, columnCount) => {
    // 6.a. Grouper par sous-recette ou catégorie selon le mode
    const groups = items.reduce((acc, item) => {
      const key = sortByCategory ? item.category : item.subRecipeId;
      if (!acc[key]) {
        acc[key] = {
          key: key,
          title: sortByCategory
            ? CATEGORY_LABELS[key] || key.replace(/-/g, " ")
            : recipe.subRecipes.find((sr) => sr.id === key)?.title || key,
          items: [],
        };
      }
      acc[key].items.push(item);
      return acc;
    }, {});

    // 6.b. En mode sous-recette, trier les ingrédients de chaque groupe par catégorie
    if (!sortByCategory) {
      Object.values(groups).forEach((group) => {
        // Trier les ingrédients par catégorie puis par nom
        const sortedItems = group.items.sort((a, b) => {
          const catIndexA = categoryOrder.indexOf(a.category || "other");
          const catIndexB = categoryOrder.indexOf(b.category || "other");
          if (catIndexA === catIndexB) {
            return a.name.localeCompare(b.name);
          }
          return catIndexA - catIndexB;
        });
        group.items = sortedItems;
      });
    }

    // 6.c. Répartir les groupes en colonnes équilibrées
    const groupsList = Object.values(groups).sort(
      (a, b) => b.items.length - a.items.length
    );
    const columns = Array(columnCount)
      .fill()
      .map(() => ({
        groups: [],
        totalItems: 0,
      }));

    groupsList.forEach((group) => {
      const targetColumn = columns.reduce(
        (min, col, index) =>
          col.totalItems < columns[min].totalItems ? index : min,
        0
      );
      columns[targetColumn].groups.push(group);
      columns[targetColumn].totalItems += group.items.length;
    });

    return columns.map((col) => col.groups);
  };

  const columns = distributeInColumns(sortedIngredients, 3);

  const [checkedIngredients, setCheckedIngredients] = useState(new Set());

  const handleIngredientCheck = (ingredient, checked) => {
    const newChecked = new Set(checkedIngredients);
    if (checked) {
      newChecked.add(`${ingredient.subRecipeId}-${ingredient.name}`);
    } else {
      newChecked.delete(`${ingredient.subRecipeId}-${ingredient.name}`);
    }
    setCheckedIngredients(newChecked);
  };

  const handleCopyIngredients = () => {
    // Utilise les ingrédients déjà triés et agrégés
    const ingredientsList = sortedIngredients
      .map((ingredient) => {
        const amount = ingredient.displayAmount;
        const unit = ingredient.unit ? ` ${ingredient.unit}` : "";
        return `${amount}${unit} ${ingredient.name}`;
      })
      .join("\n");

    navigator.clipboard.writeText(ingredientsList);
  };

  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingIngredients = allIngredients.filter(
    (ing) => !ing.isUnused
  ).length;

  const [openSnackbar, setOpenSnackbar] = useState(false);

  const handleCloseSnackbar = (event, reason) => {
    if (reason === "clickaway") {
      return;
    }
    setOpenSnackbar(false);
  };

  return (
    <>
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
        {sortByCategory && (
          <Button
            onClick={() => {
              handleCopyIngredients();
              setOpenSnackbar(true);
            }}
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
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={sortByCategory}
              onChange={(e) => setSortByCategory(e.target.checked)}
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

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "1fr 1fr",
            md: "1fr 1fr 1fr",
          },
          gap: 3,
        }}
      >
        {columns.map((columnGroups, columnIndex) => (
          <Box
            key={columnIndex}
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 0.5,
              pr: 3,
              "@media (max-width: 600px)": {
                pr: 0,
              },
            }}
          >
            {columnGroups.map((group) => (
              <Box key={group.key} sx={{ mb: 4 }}>
                {(sortByCategory ||
                  Object.keys(recipe.subRecipes).length > 1) && (
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
                {group.items.map((ingredient) => {
                  return (
                    <Box
                      key={`${ingredient.subRecipeId}-${ingredient.id}`}
                      sx={{
                        display: "grid",
                        gridTemplateColumns: sortByCategory
                          ? "0.3fr 0.7fr auto"
                          : "0.3fr 0.7fr",
                        gap: 2,
                        alignItems: "start",
                        py: 0.25,
                        mb: 0.75,
                        opacity: sortByCategory
                          ? 1
                          : ingredient.isUnused
                          ? 0.5
                          : 1,
                        textDecoration: sortByCategory
                          ? "none"
                          : ingredient.isUnused
                          ? "line-through"
                          : "none",
                      }}
                    >
                      <Typography
                        variant="body1"
                        sx={{
                          color: "text.secondary",
                          textAlign: "left",
                        }}
                      >
                        {ingredient.displayAmount}
                      </Typography>
                      <Box sx={{ textAlign: "right" }}>
                        <Typography variant="body1" component="span">
                          {ingredient.name}
                          {!sortByCategory &&
                            ingredient.displayState &&
                            ingredient.displayState !== "none" &&
                            `,`}
                        </Typography>
                        {!sortByCategory &&
                          ingredient.displayState &&
                          ingredient.displayState !== "none" && (
                            <Typography
                              variant="body1"
                              component="div"
                              sx={{
                                color: "text.disabled",
                                fontSize: "0.85em",
                                mt: -0.5,
                                ml: 0,
                              }}
                            >
                              {ingredient.displayState}
                            </Typography>
                          )}
                      </Box>
                      {sortByCategory && (
                        <Checkbox
                          size="small"
                          checked={checkedIngredients.has(
                            `${ingredient.subRecipeId}-${ingredient.name}`
                          )}
                          onChange={(e) => {
                            handleIngredientCheck(ingredient, e.target.checked);
                          }}
                          sx={{
                            p: 0.5,
                            color: "text.disabled",
                            "&.Mui-checked": {
                              color: "text.secondary",
                            },
                          }}
                        />
                      )}
                    </Box>
                  );
                })}
              </Box>
            ))}
          </Box>
        ))}
      </Box>
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
