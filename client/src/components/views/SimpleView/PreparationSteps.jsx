import React from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Button } from "@mui/material";
import { useRecipe } from "../../../contexts/RecipeContext";
import { useTheme } from "../../../contexts/ThemeContext";
import { useGlossary } from "../../../hooks/useGlossary";
import { segmentStepText } from "../../../utils/textUtils";
import GlossaryTerm from "../../common/GlossaryTerm";
import { parseTimeToMinutes } from "../../../utils/timeUtils";
import TimeDisplay from "../../common/TimeDisplay";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import RestaurantMenuOutlinedIcon from "@mui/icons-material/RestaurantMenuOutlined";
import BlenderOutlinedIcon from "@mui/icons-material/BlenderOutlined";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";

const renderSegments = (segments, glossary, darkMode) =>
  segments.map((seg, i) => {
    if (seg.type === "ingredient") {
      return (
        <span
          key={i}
          style={{
            backgroundColor: darkMode ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.03)",
            fontWeight: 600,
            borderRadius: "2px",
          }}
        >
          {seg.text}
        </span>
      );
    }
    if (seg.type === "glossary" && seg.glossaryEntry) {
      return (
        <GlossaryTerm
          key={i}
          entry={seg.glossaryEntry}
          allTerms={glossary.terms}
          categoryMap={glossary.categoryMap}
          language={glossary.language}
        >
          {seg.text}
        </GlossaryTerm>
      );
    }
    return <React.Fragment key={i}>{seg.text}</React.Fragment>;
  });

const PreparationSteps = ({ recipe }) => {
  const { t } = useTranslation();
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
  const { darkMode } = useTheme();
  const glossary = useGlossary(recipe?.metadata?.language);

  const handleSubRecipeClick = (subRecipeId, steps) => {
    const isCompleted = !completedSubRecipes[subRecipeId];
    toggleSubRecipeCompletion(subRecipeId, isCompleted);

    steps.forEach((step) => {
      if (isCompleted !== !!completedSteps[step.id]) {
        toggleStepCompletion(step.id, isCompleted, subRecipeId);
      }
    });
  };

  const subRecipes = recipe.subRecipes || [];
  const numSubRecipes = subRecipes.length;
  const isSingleSubRecipe = numSubRecipes === 1;

  const singleSubRecipeStats = isSingleSubRecipe
    ? getSubRecipeStats(subRecipes[0]?.id)
    : null;

  const hasCompletedSteps = Object.keys(completedSteps).length > 0;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, "@media print": { gap: 1.5 } }}>
      {/* Titre */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, flexGrow: 1 }}
        >
          <Typography variant="h5" component="span" sx={{ "@media print": { fontSize: "1.1rem" } }}>
            {t("recipe.preparation")}
          </Typography>
          {!isSingleSubRecipe && (
            <Typography
              variant="body2"
              sx={{
                color: "text.disabled",
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                "@media print": { display: "none" },
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
              "@media print": { display: "none" },
            }}
          >
            {t("recipe.resetSteps")}
          </Button>
        )}
      </Box>

      {/* Liste des sous-recettes */}
      {(recipe.subRecipes || []).map((subRecipe, index) => {
          const subRecipeId = subRecipe.id;
          const steps = subRecipe.steps || [];
          const isCompleted = completedSubRecipes[subRecipeId];
          const stats = getSubRecipeStats(subRecipeId);
          const remainingTime = getSubRecipeRemainingTime(subRecipeId);

          return (
            <Box
              key={subRecipeId}
              sx={{ display: "flex", flexDirection: "column", gap: 2, "@media print": { gap: 0.5 } }}
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
                      "@media print": {
                        textDecoration: "none !important",
                        fontSize: "1rem",
                      },
                    }}
                  >
                    {subRecipe.title}
                  </Typography>
                  {stats && (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, "@media print": { display: "none" } }}>
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
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1, "@media print": { gap: 0 } }}>
                {steps.map((step, stepIndex) => {
                  const isCompleted = completedSteps[step.id];
                  const segments = segmentStepText(
                    step.action,
                    recipe,
                    {
                      inputs: step.inputs || [],
                      tools: step.tools || step.requires || [],
                      output: step.output,
                      uses: step.uses,
                      produces: step.produces,
                    },
                    glossary.matchTerms
                  );

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
                        "@media print": {
                          cursor: "default",
                          breakInside: "avoid",
                          pageBreakInside: "avoid",
                          p: 0.5,
                          pl: 0,
                        },
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
                          lineHeight: { xs: 1.2, md: 1.43 },
                          mr: { xs: -0.5, md: 0 },
                          "@media print": { color: "#999 !important" },
                        }}
                      >
                        <Box component="span" sx={{ "@media print": { display: "none" } }}>○</Box>
                        <Box component="span" sx={{ display: "none", "@media print": { display: "inline" } }}>{stepIndex + 1}.</Box>
                      </Typography>
                      <Box
                        sx={{
                          display: "flex",
                          gap: 0,
                          width: "100%",
                          flexDirection: { xs: "column", md: "row" },
                          alignItems: { xs: "flex-start", md: "center" },
                        }}
                      >
                        <Typography
                          variant="body1"
                          component="div"
                          sx={{
                            color: isCompleted
                              ? "text.disabled"
                              : "text.primary",
                            textDecoration: isCompleted
                              ? "line-through"
                              : "none",
                            flexGrow: 1,
                            width: { xs: "100%", md: "auto" },
                            transition: "all 0.2s ease-in-out",
                            maxHeight: 180,
                            overflowY: "auto",
                            "@media print": {
                              textDecoration: "none !important",
                              maxHeight: "none",
                              overflowY: "visible",
                            },
                            lineHeight: 1.6,
                          }}
                        >
                          {renderSegments(segments, glossary, darkMode)}
                        </Typography>
                        {(step.time || step.stepType || step.stepMode || step.isPassive) && (
                          <Box
                            sx={{
                              display: "flex",
                              flexDirection: "row",
                              alignItems: "center",
                              gap: 1,
                              flexShrink: 0,
                              alignSelf: { xs: "flex-start", md: "auto" },
                              ml: { xs: 0, md: 0 },
                              mt: { xs: 0.5, md: 0 },
                              "@media print": { display: "none" },
                            }}
                          >
                            {(step.stepMode === "passive" || step.isPassive) && (
                              <Typography
                                variant="body2"
                                sx={{
                                  color: "text.disabled",
                                  fontStyle: "italic",
                                  display: { xs: "none", md: "block" },
                                }}
                              >
                                {t("recipe.passive")}
                              </Typography>
                            )}
                            {(step.stepMode === "passive" || step.isPassive) &&
                              (step.time || step.stepType) && (
                                <Typography
                                  variant="body2"
                                  sx={{
                                    color: "text.disabled",
                                    display: { xs: "none", md: "block" },
                                  }}
                                >
                                  •
                                </Typography>
                              )}
                            {step.time &&
                              (step.stepMode === "passive" || step.isPassive ||
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
                              (step.stepMode === "passive" || step.isPassive ||
                                parseTimeToMinutes(step.time) > 10) && (
                                <Typography
                                  variant="body2"
                                  sx={{
                                    color: "text.disabled",
                                    display: { xs: "none", md: "block" },
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
                                      display: { xs: "none", md: "block" },
                                    }}
                                  />
                                )}
                                {step.stepType === "combine" && (
                                  <BlenderOutlinedIcon
                                    sx={{
                                      fontSize: "1.2rem",
                                      color: "text.disabled",
                                      display: { xs: "none", md: "block" },
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
                                      display: { xs: "none", md: "block" },
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
