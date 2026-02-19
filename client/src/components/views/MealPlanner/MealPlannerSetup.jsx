import React, { useState, useCallback } from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  IconButton,
  Button,
  Chip,
  TextField,
  InputAdornment,
} from "@mui/material";
import { motion } from "framer-motion";
import RemoveIcon from "@mui/icons-material/Remove";
import AddIcon from "@mui/icons-material/Add";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CloseIcon from "@mui/icons-material/Close";
import BlockIcon from "@mui/icons-material/Block";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import { getCurrentSeason, SEASON_EMOJI, NUTRITION_GOALS, normalizeIngredientName } from "./utils/mealPlannerUtils";
import { usePantry } from "../../../contexts/PantryContext";

const MEAL_COUNTS = [3, 4, 5, 6, 7];

const MealPlannerSetup = ({ config, onConfigChange, availableCount, onGenerate }) => {
  const currentSeason = getCurrentSeason();
  const seasonEmoji = SEASON_EMOJI[currentSeason];
  const seasonLabel = currentSeason.charAt(0).toUpperCase() + currentSeason.slice(1);
  const { pantrySize } = usePantry();

  const canGenerate = availableCount >= config.numberOfMeals;

  const [ingredientInput, setIngredientInput] = useState("");

  const addExcludedIngredient = useCallback(() => {
    const trimmed = ingredientInput.trim();
    if (!trimmed) return;

    const normalized = normalizeIngredientName(trimmed);
    const current = config.excludedIngredients || [];

    if (current.some((ing) => normalizeIngredientName(ing) === normalized)) {
      setIngredientInput("");
      return;
    }

    onConfigChange({ excludedIngredients: [...current, trimmed] });
    setIngredientInput("");
  }, [ingredientInput, config.excludedIngredients, onConfigChange]);

  const removeExcludedIngredient = useCallback(
    (index) => {
      const current = config.excludedIngredients || [];
      onConfigChange({ excludedIngredients: current.filter((_, i) => i !== index) });
    },
    [config.excludedIngredients, onConfigChange]
  );

  const handleInputKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addExcludedIngredient();
      }
    },
    [addExcludedIngredient]
  );

  const summaryParts = [
    `${config.numberOfMeals} meals`,
    `${config.servingsPerMeal} servings each`,
    config.dietPreference && config.dietPreference !== "any"
      ? config.dietPreference
      : null,
    config.prioritizeSeasonal ? `seasonal (${seasonLabel.toLowerCase()})` : null,
  ].filter(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: { xs: 3, sm: 4 },
          pt: { xs: 3, sm: 6 },
          px: { xs: 0, sm: 0 },
          maxWidth: 720,
          mx: "auto",
        }}
      >
        {/* ── Header ── */}
        <Box sx={{ textAlign: "center" }}>
          <Typography
            variant="h4"
            sx={{ fontWeight: 800, mb: 0.5, letterSpacing: "-0.02em" }}
          >
            Meal Planner
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Pick recipes that share ingredients to simplify your shopping.
          </Typography>
        </Box>

        {/* ── Hero row: Meals + Servings ── */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            gap: 0,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            overflow: "hidden",
          }}
        >
          {/* Number of meals */}
          <Box
            sx={{
              p: { xs: 2.5, sm: 3 },
              borderRight: { xs: "none", sm: "1px solid" },
              borderBottom: { xs: "1px solid", sm: "none" },
              borderColor: "divider",
            }}
          >
            <Typography
              variant="overline"
              sx={{ color: "text.secondary", fontWeight: 600, letterSpacing: 1.2, fontSize: "0.65rem" }}
            >
              Number of meals
            </Typography>
            <ToggleButtonGroup
              value={config.numberOfMeals}
              exclusive
              onChange={(_, val) => val !== null && onConfigChange({ numberOfMeals: val })}
              sx={{
                mt: 1.5,
                width: "100%",
                "& .MuiToggleButtonGroup-grouped": {
                  flex: 1,
                  minWidth: 0,
                  fontWeight: 700,
                  fontSize: "1rem",
                  py: 1.2,
                  "&.Mui-selected": {
                    bgcolor: "text.primary",
                    color: "background.paper",
                    "&:hover": { bgcolor: "text.primary", opacity: 0.9 },
                  },
                },
              }}
            >
              {MEAL_COUNTS.map((n) => (
                <ToggleButton key={n} value={n}>{n}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          {/* Servings per meal */}
          <Box
            sx={{
              p: { xs: 2.5, sm: 3 },
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Typography
              variant="overline"
              sx={{ color: "text.secondary", fontWeight: 600, letterSpacing: 1.2, fontSize: "0.65rem" }}
            >
              Servings per meal
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 2,
                mt: 1.5,
                flex: 1,
              }}
            >
              <IconButton
                size="small"
                onClick={() =>
                  onConfigChange({ servingsPerMeal: Math.max(1, config.servingsPerMeal - 1) })
                }
                disabled={config.servingsPerMeal <= 1}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: "8px",
                  width: 40,
                  height: 40,
                }}
              >
                <RemoveIcon fontSize="small" />
              </IconButton>
              <Typography variant="h4" sx={{ fontWeight: 800, minWidth: 32, textAlign: "center" }}>
                {config.servingsPerMeal}
              </Typography>
              <IconButton
                size="small"
                onClick={() =>
                  onConfigChange({ servingsPerMeal: Math.min(12, config.servingsPerMeal + 1) })
                }
                disabled={config.servingsPerMeal >= 12}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: "8px",
                  width: 40,
                  height: 40,
                }}
              >
                <AddIcon fontSize="small" />
              </IconButton>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ ml: "auto", fontSize: "0.85rem", fontWeight: 500 }}
              >
                {config.servingsPerMeal * config.numberOfMeals} total
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* ── Preferences section (diet + nutrition + excluded) ── */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
          <Typography
            variant="overline"
            sx={{ color: "text.secondary", fontWeight: 600, letterSpacing: 1.2, fontSize: "0.65rem" }}
          >
            Preferences
          </Typography>

          {/* Diet */}
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, fontSize: "0.85rem" }}>
              Diet
            </Typography>
            <ToggleButtonGroup
              value={config.dietPreference || "any"}
              exclusive
              onChange={(_, val) => onConfigChange({ dietPreference: val === "any" ? null : val })}
              sx={{
                width: "100%",
                "& .MuiToggleButtonGroup-grouped": {
                  flex: 1,
                  minWidth: 0,
                  textTransform: "none",
                  fontWeight: 500,
                  py: 1,
                  "&.Mui-selected": {
                    bgcolor: "text.primary",
                    color: "background.paper",
                    "&:hover": { bgcolor: "text.primary", opacity: 0.9 },
                  },
                },
              }}
            >
              {[
                { value: "any", label: "Any" },
                { value: "vegetarian", label: "Vegetarian" },
                { value: "vegan", label: "Vegan" },
              ].map(({ value, label }) => (
                <ToggleButton key={label} value={value}>{label}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          {/* Nutrition goals */}
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, fontSize: "0.85rem" }}>
              Nutrition goals
              <Typography
                component="span"
                variant="caption"
                sx={{ color: "text.disabled", ml: 1, fontSize: "0.7rem", fontWeight: 400 }}
              >
                optional
              </Typography>
            </Typography>
            <ToggleButtonGroup
              value={config.nutritionGoals || []}
              onChange={(_, newGoals) => {
                onConfigChange({ nutritionGoals: newGoals });
              }}
              sx={{
                width: "100%",
                "& .MuiToggleButtonGroup-grouped": {
                  flex: 1,
                  minWidth: 0,
                  textTransform: "none",
                  fontWeight: 500,
                  fontSize: "0.8rem",
                  py: 0.8,
                  "&.Mui-selected": {
                    bgcolor: "text.primary",
                    color: "background.paper",
                    "&:hover": { bgcolor: "text.primary", opacity: 0.9 },
                  },
                },
              }}
            >
              {NUTRITION_GOALS.map((goal) => (
                <ToggleButton key={goal.id} value={goal.id}>
                  {goal.emoji} {goal.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          {/* Excluded ingredients */}
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, fontSize: "0.85rem" }}>
              Ingredients to avoid
              <Typography
                component="span"
                variant="caption"
                sx={{ color: "text.disabled", ml: 1, fontSize: "0.7rem", fontWeight: 400 }}
              >
                optional
              </Typography>
            </Typography>
            <TextField
              size="small"
              placeholder="Type an ingredient and press Enter..."
              value={ingredientInput}
              onChange={(e) => setIngredientInput(e.target.value)}
              onKeyDown={handleInputKeyDown}
              fullWidth
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: "8px",
                  fontSize: "0.85rem",
                },
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <BlockIcon sx={{ fontSize: "1rem", color: "text.disabled" }} />
                  </InputAdornment>
                ),
                endAdornment: ingredientInput.trim() && (
                  <InputAdornment position="end">
                    <Button
                      size="small"
                      onClick={addExcludedIngredient}
                      sx={{
                        minWidth: 0,
                        textTransform: "none",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        borderRadius: "6px",
                        px: 1.5,
                      }}
                    >
                      Add
                    </Button>
                  </InputAdornment>
                ),
              }}
            />
            {config.excludedIngredients?.length > 0 && (
              <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", mt: 1.5 }}>
                {config.excludedIngredients.map((ing, index) => (
                  <Chip
                    key={`${ing}-${index}`}
                    label={ing}
                    onDelete={() => removeExcludedIngredient(index)}
                    deleteIcon={<CloseIcon sx={{ fontSize: "0.85rem !important" }} />}
                    variant="outlined"
                    color="error"
                    size="small"
                    sx={{
                      fontWeight: 500,
                      fontSize: "0.8rem",
                      borderRadius: "8px",
                      height: 30,
                      "& .MuiChip-deleteIcon": {
                        color: "error.main",
                        "&:hover": { color: "error.dark" },
                      },
                    }}
                  />
                ))}
              </Box>
            )}
          </Box>
        </Box>

        {/* ── Bottom bar: Pantry + Season + Generate ── */}
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
            pt: 1,
          }}
        >
          {/* Pantry + Season indicators */}
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              gap: 1.5,
            }}
          >
            {/* Pantry indicator */}
            {pantrySize > 0 && (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  px: 2,
                  py: 1.5,
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: "divider",
                  bgcolor: "background.paper",
                  flex: 1,
                }}
              >
                <KitchenOutlinedIcon sx={{ color: "text.secondary", fontSize: 18 }} />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", lineHeight: 1.2 }}>
                    Pantry active
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem" }}>
                    {pantrySize} item{pantrySize !== 1 ? "s" : ""} will be prioritized
                  </Typography>
                </Box>
              </Box>
            )}

            {/* Season toggle */}
            <Box
              onClick={() => onConfigChange({ prioritizeSeasonal: !config.prioritizeSeasonal })}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                px: 2,
                py: 1.5,
                borderRadius: 2,
                flex: 1,
                cursor: "pointer",
                border: "1px solid",
                borderColor: config.prioritizeSeasonal ? "text.primary" : "divider",
                bgcolor: "background.paper",
                transition: "all 0.2s ease",
                userSelect: "none",
                "&:hover": {
                  borderColor: config.prioritizeSeasonal ? "text.primary" : "text.secondary",
                },
              }}
            >
              <Typography sx={{ fontSize: 20, lineHeight: 1, opacity: config.prioritizeSeasonal ? 1 : 0.4 }}>
                {seasonEmoji}
              </Typography>
              <Box sx={{ flex: 1 }}>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 600,
                    fontSize: "0.8rem",
                    lineHeight: 1.2,
                    color: config.prioritizeSeasonal ? "text.primary" : "text.secondary",
                  }}
                >
                  {seasonLabel} recipes {config.prioritizeSeasonal ? "prioritized" : "not filtered"}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem" }}>
                  {config.prioritizeSeasonal
                    ? "Seasonal produce will be favored"
                    : "All recipes regardless of season"}
                </Typography>
              </Box>
              <Box
                sx={{
                  width: 36,
                  height: 20,
                  borderRadius: 10,
                  bgcolor: config.prioritizeSeasonal ? "text.primary" : "action.disabled",
                  position: "relative",
                  transition: "background-color 0.2s ease",
                  flexShrink: 0,
                }}
              >
                <Box
                  sx={{
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    bgcolor: config.prioritizeSeasonal ? "background.paper" : "white",
                    position: "absolute",
                    top: 2,
                    left: config.prioritizeSeasonal ? 18 : 2,
                    transition: "left 0.2s ease",
                    boxShadow: 1,
                  }}
                />
              </Box>
            </Box>
          </Box>

          {/* Generate button — full width, prominent */}
          <Button
            variant="contained"
            size="large"
            onClick={onGenerate}
            disabled={!canGenerate}
            startIcon={<AutoAwesomeIcon />}
            sx={{
              py: 2,
              borderRadius: 3,
              fontWeight: 700,
              fontSize: "1rem",
              textTransform: "none",
              bgcolor: canGenerate ? "text.primary" : undefined,
              color: canGenerate ? "background.paper" : undefined,
              boxShadow: "none",
              "&:hover": {
                bgcolor: canGenerate ? "text.primary" : undefined,
                opacity: 0.9,
                boxShadow: "none",
              },
            }}
          >
            {canGenerate
              ? `Generate plan`
              : `Not enough recipes (${availableCount}/${config.numberOfMeals})`}
          </Button>
          {canGenerate && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ textAlign: "center", fontSize: "0.75rem" }}
            >
              {summaryParts.join(" · ")} · {availableCount} recipes available
            </Typography>
          )}
        </Box>
      </Box>
    </motion.div>
  );
};

export default MealPlannerSetup;
