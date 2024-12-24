import React from "react";
import { Box, Typography } from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import BarChartIcon from "@mui/icons-material/BarChart";
import ShoppingLists from "../recipe/ShoppingLists";
import RecipeStageButton from "../recipe/RecipeStageButton";
import { useRecipe } from "../../contexts/RecipeContext";

const RecipeSidebar = ({ layout }) => {
  const {
    recipe,
    selectedSubRecipe,
    setSelectedSubRecipe,
    getTotalProgress,
    getRemainingTime,
    parseTimeToMinutes,
    formatMinutesToTime,
    getSubRecipeRemainingTime,
  } = useRecipe();

  if (!recipe) return null;

  const totalProgress = getTotalProgress();
  const remainingTime = getRemainingTime();
  const totalTimeInMinutes = recipe.metadata.totalTime
    ? parseTimeToMinutes(recipe.metadata.totalTime)
    : 0;

  return (
    <Box
      sx={{
        minWidth: layout.leftColumn.minWidth,
        width: layout.leftColumn.width,
        maxWidth: layout.leftColumn.maxWidth,
        borderRight: 1,
        borderColor: "divider",
        overflow: "auto",
        bgcolor: "background.paper",
      }}
    >
      <Box
        sx={{
          height: "225px",
          width: "100%",
          bgcolor: "grey.100",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: 1,
          borderColor: "divider",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {recipe?.metadata?.image ? (
          <img
            src={`/images/${recipe.metadata.image}`}
            alt={recipe.metadata.title}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">
            Image de couverture
          </Typography>
        )}
      </Box>

      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: layout.spacing,
          p: layout.spacing,
        }}
      >
        <Box>
          <Typography
            variant="h4"
            sx={{
              fontWeight: "bold",
              mb: 2,
              color: "grey.900",
            }}
          >
            {recipe?.metadata?.title || "Non spécifié"}
          </Typography>

          <Box sx={{ display: "flex", gap: 3, mb: 2, flexWrap: "wrap" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <AccessTimeIcon
                fontSize="small"
                sx={{
                  color:
                    remainingTime !== totalTimeInMinutes &&
                    totalProgress.completed > 0
                      ? "primary.main"
                      : "grey.500",
                }}
              />
              <Typography
                variant="body2"
                sx={{
                  color:
                    remainingTime !== totalTimeInMinutes &&
                    totalProgress.completed > 0
                      ? "primary.main"
                      : "text.secondary",
                  fontWeight:
                    remainingTime !== totalTimeInMinutes &&
                    totalProgress.completed > 0
                      ? 600
                      : 400,
                }}
              >
                {formatMinutesToTime(remainingTime)} restant
              </Typography>
            </Box>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <RestaurantIcon fontSize="small" sx={{ color: "grey.500" }} />
              <Typography variant="body2" color="text.secondary">
                {recipe?.metadata?.servings || "Non spécifié"}
              </Typography>
            </Box>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <BarChartIcon fontSize="small" sx={{ color: "grey.500" }} />
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ textTransform: "capitalize" }}
              >
                {recipe?.metadata?.difficulty === "hard"
                  ? "Difficile"
                  : recipe?.metadata?.difficulty === "medium"
                  ? "Moyen"
                  : recipe?.metadata?.difficulty === "easy"
                  ? "Facile"
                  : "Non spécifié"}
              </Typography>
            </Box>
          </Box>

          <Typography variant="body1" sx={{ color: "grey.700" }}>
            {recipe?.metadata?.description || "Non spécifié"}
          </Typography>
        </Box>

        <ShoppingLists />

        <Box>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: "grey.500",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                fontWeight: 500,
              }}
            >
              Sous-recettes
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: "grey.500",
              }}
            >
              {totalProgress.completed}/{totalProgress.total} étapes
            </Typography>
          </Box>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {Object.entries(recipe.subRecipes).map(([id, subRecipe]) => {
              const remainingTime = getSubRecipeRemainingTime(id);

              return (
                <RecipeStageButton
                  key={id}
                  id={id}
                  title={subRecipe.title || id}
                  time={remainingTime}
                  selected={selectedSubRecipe === id}
                  onClick={() => setSelectedSubRecipe(id)}
                />
              );
            })}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default RecipeSidebar;
