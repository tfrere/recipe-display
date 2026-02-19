import React, { useState, useCallback, useMemo, useEffect } from "react";
import { Box, Container, CircularProgress, Typography } from "@mui/material";
import { AnimatePresence } from "framer-motion";
import { useRecipeList } from "../contexts/RecipeListContext";
import { usePantry } from "../contexts/PantryContext";
import { getRecipe } from "../services/recipeService";
import MealPlannerSetup from "../components/views/MealPlanner/MealPlannerSetup";
import MealPlannerPlan from "../components/views/MealPlanner/MealPlannerPlan";
import ShoppingListDrawer from "../components/views/MealPlanner/ShoppingListDrawer";
import {
  generateMealPlan,
  swapRecipe,
} from "../components/views/MealPlanner/utils/mealPlannerUtils";

const MealPlannerPage = () => {
  const { allRecipes } = useRecipeList();
  const { pantryItems } = usePantry();

  // ─── State ───────────────────────────────────────────────────
  const [step, setStep] = useState("setup"); // "setup" | "loading" | "plan"
  const [config, setConfig] = useState(() => {
    // Restore excluded ingredients from localStorage
    let savedExcluded = [];
    try {
      const stored = localStorage.getItem("mealPlanner_excludedIngredients");
      if (stored) savedExcluded = JSON.parse(stored);
    } catch { /* ignore */ }

    return {
      numberOfMeals: 4,
      servingsPerMeal: 4,
      dietPreference: null,
      prioritizeSeasonal: true,
      nutritionGoals: [],
      excludedIngredients: savedExcluded,
    };
  });
  const [plan, setPlan] = useState([]); // Array of { recipe, reasons, sharedCount }
  const [fullRecipes, setFullRecipes] = useState([]); // Full recipe data for shopping list
  const [lockedSlugs, setLockedSlugs] = useState(new Set());
  const [shoppingListOpen, setShoppingListOpen] = useState(false);

  // ─── Derived ─────────────────────────────────────────────────
  const availableCount = useMemo(() => {
    if (!config.dietPreference) return allRecipes.length;
    return allRecipes.filter((r) =>
      r.diets?.includes(config.dietPreference)
    ).length;
  }, [allRecipes, config.dietPreference]);

  // ─── Config update ───────────────────────────────────────────
  const handleConfigChange = useCallback((updates) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  // Persist excluded ingredients to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(
        "mealPlanner_excludedIngredients",
        JSON.stringify(config.excludedIngredients)
      );
    } catch { /* ignore quota errors */ }
  }, [config.excludedIngredients]);

  // ─── Load full recipe data for shopping list ─────────────────
  const loadFullRecipes = useCallback(async (planItems) => {
    try {
      const recipes = await Promise.all(
        planItems.map((item) => getRecipe(item.recipe.slug))
      );
      setFullRecipes(
        planItems.map((item, i) => ({
          recipe: recipes[i],
          reasons: item.reasons,
          sharedCount: item.sharedCount,
        }))
      );
    } catch (error) {
      console.error("Error loading full recipes:", error);
      // Fallback: use list data (shopping list will have limited info)
      setFullRecipes(planItems);
    }
  }, []);

  // ─── Generate plan ───────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    setStep("loading");

    // Small delay for animation
    await new Promise((resolve) => setTimeout(resolve, 300));

    const lockedRecipes = plan
      .filter((item) => lockedSlugs.has(item.recipe.slug))
      .map((item) => item.recipe);

    const newPlan = generateMealPlan(allRecipes, config, lockedRecipes, pantryItems);
    setPlan(newPlan);

    // Load full recipe data in background for shopping list
    loadFullRecipes(newPlan);

    setStep("plan");
  }, [allRecipes, config, plan, lockedSlugs, loadFullRecipes, pantryItems]);

  // ─── Regenerate (keep locked) ────────────────────────────────
  const handleRegenerate = useCallback(async () => {
    const lockedRecipes = plan
      .filter((item) => lockedSlugs.has(item.recipe.slug))
      .map((item) => item.recipe);

    const newPlan = generateMealPlan(allRecipes, config, lockedRecipes, pantryItems);
    setPlan(newPlan);
    loadFullRecipes(newPlan);
  }, [allRecipes, config, plan, lockedSlugs, loadFullRecipes, pantryItems]);

  // ─── Swap a single recipe ───────────────────────────────────
  const handleSwap = useCallback(
    (index) => {
      const newPlan = swapRecipe(allRecipes, config, plan, index, pantryItems);
      setPlan(newPlan);
      loadFullRecipes(newPlan);
    },
    [allRecipes, config, plan, loadFullRecipes, pantryItems]
  );

  // ─── Toggle lock ─────────────────────────────────────────────
  const handleToggleLock = useCallback((slug) => {
    setLockedSlugs((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        next.add(slug);
      }
      return next;
    });
  }, []);

  // ─── Back to setup ──────────────────────────────────────────
  const handleNewPlan = useCallback(() => {
    setStep("setup");
    setPlan([]);
    setFullRecipes([]);
    setLockedSlugs(new Set());
  }, []);

  // ─── Render ──────────────────────────────────────────────────
  return (
    <Box
      sx={{
        minHeight: "calc(100vh - 64px)",
        bgcolor: "background.default",
        pb: 4,
      }}
    >
      <Container maxWidth="lg" sx={{ pt: { xs: 1, sm: 2 } }}>
        <AnimatePresence mode="wait">
          {step === "setup" && (
            <MealPlannerSetup
              key="setup"
              config={config}
              onConfigChange={handleConfigChange}
              availableCount={availableCount}
              onGenerate={handleGenerate}
            />
          )}

          {step === "loading" && (
            <Box
              key="loading"
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "50vh",
                gap: 2,
              }}
            >
              <CircularProgress size={40} />
              <Typography variant="body2" color="text.secondary">
                Generating your meal plan...
              </Typography>
            </Box>
          )}

          {step === "plan" && (
            <MealPlannerPlan
              key="plan"
              plan={plan}
              config={config}
              lockedSlugs={lockedSlugs}
              onToggleLock={handleToggleLock}
              onSwap={handleSwap}
              onRegenerate={handleRegenerate}
              onNewPlan={handleNewPlan}
              onOpenShoppingList={() => setShoppingListOpen(true)}
            />
          )}
        </AnimatePresence>
      </Container>

      {/* Shopping List Drawer */}
      <ShoppingListDrawer
        open={shoppingListOpen}
        onClose={() => setShoppingListOpen(false)}
        planItems={fullRecipes.length > 0 ? fullRecipes : plan}
        servingsPerMeal={config.servingsPerMeal}
      />
    </Box>
  );
};

export default MealPlannerPage;
