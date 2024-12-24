import React, { useState } from "react";
import {
  Box,
  Typography,
  Paper,
  Stack,
  Grid,
  Checkbox,
  IconButton,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { useRecipe } from "../../contexts/RecipeContext";
import RecipeChip, { CHIP_TYPES } from "../common/RecipeChip";

const highlightMatches = (text, recipe, step) => {
  if (!text || !recipe) return text;

  // Create arrays of names to match
  const ingredientNames = step.inputs
    .filter((input) => input.type === "ingredient")
    .map((input) => recipe.ingredients[input.ref]?.name)
    .filter(Boolean);

  const toolNames = (step.tools || [])
    .map((toolId) => recipe.tools[toolId]?.name)
    .filter(Boolean);

  const stateNames = [
    ...step.inputs
      .filter((input) => input.type === "state")
      .map((input) => input.ref),
    step.output ? step.output.description : null,
  ].filter(Boolean);

  // Combine all terms to match
  const terms = [...ingredientNames, ...toolNames, ...stateNames]
    .map((term) => term.toLowerCase().split(/\s+/))
    .flat()
    .filter((term) => term.length >= 3);

  // Sort terms by length (longest first) to avoid partial matches
  terms.sort((a, b) => b.length - a.length);

  // Split the text into segments and create spans for matches
  let segments = [{ text, isMatch: false }];

  terms.forEach((term) => {
    segments = segments.flatMap((segment) => {
      if (segment.isMatch) return [segment];

      // Create a regex that matches the exact term within word boundaries
      const regex = new RegExp(`(${term})`, "gi");
      const parts = segment.text.split(regex);

      // Reconstruct the segments with matches
      return parts.map((part) => ({
        text: part,
        isMatch: part.toLowerCase() === term.toLowerCase(),
      }));
    });
  });

  // Return the text with highlighted matches
  return (
    <span>
      {segments.map((segment, index) =>
        segment.isMatch ? (
          <span
            key={index}
            style={{ fontWeight: "bold", color: "primary.main" }}
          >
            {segment.text}
          </span>
        ) : (
          segment.text
        )
      )}
    </span>
  );
};

const StepCard = ({
  step,
  isCompleted,
  onToggleComplete,
  isExpanded,
  onToggleExpand,
}) => {
  const { recipe, selectedSubRecipe, completedSteps } = useRecipe();
  const subRecipe = recipe.subRecipes[selectedSubRecipe];

  const getIngredientInfo = (input) => {
    if (input.type === "ingredient") {
      const ingredient = recipe.ingredients?.[input.ref];
      if (!ingredient) {
        console.warn(`Ingrédient manquant dans la recette: ${input.ref}`);
        return {
          name: input.ref,
          amount: null,
          error: true,
          type: "ingredient",
        };
      }

      const amount = subRecipe.ingredients?.[input.ref]?.amount;
      return {
        name: ingredient.name,
        amount: amount ? `${amount}${ingredient.unit || ""}` : null,
        error: false,
        type: "ingredient",
      };
    } else if (input.type === "state") {
      return {
        name: input.ref,
        amount: null,
        error: false,
        type: "state",
      };
    }

    return {
      name: input.ref,
      amount: null,
      error: false,
      type: input.type,
    };
  };

  return (
    <Paper
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 2,
        overflow: "hidden",
        opacity: isCompleted ? 0.7 : 1,
        transition: "opacity 0.2s",
        bgcolor: isCompleted ? "grey.50" : "background.paper",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          p: 2,
          borderBottom: isExpanded ? "1px solid" : "none",
          borderColor: "divider",
          bgcolor: isCompleted ? "grey.50" : "transparent",
        }}
      >
        <Checkbox
          checked={isCompleted}
          onChange={(e) => onToggleComplete(e.target.checked)}
          sx={{ ml: -1 }}
        />
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="body1"
            sx={{
              textDecoration: completedSteps[step.id] ? "line-through" : "none",
            }}
          >
            {highlightMatches(step.action, recipe, step)}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <RecipeChip
            label={
              step.type === "cooking"
                ? "Cuisson"
                : step.type === "preparation"
                ? "Préparation"
                : "Assemblage"
            }
            type={
              step.type === "cooking"
                ? CHIP_TYPES.ACTION_COOKING
                : step.type === "preparation"
                ? CHIP_TYPES.ACTION_PREPARATION
                : CHIP_TYPES.ACTION_ASSEMBLY
            }
          />
          {step.time && (
            <RecipeChip label={step.time} type={CHIP_TYPES.STATE} />
          )}
        </Box>
        <IconButton
          size="small"
          onClick={onToggleExpand}
          sx={{
            color: "grey.400",
            "&:hover": {
              color: "primary.main",
            },
          }}
        >
          {isExpanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
        </IconButton>
      </Box>

      {/* Contenu détaillé de l'étape */}
      {isExpanded && (
        <Box sx={{ p: 2, opacity: isCompleted ? 0.7 : 1 }}>
          <Grid container spacing={2} alignItems="center">
            {/* Colonne 1: Ingrédients */}
            <Grid item xs={12} md={3.5}>
              <Stack
                direction="row"
                spacing={1}
                flexWrap="wrap"
                useFlexGap
                alignItems="center"
                sx={{ minHeight: "40px" }}
              >
                {step.inputs.map((input, idx) => {
                  const info = getIngredientInfo(input);
                  return (
                    <RecipeChip
                      key={idx}
                      label={
                        info.amount
                          ? `${info.name} (${info.amount})`
                          : info.name
                      }
                      type={
                        info.type === "ingredient"
                          ? CHIP_TYPES.INGREDIENT
                          : CHIP_TYPES.STATE
                      }
                      isUnused={info.error}
                    />
                  );
                })}
              </Stack>
            </Grid>

            {/* Séparateur 1 */}
            <Grid
              item
              xs={12}
              md={0.5}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "40px",
              }}
            >
              <Typography
                variant="h5"
                sx={{ color: "text.secondary", fontWeight: "light" }}
              >
                +
              </Typography>
            </Grid>

            {/* Colonne 2: Ustensiles */}
            <Grid item xs={12} md={3.5}>
              <Stack
                direction="row"
                spacing={1}
                flexWrap="wrap"
                useFlexGap
                alignItems="center"
                sx={{ minHeight: "40px" }}
              >
                {(step.tools || []).map((toolId) => (
                  <RecipeChip
                    key={toolId}
                    label={recipe.tools[toolId].name}
                    type={CHIP_TYPES.TOOL}
                  />
                ))}
              </Stack>
            </Grid>

            {/* Séparateur 2 */}
            <Grid
              item
              xs={12}
              md={0.5}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "40px",
              }}
            >
              <Typography
                variant="h5"
                sx={{ color: "text.secondary", fontWeight: "light" }}
              >
                →
              </Typography>
            </Grid>

            {/* Colonne 3: Résultat */}
            <Grid item xs={12} md={3.5}>
              {step.output && (
                <Box
                  sx={{
                    minHeight: "40px",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <RecipeChip
                    label={step.output.description}
                    type={CHIP_TYPES.STATE}
                  />
                </Box>
              )}
            </Grid>
          </Grid>
        </Box>
      )}
    </Paper>
  );
};

const StepByStepView = () => {
  const { recipe, selectedSubRecipe, completedSteps, toggleStepCompletion } =
    useRecipe();
  const [globalExpanded, setGlobalExpanded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});

  if (!recipe || !selectedSubRecipe || !recipe.subRecipes[selectedSubRecipe]) {
    return null;
  }

  const subRecipe = recipe.subRecipes[selectedSubRecipe];

  const handleGlobalExpand = (checked) => {
    setGlobalExpanded(checked);
    const newExpandedSteps = {};
    subRecipe.steps.forEach((step) => {
      newExpandedSteps[step.id] = checked;
    });
    setExpandedSteps(newExpandedSteps);
  };

  const handleStepExpand = (stepId) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  };

  return (
    <Box
      sx={{
        p: 3,
        bgcolor: "grey.50",
        minHeight: "100%",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 1,
          mb: 3,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {globalExpanded ? "Mode détaillé" : "Mode simplifié"}
        </Typography>
        <Checkbox
          checked={globalExpanded}
          onChange={(e) => handleGlobalExpand(e.target.checked)}
          size="small"
          sx={{
            color: "grey.400",
            "&.Mui-checked": {
              color: "primary.main",
            },
          }}
        />
      </Box>

      <Stack spacing={3}>
        {subRecipe.steps.map((step) => (
          <StepCard
            key={step.id}
            step={step}
            isCompleted={completedSteps[step.id] || false}
            onToggleComplete={(completed) =>
              toggleStepCompletion(step.id, completed, selectedSubRecipe)
            }
            isExpanded={expandedSteps[step.id] || false}
            onToggleExpand={() => handleStepExpand(step.id)}
          />
        ))}
      </Stack>
    </Box>
  );
};

export default StepByStepView;
