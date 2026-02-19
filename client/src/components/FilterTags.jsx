import React, { useState } from "react";
import { Box, Typography, Collapse, IconButton } from "@mui/material";
import { useRecipeList } from "../contexts/RecipeListContext";
import { useConstants } from "../contexts/ConstantsContext";
import { usePantry } from "../contexts/PantryContext";
import FilterTag from "./common/FilterTag";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import TuneIcon from "@mui/icons-material/Tune";
import { useTheme, useMediaQuery } from "@mui/material";

const FILTER_TEXTS = {
  FILTER_BY: "Filter",
  QUICK_RECIPES: "Quick recipes",
  LOW_INGREDIENTS: "Few ingr.",
  PANTRY_FRIENDLY: "Pantry-friendly",
  ALL: "All seasons",
  SHOW_FILTERS: "Show filters",
  HIDE_FILTERS: "Hide filters",
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
    isPantrySort,
    setIsPantrySort,
    stats,
  } = useRecipeList();
  const { pantrySize } = usePantry();

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  // Calculate active filters count
  const activeFiltersCount = [
    selectedDiet,
    selectedSeason,
    selectedDishType,
    isQuickOnly,
    isLowIngredientsOnly,
    isPantrySort,
  ].filter((filter) => {
    if (Array.isArray(filter)) {
      return filter.length > 0;
    } else if (typeof filter === "boolean") {
      return filter === true;
    } else {
      return filter !== null && filter !== undefined;
    }
  }).length;

  const toggleFilters = () => {
    setFiltersExpanded(!filtersExpanded);
  };

  const FiltersContent = () => (
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
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <FilterTag
            label={FILTER_TEXTS.QUICK_RECIPES}
            count={stats.quick?.count}
            checked={isQuickOnly}
            onChange={() => setIsQuickOnly(!isQuickOnly)}
          />
          <FilterTag
            label={FILTER_TEXTS.LOW_INGREDIENTS}
            count={stats.lowIngredients?.count}
            checked={isLowIngredientsOnly}
            onChange={() => setIsLowIngredientsOnly(!isLowIngredientsOnly)}
          />
          {pantrySize > 0 && (
            <FilterTag
              label={FILTER_TEXTS.PANTRY_FRIENDLY}
              count={pantrySize}
              checked={isPantrySort}
              onChange={() => setIsPantrySort(!isPantrySort)}
            />
          )}
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
  );

  return (
    <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
      {/* <Typography
        variant="body1"
        color="text.secondary"
        sx={{ whiteSpace: "nowrap", mt: 1 }}
      >
        {FILTER_TEXTS.FILTER_BY}
      </Typography> */}

      {isMobile ? (
        <Box sx={{ width: "100%" }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "8px 12px",
              cursor: "pointer",
              bgcolor: "background.paper",
              borderRadius: "8px",
              border: "1px solid",
              borderColor: activeFiltersCount > 0 ? "primary.main" : "divider",
              mb: filtersExpanded ? 1 : 0,
              transition: "all 0.2s ease",
              "&:hover": {
                bgcolor: "action.hover",
              },
            }}
            onClick={toggleFilters}
          >
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <TuneIcon sx={{ mr: 1, color: "text.primary", opacity: 0.5 }} />
              <Typography variant="button" color="text.primary">
                {filtersExpanded
                  ? FILTER_TEXTS.HIDE_FILTERS
                  : FILTER_TEXTS.SHOW_FILTERS}
              </Typography>
              {activeFiltersCount > 0 && (
                <Box
                  sx={{
                    ml: 1,
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    borderRadius: "50%",
                    width: 24,
                    height: 24,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "0.75rem",
                    fontWeight: "bold",
                  }}
                >
                  {activeFiltersCount}
                </Box>
              )}
            </Box>
            <IconButton
              size="small"
              sx={{
                p: 0,
                transition: "transform 0.3s ease",
                "&:hover": {
                  transform: "rotate(180deg)",
                },
              }}
              onClick={(e) => {
                e.stopPropagation();
                toggleFilters();
              }}
            >
              {filtersExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse
            in={filtersExpanded}
            timeout="auto"
            unmountOnExit
            sx={{
              mt: 1,
              transition: "all 0.3s ease-in-out",
              "& .MuiCollapse-wrapperInner": {
                borderRadius: "8px",
                bgcolor: "background.paper",
                padding: "12px 16px",
                border: "1px solid",
                borderColor: "divider",
              },
            }}
          >
            <FiltersContent />
          </Collapse>
        </Box>
      ) : (
        <FiltersContent />
      )}
    </Box>
  );
};

export default FilterTags;
