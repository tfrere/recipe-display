import React from "react";
import { Box, Typography, Button } from "@mui/material";
import { useRecipe } from "../../../contexts/RecipeContext";
import { highlightMatches } from "../../../utils/textUtils.jsx";
import { parseTimeToMinutes } from "../../../utils/timeUtils";
import TimeDisplay from "../../common/TimeDisplay";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import RestaurantMenuOutlinedIcon from "@mui/icons-material/RestaurantMenuOutlined";
import BlenderOutlinedIcon from "@mui/icons-material/BlenderOutlined";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";

const PREPARATION_TEXTS = {
  TITLE: "Preparation",
  RESET: "Reset steps",
  TIME: {
    MINUTE: (count) => (count === 1 ? "1 minute" : `${count} minutes`),
    HOUR: (count) => (count === 1 ? "1 hour" : `${count} hours`),
    HOUR_MINUTE: (hours, minutes) =>
      `${hours} ${hours === 1 ? "hour" : "hours"} ${minutes} ${
        minutes === 1 ? "minute" : "minutes"
      }`,
  },
};

const PreparationSteps = ({ recipe }) => {
  const {
    completedSteps,
    toggleStepCompletion,
    completedSubRecipes,
    toggleSubRecipeCompletion,
    getSubRecipeRemainingTime,
    getSubRecipeStats,
    getCompletedSubRecipesCount,
    resetAllSteps,
  } = useRecipe();

  const handleSubRecipeClick = (subRecipeId, steps) => {
    const isCompleted = !completedSubRecipes[subRecipeId];
    toggleSubRecipeCompletion(subRecipeId, isCompleted);

    // Si on marque comme complété, on coche toutes les étapes
    steps.forEach((step) => {
      if (isCompleted !== !!completedSteps[step.id]) {
        toggleStepCompletion(step.id, isCompleted, subRecipeId);
      }
    });
  };

  const numSubRecipes = Object.keys(recipe.subRecipes || {}).length;
  const isSingleSubRecipe = numSubRecipes === 1;

  // Pour le cas d'une sous-recette unique, utiliser getSubRecipeStats
  const singleSubRecipeStats = isSingleSubRecipe
    ? getSubRecipeStats(Object.keys(recipe.subRecipes)[0])
    : null;

  // Vérifie si des étapes ont été complétées
  const hasCompletedSteps = Object.keys(completedSteps).length > 0;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {/* Titre */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, flexGrow: 1 }}
        >
          <Typography variant="h5" component="span">
            {PREPARATION_TEXTS.TITLE}
          </Typography>
          {!isSingleSubRecipe && (
            <Typography
              variant="body2"
              sx={{
                color: "text.disabled",
                display: "flex",
                alignItems: "center",
                gap: 0.5,
              }}
            >
              • {getCompletedSubRecipesCount()}/{numSubRecipes}
            </Typography>
          )}
        </Box>
        {hasCompletedSteps && (
          <Button
            onClick={resetAllSteps}
            size="small"
            startIcon={<RestartAltIcon />}
            variant="outlined"
            sx={{
              borderColor: "divider",
              color: "text.secondary",
              textTransform: "none",
              "&:hover": {
                borderColor: "text.secondary",
                bgcolor: "action.hover",
              },
            }}
          >
            {PREPARATION_TEXTS.RESET}
          </Button>
        )}
      </Box>

      {/* Liste des sous-recettes */}
      {Object.entries(recipe.subRecipes || {}).map(
        ([subRecipeId, subRecipe], index) => {
          const steps = subRecipe.steps || [];
          const isCompleted = completedSubRecipes[subRecipeId];
          const stats = getSubRecipeStats(subRecipeId);
          const remainingTime = getSubRecipeRemainingTime(subRecipeId);

          return (
            <Box
              key={subRecipeId}
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              {/* Titre de la sous-recette (si plus d'une) */}
              {!isSingleSubRecipe && (
                <Box
                  onClick={() => handleSubRecipeClick(subRecipeId, steps)}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    cursor: "pointer",
                    userSelect: "none",
                    "&:hover": {
                      "& .MuiTypography-root": {
                        color: "text.primary",
                      },
                    },
                  }}
                >
                  <Typography
                    variant="h6"
                    sx={{
                      color: isCompleted ? "text.disabled" : "text.primary",
                      textDecoration: isCompleted ? "line-through" : "none",
                      transition: "all 0.2s ease-in-out",
                    }}
                  >
                    {subRecipe.title}
                  </Typography>
                  {stats && (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography
                        variant="body2"
                        sx={{
                          color: isCompleted
                            ? "text.disabled"
                            : "text.secondary",
                          transition: "all 0.2s ease-in-out",
                        }}
                      >
                        • {stats.completedStepsCount}/{stats.totalSteps}
                      </Typography>
                    </Box>
                  )}
                </Box>
              )}

              {/* Liste des étapes */}
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {steps.map((step, stepIndex) => {
                  const isCompleted = completedSteps[step.id];

                  return (
                    <Box
                      key={step.id}
                      onClick={() =>
                        toggleStepCompletion(step.id, !isCompleted, subRecipeId)
                      }
                      sx={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 2,
                        cursor: "pointer",
                        userSelect: "none",
                        p: 1.5,
                        pl: { xs: 0, sm: 1.5 },
                        borderRadius: 1,
                        transition: "all 0.2s ease-in-out",
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          color: "text.disabled",
                          width: "16px",
                          flexShrink: 0,
                          textAlign: "right",
                          fontSize: "0.875rem",
                          lineHeight: { xs: 1.2, sm: 1.43 },
                          mr: { xs: -0.5, sm: 0 },
                        }}
                      >
                        ○
                      </Typography>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 2,
                          width: "100%",
                        }}
                      >
                        <Typography
                          variant="body1"
                          sx={{
                            color: isCompleted
                              ? "text.disabled"
                              : "text.primary",
                            textDecoration: isCompleted
                              ? "line-through"
                              : "none",
                            flexGrow: 1,
                            transition: "all 0.2s ease-in-out",
                          }}
                        >
                          {highlightMatches(step.action, recipe, {
                            inputs: step.inputs || [],
                            tools: step.tools || [],
                            output: step.output,
                          })}
                        </Typography>
                        {(step.time || step.stepType || step.stepMode) && (
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                              flexShrink: 0,
                              height: "100%",
                            }}
                          >
                            {step.stepMode === "passive" && (
                              <Typography
                                variant="body2"
                                sx={{
                                  color: "text.disabled",
                                  fontStyle: "italic",
                                }}
                              >
                                passive
                              </Typography>
                            )}
                            {step.stepMode === "passive" &&
                              (step.time || step.stepType) && (
                                <Typography
                                  variant="body2"
                                  sx={{
                                    color: "text.disabled",
                                  }}
                                >
                                  •
                                </Typography>
                              )}
                            {step.time &&
                              (step.stepMode === "passive" ||
                                parseTimeToMinutes(step.time) > 10) && (
                                <Typography
                                  variant="body2"
                                  sx={{
                                    color: "text.disabled",
                                  }}
                                >
                                  <TimeDisplay
                                    timeString={step.time}
                                    detailed={true}
                                  />
                                </Typography>
                              )}
                            {step.time &&
                              step.stepType &&
                              (step.stepMode === "passive" ||
                                parseTimeToMinutes(step.time) > 10) && (
                                <Typography
                                  variant="body2"
                                  sx={{
                                    color: "text.disabled",
                                  }}
                                >
                                  •
                                </Typography>
                              )}
                            {step.stepType && (
                              <>
                                {step.stepType === "prep" && (
                                  <RestaurantMenuOutlinedIcon
                                    sx={{
                                      fontSize: "1.2rem",
                                      color: "text.disabled",
                                    }}
                                  />
                                )}
                                {step.stepType === "combine" && (
                                  <BlenderOutlinedIcon
                                    sx={{
                                      fontSize: "1.2rem",
                                      color: "text.disabled",
                                    }}
                                  />
                                )}
                                {step.stepType === "cook" && (
                                  <LocalFireDepartmentOutlinedIcon
                                    sx={{
                                      fontSize: "1.2rem",
                                      color: isCompleted
                                        ? "text.disabled"
                                        : "warning.main",
                                    }}
                                  />
                                )}
                              </>
                            )}
                          </Box>
                        )}
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          );
        }
      )}
    </Box>
  );
};

export default PreparationSteps;
