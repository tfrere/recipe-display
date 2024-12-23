import React, { useState } from "react";
import {
  Box,
  Typography,
  Paper,
  Chip,
  Stack,
  alpha,
  Grid,
  Checkbox,
  IconButton,
} from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import KitchenIcon from "@mui/icons-material/Kitchen";
import InputIcon from "@mui/icons-material/Input";
import OutputIcon from "@mui/icons-material/Output";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { useRecipe } from "../../contexts/RecipeContext";

const StepCard = ({
  step,
  isCompleted,
  onToggleComplete,
  isExpanded,
  onToggleExpand,
}) => {
  const { recipe, selectedSubRecipe } = useRecipe();
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
        bgcolor: "background.paper",
      }}
    >
      {/* En-tête de l'étape */}
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
        <Typography
          variant="subtitle1"
          sx={{
            fontWeight: 500,
            textDecoration: isCompleted ? "line-through" : "none",
            color: isCompleted ? "grey.600" : "grey.900",
            flex: 1,
          }}
        >
          {step.action}
        </Typography>
        {step.time && (
          <Chip
            icon={<AccessTimeIcon />}
            label={step.time}
            size="small"
            variant="outlined"
            sx={{ mr: 1 }}
          />
        )}
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
                    <Chip
                      key={idx}
                      label={
                        info.amount
                          ? `${info.name} (${info.amount})`
                          : info.name
                      }
                      size="small"
                      variant="outlined"
                      color={
                        info.error
                          ? "error"
                          : info.type === "ingredient"
                          ? "primary"
                          : "secondary"
                      }
                      sx={{
                        mb: 0.5,
                        ...(info.error && {
                          borderStyle: "dashed",
                        }),
                      }}
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
                  <Chip
                    key={toolId}
                    label={recipe.tools[toolId].name}
                    size="small"
                    variant="outlined"
                    color="warning"
                    sx={{ mb: 0.5 }}
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
                  <Typography
                    variant="body2"
                    sx={{
                      color: "text.primary",
                      fontWeight: 600,
                    }}
                  >
                    {step.output.description}
                  </Typography>
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
