import React, { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
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
import RestaurantOutlinedIcon from "@mui/icons-material/RestaurantOutlined";
import { getCurrentSeason, SEASON_EMOJI, NUTRITION_GOALS, normalizeIngredientName } from "./utils/mealPlannerUtils";
import { usePantry } from "../../../contexts/PantryContext";

const MEAL_COUNTS = [3, 4, 5, 6, 7];

const toggleGroupSx = {
  width: "100%",
  "& .MuiToggleButtonGroup-grouped": {
    flex: 1,
    minWidth: 0,
    textTransform: "none",
    fontWeight: 600,
    fontSize: "0.85rem",
    py: 1,
    "&.Mui-selected": {
      bgcolor: "text.primary",
      color: "background.paper",
      "&:hover": { bgcolor: "text.primary", opacity: 0.9 },
    },
  },
};

const SectionLabel = ({ children }) => (
  <Typography
    variant="overline"
    sx={{ color: "text.secondary", fontWeight: 600, letterSpacing: 1.2, fontSize: "0.6rem", lineHeight: 1, mb: 1 }}
  >
    {children}
  </Typography>
);

const Divider = () => (
  <Box sx={{ height: "1px", bgcolor: "divider" }} />
);

const MealPlannerSetup = ({ config, onConfigChange, availableCount, onGenerate }) => {
  const { t } = useTranslation();
  const currentSeason = getCurrentSeason();
  const seasonEmoji = SEASON_EMOJI[currentSeason];
  const seasonLabel = currentSeason.charAt(0).toUpperCase() + currentSeason.slice(1);
  const { pantrySize } = usePantry();
  const pantryEnabled = config.usePantry !== false;

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
    t("mealPlanner.planSummary", { count: config.numberOfMeals, servings: config.servingsPerMeal }),
    config.dietPreference && config.dietPreference !== "any"
      ? t(`diets.${config.dietPreference}`)
      : null,
    config.prioritizeSeasonal ? t("mealPlanner.seasonal") : null,
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
          gap: 2,
          pt: { xs: 2, sm: 4 },
          maxWidth: 560,
          mx: "auto",
        }}
      >
        {/* ── Main card ── */}
        <Box
          sx={{
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            overflow: "hidden",
          }}
        >
          {/* Meals + Servings side by side */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            }}
          >
            <Box
              sx={(theme) => ({
                p: 2.5,
                borderRight: { xs: "none", sm: `1px solid ${theme.palette.divider}` },
                borderBottom: { xs: `1px solid ${theme.palette.divider}`, sm: "none" },
              })}
            >
              <SectionLabel>{t("mealPlanner.meals")}</SectionLabel>
              <ToggleButtonGroup
                value={config.numberOfMeals}
                exclusive
                onChange={(_, val) => val !== null && onConfigChange({ numberOfMeals: val })}
                sx={toggleGroupSx}
              >
                {MEAL_COUNTS.map((n) => (
                  <ToggleButton key={n} value={n}>{n}</ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>
            <Box sx={{ p: 2.5, display: "flex", flexDirection: "column" }}>
              <SectionLabel>{t("mealPlanner.servingsPerMeal")}</SectionLabel>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flex: 1 }}>
                <IconButton
                  size="small"
                  onClick={() => onConfigChange({ servingsPerMeal: Math.max(1, config.servingsPerMeal - 1) })}
                  disabled={config.servingsPerMeal <= 1}
                  sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, width: 36, height: 36 }}
                >
                  <RemoveIcon sx={{ fontSize: "1rem" }} />
                </IconButton>
                <Typography variant="h5" sx={{ fontWeight: 800, minWidth: 28, textAlign: "center" }}>
                  {config.servingsPerMeal}
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => onConfigChange({ servingsPerMeal: Math.min(12, config.servingsPerMeal + 1) })}
                  disabled={config.servingsPerMeal >= 12}
                  sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, width: 36, height: 36 }}
                >
                  <AddIcon sx={{ fontSize: "1rem" }} />
                </IconButton>
                <Typography variant="body2" color="text.disabled" sx={{ ml: "auto", fontSize: "0.8rem" }}>
                  {config.servingsPerMeal * config.numberOfMeals} {t("mealPlanner.total")}
                </Typography>
              </Box>
            </Box>
          </Box>

          <Divider />

          {/* Diet */}
          <Box sx={{ p: 2.5 }}>
            <SectionLabel>{t("mealPlanner.diet")}</SectionLabel>
            <ToggleButtonGroup
              value={config.dietPreference || "any"}
              exclusive
              onChange={(_, val) => onConfigChange({ dietPreference: val === "any" ? null : val })}
              sx={toggleGroupSx}
            >
              {[
                { value: "any", labelKey: "mealPlanner.dietAny" },
                { value: "vegetarian", labelKey: "diets.vegetarian" },
                { value: "vegan", labelKey: "diets.vegan" },
              ].map(({ value, labelKey }) => (
                <ToggleButton key={value} value={value}>{t(labelKey)}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          <Divider />

          {/* Nutrition goal */}
          <Box sx={{ p: 2.5 }}>
            <SectionLabel>{t("mealPlanner.nutritionGoal")}</SectionLabel>
            <ToggleButtonGroup
              value={config.nutritionGoals?.[0] || null}
              exclusive
              onChange={(_, val) => onConfigChange({ nutritionGoals: val ? [val] : [] })}
              sx={toggleGroupSx}
            >
              {NUTRITION_GOALS.map((goal) => (
                <ToggleButton key={goal.id} value={goal.id}>
                  {goal.emoji} {t(goal.id === "high-protein" ? "mealPlanner.goalHighProtein" : goal.id === "low-calorie" ? "mealPlanner.goalLight" : "mealPlanner.goalHighFiber")}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          <Divider />

          {/* Season + Pantry side by side */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: pantrySize > 0 ? { xs: "1fr", sm: "1fr 1fr" } : "1fr",
            }}
          >
            <Box
              onClick={() => onConfigChange({ prioritizeSeasonal: !config.prioritizeSeasonal })}
              sx={(theme) => ({
                p: 2.5,
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                cursor: "pointer",
                userSelect: "none",
                transition: "background-color 0.15s ease",
                "&:hover": { bgcolor: "action.hover" },
                ...(pantrySize > 0 && {
                  borderRight: { xs: "none", sm: `1px solid ${theme.palette.divider}` },
                  borderBottom: { xs: `1px solid ${theme.palette.divider}`, sm: "none" },
                }),
              })}
            >
              <Typography sx={{ fontSize: 18, lineHeight: 1, opacity: config.prioritizeSeasonal ? 1 : 0.35 }}>
                {seasonEmoji}
              </Typography>
              <Box sx={{ flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", lineHeight: 1.2 }}>
                  {t("mealPlanner.seasonalRecipes", { season: seasonLabel })}
                </Typography>
                <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.7rem" }}>
                  {config.prioritizeSeasonal ? t("mealPlanner.seasonalPrioritized") : t("mealPlanner.noSeasonalFilter")}
                </Typography>
              </Box>
              <Box
                sx={{
                  width: 34,
                  height: 18,
                  borderRadius: 9,
                  bgcolor: config.prioritizeSeasonal ? "text.primary" : "action.disabled",
                  position: "relative",
                  transition: "background-color 0.2s ease",
                  flexShrink: 0,
                }}
              >
                <Box
                  sx={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    bgcolor: "background.paper",
                    position: "absolute",
                    top: 2,
                    left: config.prioritizeSeasonal ? 18 : 2,
                    transition: "left 0.2s ease",
                    boxShadow: 1,
                  }}
                />
              </Box>
            </Box>

            {pantrySize > 0 && (
              <Box
                onClick={() => onConfigChange({ usePantry: !pantryEnabled })}
                sx={{
                  p: 2.5,
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  cursor: "pointer",
                  userSelect: "none",
                  transition: "background-color 0.15s ease",
                  "&:hover": { bgcolor: "action.hover" },
                }}
              >
                <KitchenOutlinedIcon sx={{ color: "text.secondary", fontSize: 18, opacity: pantryEnabled ? 1 : 0.35 }} />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", lineHeight: 1.2 }}>
                    {t("mealPlanner.pantry")}
                  </Typography>
                  <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.7rem" }}>
                    {pantryEnabled
                      ? t("mealPlanner.pantryPrioritized", { count: pantrySize })
                      : t("mealPlanner.pantryIgnored")}
                  </Typography>
                </Box>
                <Box
                  sx={{
                    width: 34,
                    height: 18,
                    borderRadius: 9,
                    bgcolor: pantryEnabled ? "text.primary" : "action.disabled",
                    position: "relative",
                    transition: "background-color 0.2s ease",
                    flexShrink: 0,
                  }}
                >
                  <Box
                    sx={{
                      width: 14,
                      height: 14,
                      borderRadius: "50%",
                      bgcolor: "background.paper",
                      position: "absolute",
                      top: 2,
                      left: pantryEnabled ? 18 : 2,
                      transition: "left 0.2s ease",
                      boxShadow: 1,
                    }}
                  />
                </Box>
              </Box>
            )}
          </Box>

          <Divider />

          {/* Meals only filter */}
          <Box
            onClick={() => onConfigChange({ mealsOnly: !config.mealsOnly })}
            sx={{
              p: 2.5,
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              cursor: "pointer",
              userSelect: "none",
              transition: "background-color 0.15s ease",
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            <RestaurantOutlinedIcon sx={{ color: "text.secondary", fontSize: 18, opacity: config.mealsOnly ? 1 : 0.35 }} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", lineHeight: 1.2 }}>
                {t("mealPlanner.mealsOnly")}
              </Typography>
              <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.7rem" }}>
                {config.mealsOnly ? t("mealPlanner.mealsOnlyEnabled") : t("mealPlanner.mealsOnlyDisabled")}
              </Typography>
            </Box>
            <Box
              sx={{
                width: 34,
                height: 18,
                borderRadius: 9,
                bgcolor: config.mealsOnly ? "text.primary" : "action.disabled",
                position: "relative",
                transition: "background-color 0.2s ease",
                flexShrink: 0,
              }}
            >
              <Box
                sx={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  bgcolor: "background.paper",
                  position: "absolute",
                  top: 2,
                  left: config.mealsOnly ? 18 : 2,
                  transition: "left 0.2s ease",
                  boxShadow: 1,
                }}
              />
            </Box>
          </Box>

          <Divider />

          {/* Excluded ingredients */}
          <Box sx={{ p: 2.5 }}>
            <SectionLabel>{t("mealPlanner.ingredientsToAvoid")}</SectionLabel>
            <TextField
              size="small"
              placeholder={t("mealPlanner.excludedPlaceholder")}
              value={ingredientInput}
              onChange={(e) => setIngredientInput(e.target.value)}
              onKeyDown={handleInputKeyDown}
              fullWidth
              sx={{
                "& .MuiOutlinedInput-root": { borderRadius: 2, fontSize: "0.85rem" },
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <BlockIcon sx={{ fontSize: "0.9rem", color: "text.disabled" }} />
                  </InputAdornment>
                ),
                endAdornment: ingredientInput.trim() && (
                  <InputAdornment position="end">
                    <Button
                      size="small"
                      onClick={addExcludedIngredient}
                      sx={{ minWidth: 0, textTransform: "none", fontSize: "0.75rem", fontWeight: 600, borderRadius: 1.5, px: 1.5 }}
                    >
                      {t("addRecipe.add")}
                    </Button>
                  </InputAdornment>
                ),
              }}
            />
            {config.excludedIngredients?.length > 0 && (
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 1.5 }}>
                {config.excludedIngredients.map((ing, index) => (
                  <Chip
                    key={`${ing}-${index}`}
                    label={ing}
                    onDelete={() => removeExcludedIngredient(index)}
                    deleteIcon={<CloseIcon sx={{ fontSize: "0.8rem !important" }} />}
                    variant="outlined"
                    size="small"
                    sx={{
                      fontWeight: 500,
                      fontSize: "0.78rem",
                      borderRadius: 2,
                      height: 28,
                      borderColor: "error.main",
                      color: "error.main",
                      "& .MuiChip-deleteIcon": { color: "error.main", "&:hover": { color: "error.dark" } },
                    }}
                  />
                ))}
              </Box>
            )}
          </Box>
        </Box>

        {/* ── Generate button ── */}
        <Button
          variant="contained"
          size="large"
          onClick={onGenerate}
          disabled={!canGenerate}
          startIcon={<AutoAwesomeIcon />}
          sx={{
            py: 1.75,
            borderRadius: 3,
            fontWeight: 700,
            fontSize: "0.95rem",
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
            ? t("mealPlanner.generatePlan")
            : t("mealPlanner.notEnoughRecipes", { count: availableCount, needed: config.numberOfMeals })}
        </Button>
        {canGenerate && (
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ textAlign: "center", fontSize: "0.7rem", mt: -1 }}
          >
            {summaryParts.join(" · ")} · {availableCount} {t("mealPlanner.recipesAvailable")}
          </Typography>
        )}
      </Box>
    </motion.div>
  );
};

export default MealPlannerSetup;
