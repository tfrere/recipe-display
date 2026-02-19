import React from "react";
import {
  Box,
  Typography,
  Button,
  IconButton,
} from "@mui/material";
import { motion } from "framer-motion";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RefreshIcon from "@mui/icons-material/Refresh";
import ShoppingCartOutlinedIcon from "@mui/icons-material/ShoppingCartOutlined";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import GrassOutlinedIcon from "@mui/icons-material/GrassOutlined";
import LinkIcon from "@mui/icons-material/Link";
import MealPlannerRecipeCard from "./MealPlannerRecipeCard";
import { formatTimeCompact } from "../../../utils/timeUtils";
import {
  getCurrentSeason,
  SEASON_EMOJI,
  countTotalSharedIngredients,
  computePlanNutrition,
} from "./utils/mealPlannerUtils";
import MacroBalanceBar from "./MacroBalanceBar";

const DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const StatPill = ({ icon, value, label }) => (
  <Box
    sx={{
      display: "flex",
      alignItems: "center",
      gap: 0.75,
      px: 1.5,
      py: 0.75,
      borderRadius: 2,
      border: "1px solid",
      borderColor: "divider",
      bgcolor: "background.paper",
    }}
  >
    {icon}
    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.85rem" }}>
      {value}
    </Typography>
    <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
      {label}
    </Typography>
  </Box>
);

const MealPlannerPlan = ({
  plan,
  config,
  lockedSlugs,
  onToggleLock,
  onSwap,
  onRegenerate,
  onNewPlan,
  onOpenShoppingList,
}) => {
  const currentSeason = getCurrentSeason();
  const seasonEmoji = SEASON_EMOJI[currentSeason];

  const totalTime = plan.reduce(
    (acc, item) => acc + (item.recipe.totalTimeMinutes || item.recipe.totalTime || item.recipe.totalCookingTime || 0),
    0
  );
  const seasonalCount = plan.filter((item) =>
    item.recipe.seasons?.includes(currentSeason)
  ).length;
  const sharedIngredientsCount = countTotalSharedIngredients(
    plan.map((item) => item.recipe)
  );

  const nutrition = computePlanNutrition(plan.map((item) => item.recipe));
  const hasNutrition = nutrition.recipesWithData > 0;

  const useDayLabels = plan.length <= 7;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      {/* ── Header ── */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mb: 3,
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <IconButton
            onClick={onNewPlan}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <ArrowBackIcon sx={{ fontSize: "1.1rem" }} />
          </IconButton>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 800, lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Your meal plan
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {plan.length} meals · {config.servingsPerMeal} servings each
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={onRegenerate}
            sx={{
              textTransform: "none",
              fontWeight: 600,
              borderRadius: 2,
              borderColor: "divider",
              color: "text.primary",
              "&:hover": { borderColor: "text.secondary" },
            }}
          >
            Shuffle
          </Button>
          <Button
            variant="contained"
            startIcon={<ShoppingCartOutlinedIcon />}
            onClick={onOpenShoppingList}
            sx={{
              textTransform: "none",
              fontWeight: 600,
              borderRadius: 2,
              bgcolor: "text.primary",
              color: "background.paper",
              "&:hover": { bgcolor: "text.primary", opacity: 0.9 },
            }}
          >
            Shopping list
          </Button>
        </Box>
      </Box>

      {/* ── Stats pills ── */}
      <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap", mb: 3 }}>
        <StatPill
          icon={<AccessTimeOutlinedIcon sx={{ fontSize: "1rem", color: "text.secondary" }} />}
          value={formatTimeCompact(totalTime)}
          label="total cook time"
        />
        <StatPill
          icon={<Typography sx={{ fontSize: "0.9rem", lineHeight: 1 }}>{seasonEmoji}</Typography>}
          value={`${seasonalCount}/${plan.length}`}
          label="seasonal"
        />
        <StatPill
          icon={<LinkIcon sx={{ fontSize: "1rem", color: "text.secondary" }} />}
          value={sharedIngredientsCount}
          label="shared ingredients"
        />
      </Box>

      {/* ── Nutrition ── */}
      {hasNutrition && <MacroBalanceBar nutrition={nutrition} />}

      {/* ── Recipe cards ── */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            md: "repeat(3, 1fr)",
            lg: "repeat(4, 1fr)",
          },
          gap: 2.5,
        }}
      >
        {plan.map((item, index) => (
          <Box key={item.recipe.slug} sx={{ display: "flex", flexDirection: "column" }}>
            {/* Day label */}
            <Typography
              variant="overline"
              sx={{
                display: "block",
                fontWeight: 700,
                letterSpacing: 1.5,
                fontSize: "0.6rem",
                color: "text.secondary",
                mb: 0.75,
                pl: 0.5,
              }}
            >
              {useDayLabels ? DAY_LABELS[index] : `Meal ${index + 1}`}
            </Typography>
            <Box sx={{ flex: 1 }}>
              <MealPlannerRecipeCard
                item={item}
                isLocked={lockedSlugs.has(item.recipe.slug)}
                onToggleLock={() => onToggleLock(item.recipe.slug)}
                onSwap={() => onSwap(index)}
              />
            </Box>
          </Box>
        ))}
      </Box>
    </motion.div>
  );
};

export default MealPlannerPlan;
