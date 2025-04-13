import React from "react";
import { Box } from "@mui/material";
import SearchBar from "./SearchBar";
import { useRecipeList } from "../../contexts/RecipeListContext";

const SearchBarWithResults = () => {
  const {
    searchQuery,
    setSearchQuery,
    filteredRecipes,
    allRecipes,
    selectedDiet,
    selectedSeason,
    selectedType,
    selectedDishType,
    isQuickOnly,
    isLowIngredientsOnly,
  } = useRecipeList();

  const hasActiveFilters = Boolean(
    searchQuery ||
      selectedDiet ||
      selectedSeason ||
      selectedType ||
      selectedDishType ||
      isQuickOnly ||
      isLowIngredientsOnly
  );

  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        alignItems: "stretch",
      }}
    >
      <SearchBar
        value={searchQuery}
        onChange={setSearchQuery}
        onClear={() => setSearchQuery("")}
        filteredCount={filteredRecipes?.length || 0}
        totalCount={allRecipes?.length || 0}
        hasActiveFilters={hasActiveFilters}
      />
    </Box>
  );
};

export default SearchBarWithResults;
