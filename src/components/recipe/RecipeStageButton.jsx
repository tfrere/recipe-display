import React from "react";
import { Box, Typography, Checkbox } from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import { useRecipe } from "../../contexts/RecipeContext";

const RecipeStageButton = ({ id, title, time, selected, onClick }) => {
  const {
    completedSubRecipes,
    toggleSubRecipeCompletion,
    getSubRecipeProgress,
    formatMinutesToTime,
  } = useRecipe();
  const isCompleted = completedSubRecipes[id] || false;
  const progress = getSubRecipeProgress(id);

  const handleCheckboxClick = (e) => {
    e.stopPropagation();
    toggleSubRecipeCompletion(id, !isCompleted);
  };

  return (
    <Box
      onClick={onClick}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        p: 1,
        borderRadius: 1,
        cursor: "pointer",
        bgcolor: selected ? "primary.50" : "transparent",
        border: 1,
        borderColor: selected ? "primary.200" : "divider",
        "&:hover": {
          bgcolor: selected ? "primary.100" : "grey.50",
        },
        opacity: isCompleted ? 0.7 : 1,
        transition: "all 0.2s",
      }}
    >
      <Checkbox
        checked={isCompleted}
        onClick={handleCheckboxClick}
        sx={{
          ml: -0.5,
          color: selected ? "primary.main" : "grey.400",
          "&.Mui-checked": {
            color: selected ? "primary.main" : "grey.600",
          },
        }}
      />
      <Box sx={{ flex: 1, display: "flex", alignItems: "center", gap: 1 }}>
        <Typography
          variant="subtitle1"
          sx={{
            fontWeight: 600,
            color: "text.primary",
            flex: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {title}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            color: "grey.500",
          }}
        >
          {progress.completed}/{progress.total}
        </Typography>
      </Box>
      {time > 0 && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.5,
            color: selected ? "primary.main" : "text.secondary",
          }}
        >
          <AccessTimeIcon fontSize="small" />
          <Typography variant="body2">{formatMinutesToTime(time)}</Typography>
        </Box>
      )}
    </Box>
  );
};

export default RecipeStageButton;
