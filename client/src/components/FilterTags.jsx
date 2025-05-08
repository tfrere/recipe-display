import React from "react";
import { Box, Typography } from "@mui/material";
import { useRecipeList } from "../contexts/RecipeListContext";
import { useConstants } from "../contexts/ConstantsContext";
import FilterTag from "./common/FilterTag";

const FILTER_TEXTS = {
  FILTER_BY: "Filter",
  QUICK_RECIPES: "Quick recipes",
  LOW_INGREDIENTS: "Few ingr.",
  ALL: "All seasons",
};

const getTranslation = (prefix, key, constants) => {
  if (!key) return "";

  const RECIPE_TYPE_LABELS = Object.fromEntries(
    constants.recipe_types.map((type) => [type.id, type.label])
  );
  const DIET_LABELS = Object.fromEntries(
    constants.diets.map((diet) => [diet.id, diet.label])
  );
  const SEASON_LABELS = Object.fromEntries(
    constants.seasons.map((season) => [season.id, season.label])
  );

  switch (prefix) {
    case "recipe.dishType":
      return RECIPE_TYPE_LABELS[key] || key;
    case "recipe.diet":
      return DIET_LABELS[key] || key;
    case "recipe.season":
      return SEASON_LABELS[key] || key;
    default:
      return key;
  }
};

const FilterSection = ({
  items,
  selectedValue,
  onSelect,
  translatePrefix,
  type,
  constants,
}) => {
  // Ne pas afficher la section uniquement si c'est la saison et qu'il n'y a pas d'items
  if (type === "season" && items.length === 0) return null;

  // Si la section est vide (sauf saison), on affiche quand même les filtres avec count à 0
  const displayItems =
    items.length === 0 && type !== "season"
      ? type === "diet"
        ? [
            { key: "vegetarian", count: 0 },
            { key: "vegan", count: 0 },
          ]
        : type === "dishType"
        ? [
            { key: "appetizer", count: 0 },
            { key: "starter", count: 0 },
            { key: "main", count: 0 },
            { key: "dessert", count: 0 },
          ]
        : items
      : type === "diet"
      ? items.filter((item) => item.key !== "omnivorous")
      : items;

  return (
    <Box sx={{ display: "flex", gap: 0, flexWrap: "wrap" }}>
      {displayItems.map(({ key, count }) => {
        const isSelected = Array.isArray(selectedValue)
          ? selectedValue?.includes(key)
          : selectedValue === key;

        const handleSelect = () => {
          if (Array.isArray(selectedValue)) {
            if (isSelected) {
              onSelect(selectedValue.filter((v) => v !== key));
            } else {
              onSelect([...(selectedValue || []), key]);
            }
          } else {
            onSelect(isSelected ? null : key);
          }
        };

        return (
          <FilterTag
            key={key}
            label={getTranslation(translatePrefix, key, constants)}
            count={count}
            checked={isSelected}
            onChange={handleSelect}
            showCheckbox={true}
          />
        );
      })}
    </Box>
  );
};

const FilterTags = () => {
  const { constants } = useConstants();
  const {
    selectedDiet,
    setSelectedDiet,
    selectedSeason,
    setSelectedSeason,
    selectedDishType,
    setSelectedDishType,
    isQuickOnly,
    setIsQuickOnly,
    isLowIngredientsOnly,
    setIsLowIngredientsOnly,
    stats,
  } = useRecipeList();

  return (
    <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mt: 1 }}>
      {/* <Typography
        variant="body1"
        color="text.secondary"
        sx={{ whiteSpace: "nowrap", mt: 1 }}
      >
        {FILTER_TEXTS.FILTER_BY}
      </Typography> */}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Box
          sx={{
            display: "flex",
            gap: 2,
            columnGap: 4,
            flexWrap: "wrap",
            alignItems: "flex-start",
          }}
        >
          <FilterSection
            items={stats.dishType}
            selectedValue={selectedDishType}
            onSelect={setSelectedDishType}
            translatePrefix="recipe.dishType"
            type="dishType"
            constants={constants}
          />
          <Box sx={{ display: "flex", gap: 1 }}>
            <FilterTag
              label={FILTER_TEXTS.QUICK_RECIPES}
              count={stats.quick?.count}
              checked={isQuickOnly}
              onChange={() => setIsQuickOnly(!isQuickOnly)}
              showCheckbox={true}
            />
            <FilterTag
              label={FILTER_TEXTS.LOW_INGREDIENTS}
              count={stats.lowIngredients?.count}
              checked={isLowIngredientsOnly}
              onChange={() => setIsLowIngredientsOnly(!isLowIngredientsOnly)}
              showCheckbox={true}
            />
          </Box>
        </Box>
        <Box
          sx={{
            display: "flex",
            gap: 2,
            columnGap: 4,
            flexWrap: "wrap",
            alignItems: "flex-start",
          }}
        >
          <FilterSection
            items={stats.diet}
            selectedValue={selectedDiet}
            onSelect={setSelectedDiet}
            translatePrefix="recipe.diet"
            type="diet"
            constants={constants}
          />
          <FilterSection
            items={stats.season}
            selectedValue={selectedSeason}
            onSelect={setSelectedSeason}
            translatePrefix="recipe.season"
            type="season"
            constants={constants}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default FilterTags;
