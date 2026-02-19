/**
 * Meal Planner utility functions
 * - Nutrition-aware recipe selection algorithm (greedy scoring with macro balance)
 * - Shopping list aggregation
 * - Ingredient normalization
 *
 * Algorithm approach: Enhanced greedy scoring inspired by constraint-satisfaction
 * research (MPG / Transportation Problem adaptation). We score each candidate
 * recipe against the current plan state using multiple weighted factors:
 *   1. Shared ingredients (shopping optimization)
 *   2. Recipe type variety
 *   3. Seasonal fit
 *   4. Macro balance deviation from target (nutrition)
 *   5. Calorie range moderation
 *   6. Nutrition tag preference matching
 */

// ─── Season detection (from shared utility) ────────────────────────
import { getCurrentSeason, SEASON_EMOJI } from "../../../../utils/seasonUtils";
export { getCurrentSeason, SEASON_EMOJI };

// ─── Nutrition tag definitions ───────────────────────────────────────
export const NUTRITION_GOALS = [
  { id: "balanced", label: "Balanced", emoji: "\u2696\uFE0F", description: "Even macro distribution" },
  { id: "high-protein", label: "High Protein", emoji: "\u{1F4AA}", description: "Protein > 25g/serving" },
  { id: "low-calorie", label: "Light", emoji: "\u{1F343}", description: "Under 400 kcal/serving" },
  { id: "high-fiber", label: "High Fiber", emoji: "\u{1F33E}", description: "Fiber > 8g/serving" },
];

// ─── Ideal macro targets (% of calories) ────────────────────────────
// Based on ANSES (France, 2016) nutritional references.
// Cross-validated against IOM/USDA AMDR, EFSA DRV, and WHO guidelines.
// See DATA_SOURCES.md and MacroBalanceBar.jsx for full source details.
export const MACRO_TARGETS = {
  protein: { min: 0.10, ideal: 0.15, max: 0.20 }, // ANSES: 10-20% of kcal
  carbs: { min: 0.40, ideal: 0.50, max: 0.55 },   // ANSES: 40-55% of kcal
  fat: { min: 0.35, ideal: 0.37, max: 0.40 },      // ANSES: 35-40% of kcal
};

// Ideal calorie range per meal (kcal)
const CALORIE_RANGE = { min: 300, ideal: 550, max: 800 };

// ─── Text normalization ──────────────────────────────────────────────
export const normalizeIngredientName = (name) => {
  if (!name) return "";
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
};

// ─── Ingredient category mapping ─────────────────────────────────────
const CATEGORY_MAP = {
  produce: { label: "Fruits & Vegetables", emoji: "\u{1F96C}", order: 1 },
  herb: { label: "Fresh Herbs", emoji: "\u{1F33F}", order: 1.5 },
  meat: { label: "Meat & Fish", emoji: "\u{1F969}", order: 2 },
  poultry: { label: "Meat & Fish", emoji: "\u{1F969}", order: 2 },
  seafood: { label: "Meat & Fish", emoji: "\u{1F969}", order: 2 },
  fish: { label: "Meat & Fish", emoji: "\u{1F969}", order: 2 },
  dairy: { label: "Dairy", emoji: "\u{1F9C0}", order: 3 },
  egg: { label: "Eggs", emoji: "\u{1F95A}", order: 3.5 },
  grain: { label: "Grains & Pasta", emoji: "\u{1F35E}", order: 4 },
  pasta: { label: "Grains & Pasta", emoji: "\u{1F35E}", order: 4 },
  legume: { label: "Legumes", emoji: "\u{1FAD8}", order: 4.3 },
  nuts_seeds: { label: "Nuts & Seeds", emoji: "\u{1F330}", order: 4.5 },
  pantry: { label: "Pantry", emoji: "\u{1FAD9}", order: 5 },
  oil: { label: "Oils & Fats", emoji: "\u{1FAD2}", order: 5.5 },
  fat: { label: "Oils & Fats", emoji: "\u{1FAD2}", order: 5.5 },
  spice: { label: "Spices", emoji: "\u{1F9C2}", order: 6 },
  condiment: { label: "Condiments", emoji: "\u{1F9C8}", order: 7 },
  sauce: { label: "Condiments", emoji: "\u{1F9C8}", order: 7 },
  beverage: { label: "Beverages", emoji: "\u{1F95B}", order: 8 },
  other: { label: "Other", emoji: "\u{1F4E6}", order: 9 },
};

const getCategoryInfo = (category) => {
  if (!category) return CATEGORY_MAP.other;
  const lower = category.toLowerCase();
  return CATEGORY_MAP[lower] || CATEGORY_MAP.other;
};

// ─── Ingredient helpers ──────────────────────────────────────────────

const getIngredientNames = (recipe) => {
  if (!recipe.ingredients) return new Set();
  if (Array.isArray(recipe.ingredients)) {
    return new Set(
      recipe.ingredients.map((ing) =>
        typeof ing === "string"
          ? normalizeIngredientName(ing)
          : normalizeIngredientName(ing.name_en || ing.name || "")
      )
    );
  }
  return new Set();
};

const countSharedIngredients = (candidateIngredients, selectedIngredientSets) => {
  let sharedCount = 0;
  for (const name of candidateIngredients) {
    for (const selectedSet of selectedIngredientSets) {
      if (selectedSet.has(name)) {
        sharedCount++;
        break;
      }
    }
  }
  return sharedCount;
};

export const countTotalSharedIngredients = (recipes) => {
  if (!recipes || recipes.length < 2) return 0;
  const allIngredientSets = recipes.map((r) => getIngredientNames(r));
  const ingredientAppearances = new Map();
  for (const ingredientSet of allIngredientSets) {
    for (const name of ingredientSet) {
      ingredientAppearances.set(name, (ingredientAppearances.get(name) || 0) + 1);
    }
  }
  let sharedCount = 0;
  for (const [, count] of ingredientAppearances) {
    if (count > 1) sharedCount++;
  }
  return sharedCount;
};

// ─── Nutrition helpers ───────────────────────────────────────────────

/**
 * Get nutrition data from a recipe (handles both list and full format).
 * Returns null if no nutrition data available.
 */
const getNutrition = (recipe) => {
  const n = recipe.nutritionPerServing;
  if (!n || n.confidence === "none") return null;
  return {
    calories: n.calories || 0,
    protein: n.protein || 0,
    fat: n.fat || 0,
    carbs: n.carbs || 0,
    fiber: n.fiber || 0,
    confidence: n.confidence || "low",
  };
};

/**
 * Check if a recipe has reliable nutrition data (high confidence only = 90%+ resolved).
 * Medium/low confidence data is displayed in the UI but excluded from meal planning
 * to avoid suggesting meals based on unreliable nutritional estimates.
 */
const hasNutritionData = (recipe) => {
  const n = getNutrition(recipe);
  return n !== null && n.confidence === "high";
};

/**
 * Compute macro percentages from absolute values.
 * Returns { proteinPct, carbsPct, fatPct } as fractions (0-1).
 */
const computeMacroPcts = (protein, carbs, fat) => {
  const totalCal = protein * 4 + carbs * 4 + fat * 9;
  if (totalCal === 0) return { proteinPct: 0.33, carbsPct: 0.33, fatPct: 0.33 };
  return {
    proteinPct: (protein * 4) / totalCal,
    carbsPct: (carbs * 4) / totalCal,
    fatPct: (fat * 9) / totalCal,
  };
};

/**
 * Score how well a macro distribution matches the ideal targets.
 * Returns 0 (perfect) to negative values (further from ideal).
 * Uses sum of squared deviations from ideal — penalizes large deviations more.
 */
const macroBalanceScore = (proteinPct, carbsPct, fatPct) => {
  const devProtein = Math.abs(proteinPct - MACRO_TARGETS.protein.ideal);
  const devCarbs = Math.abs(carbsPct - MACRO_TARGETS.carbs.ideal);
  const devFat = Math.abs(fatPct - MACRO_TARGETS.fat.ideal);

  // Sum of squared deviations (max ~0.15, typical ~0.03-0.08)
  const totalDev = devProtein ** 2 + devCarbs ** 2 + devFat ** 2;

  // Convert to a score: 0 deviation → +3, high deviation → 0 or negative
  return Math.max(0, 3 - totalDev * 100);
};

/**
 * Score how well a calorie value fits in the ideal range.
 * Returns 0 to +2.
 */
const calorieRangeScore = (calories) => {
  if (calories <= 0) return 0;
  if (calories >= CALORIE_RANGE.min && calories <= CALORIE_RANGE.max) {
    // Within range: bonus based on closeness to ideal
    const dev = Math.abs(calories - CALORIE_RANGE.ideal) / CALORIE_RANGE.ideal;
    return Math.max(0, 2 - dev * 2);
  }
  // Outside range: penalty
  if (calories < CALORIE_RANGE.min) {
    return Math.max(-2, -((CALORIE_RANGE.min - calories) / CALORIE_RANGE.min) * 2);
  }
  return Math.max(-2, -((calories - CALORIE_RANGE.max) / CALORIE_RANGE.max) * 2);
};

/**
 * Compute the running average nutrition of a set of recipes.
 */
const computeAverageNutrition = (recipes) => {
  let totalCalories = 0;
  let totalProtein = 0;
  let totalCarbs = 0;
  let totalFat = 0;
  let totalFiber = 0;
  let count = 0;

  for (const recipe of recipes) {
    const n = getNutrition(recipe);
    if (!n) continue;
    totalCalories += n.calories;
    totalProtein += n.protein;
    totalCarbs += n.carbs;
    totalFat += n.fat;
    totalFiber += n.fiber;
    count++;
  }

  if (count === 0) return null;
  return {
    calories: totalCalories / count,
    protein: totalProtein / count,
    carbs: totalCarbs / count,
    fat: totalFat / count,
    fiber: totalFiber / count,
    count,
  };
};

// ─── Plan nutrition stats (exported for UI) ──────────────────────────

/**
 * Compute aggregate nutrition stats for the whole plan.
 * Returns { avgCalories, avgProtein, avgCarbs, avgFat, avgFiber, macroPcts, recipesWith Data, total }
 */
export const computePlanNutrition = (planRecipes) => {
  const avg = computeAverageNutrition(planRecipes);
  if (!avg) {
    return {
      avgCalories: 0,
      avgProtein: 0,
      avgCarbs: 0,
      avgFat: 0,
      avgFiber: 0,
      proteinPct: 0,
      carbsPct: 0,
      fatPct: 0,
      recipesWithData: 0,
      total: planRecipes.length,
    };
  }
  const pcts = computeMacroPcts(avg.protein, avg.carbs, avg.fat);
  return {
    avgCalories: Math.round(avg.calories),
    avgProtein: Math.round(avg.protein * 10) / 10,
    avgCarbs: Math.round(avg.carbs * 10) / 10,
    avgFat: Math.round(avg.fat * 10) / 10,
    avgFiber: Math.round(avg.fiber * 10) / 10,
    proteinPct: Math.round(pcts.proteinPct * 100),
    carbsPct: Math.round(pcts.carbsPct * 100),
    fatPct: Math.round(pcts.fatPct * 100),
    recipesWithData: avg.count,
    total: planRecipes.length,
  };
};

// ─── Recipe selection algorithm ──────────────────────────────────────

/**
 * Filter recipes based on meal planner configuration.
 * Now includes nutrition tag filtering.
 */
// Recipe types that don't belong in a meal plan (not actual meals)
const EXCLUDED_RECIPE_TYPES = ["base", "dessert", "drink", "appetizer"];

const filterCandidates = (allRecipes, config) => {
  // Pre-normalize excluded ingredients for matching (substring match)
  const excludedIngredients = (config.excludedIngredients || []).map((name) =>
    normalizeIngredientName(name)
  ).filter(Boolean);

  return allRecipes.filter((recipe) => {
    // Exclude non-meal recipe types (bases, desserts, drinks)
    if (EXCLUDED_RECIPE_TYPES.includes(recipe.recipeType)) return false;

    // Only keep recipes with high nutrition confidence
    const confidence = recipe.nutritionPerServing?.confidence;
    if (confidence !== "high") return false;

    // Exclude recipes containing disliked ingredients (substring match)
    if (excludedIngredients.length > 0) {
      const recipeIngredients = getIngredientNames(recipe);
      for (const excluded of excludedIngredients) {
        for (const ing of recipeIngredients) {
          if (ing.includes(excluded)) return false;
        }
      }
    }

    // Diet filter
    if (config.dietPreference) {
      if (!recipe.diets?.includes(config.dietPreference)) return false;
    }

    // Nutrition tag filter (soft filter: at least match one if multiple goals)
    // We use this as a hard filter only if the user selected goals AND enough recipes match
    if (config.nutritionGoals && config.nutritionGoals.length > 0) {
      const tags = recipe.nutritionTags || [];
      const matchesAny = config.nutritionGoals.some((goal) => tags.includes(goal));
      // If recipe has no nutrition data at all, don't filter it out
      // (we'll penalize in scoring instead)
      if (tags.length > 0 && !matchesAny) return false;
    }

    return true;
  });
};

/**
 * Get English ingredient names from a recipe.
 */
const getIngredientNamesEn = (recipe) => {
  if (!recipe.ingredients || !Array.isArray(recipe.ingredients)) return [];
  return recipe.ingredients
    .map((ing) =>
      typeof ing === "object" ? normalizeIngredientName(ing.name_en || "") : ""
    )
    .filter(Boolean);
};

/**
 * Count how many of a recipe's ingredients are in the user's pantry.
 * Matches on English names only.
 */
const countPantryMatches = (ingredientNamesEn, pantrySet) => {
  if (!pantrySet || pantrySet.size === 0) return 0;
  let count = 0;
  for (const nameEn of ingredientNamesEn) {
    for (const pantryItem of pantrySet) {
      if (nameEn.includes(pantryItem) || pantryItem.includes(nameEn)) {
        count++;
        break;
      }
    }
  }
  return count;
};

/**
 * Score a candidate recipe relative to already-selected recipes.
 * Enhanced with nutrition-aware scoring.
 */
const scoreRecipe = (candidate, selectedRecipes, config, candidateIngredients, selectedIngredientSets, pantrySet) => {
  let score = 0;
  const reasons = [];
  const currentSeason = getCurrentSeason();

  // ── 1. NUTRITION SCORING (primary signal, up to +20) ──
  // Nutrition is the top priority for meal planning — we want balanced,
  // well-portioned meals before optimizing for shopping convenience.
  const candidateNutrition = getNutrition(candidate);

  if (candidateNutrition) {
    // 1a. Macro balance of the plan WITH this candidate (0 to +8)
    if (selectedRecipes.length > 0) {
      const allWithCandidate = [...selectedRecipes, candidate];
      const avg = computeAverageNutrition(allWithCandidate);
      if (avg) {
        const pcts = computeMacroPcts(avg.protein, avg.carbs, avg.fat);
        const balanceBonus = macroBalanceScore(pcts.proteinPct, pcts.carbsPct, pcts.fatPct);
        score += balanceBonus * 2.5;
        if (balanceBonus > 2) {
          reasons.push("balanced");
        }
      }
    } else {
      // First recipe: score its own balance
      const pcts = computeMacroPcts(
        candidateNutrition.protein,
        candidateNutrition.carbs,
        candidateNutrition.fat
      );
      score += macroBalanceScore(pcts.proteinPct, pcts.carbsPct, pcts.fatPct) * 2.5;
    }

    // 1b. Calorie range moderation (0 to +5)
    score += calorieRangeScore(candidateNutrition.calories) * 2.5;

    // 1c. Nutrition tag goal matching (+4 per matching goal)
    if (config.nutritionGoals && config.nutritionGoals.length > 0) {
      const tags = candidate.nutritionTags || [];
      const matchCount = config.nutritionGoals.filter((g) => tags.includes(g)).length;
      if (matchCount > 0) {
        score += matchCount * 4;
        for (const goal of config.nutritionGoals) {
          if (tags.includes(goal)) {
            reasons.push(goal);
          }
        }
      }
    }

    // 1d. Anti-indulgence clustering: if most selected are "indulgent",
    //     strongly prefer non-indulgent recipes
    const indulgentCount = selectedRecipes.filter(
      (r) => r.nutritionTags?.includes("indulgent")
    ).length;
    if (selectedRecipes.length > 0 && indulgentCount / selectedRecipes.length > 0.5) {
      if (!candidate.nutritionTags?.includes("indulgent")) {
        score += 3;
      } else {
        score -= 2;
      }
    }
  }

  // ── 2. Seasonal bonus (+10) ──
  if (config.prioritizeSeasonal && candidate.seasons?.includes(currentSeason)) {
    score += 10;
    reasons.push("seasonal");
  }

  // ── 2b. Pantry bonus (+0.5 per pantry ingredient, capped at +5) ──
  if (pantrySet && pantrySet.size > 0) {
    const namesEn = getIngredientNamesEn(candidate);
    const pantryCount = countPantryMatches(namesEn, pantrySet);
    if (pantryCount > 0) {
      score += Math.min(pantryCount * 0.5, 5);
      reasons.push(`${pantryCount}_pantry`);
    }
  }

  // ── 3. Variety bonus: prefer different recipe types (+2) ──
  const selectedTypes = selectedRecipes.map((r) => r.recipeType);
  if (!selectedTypes.includes(candidate.recipeType)) {
    score += 2;
    reasons.push("variety");
  }

  // ── 4. Shared ingredients bonus (+0.5 per shared, capped at +3) ──
  // Shopping optimization is nice-to-have, not a driver
  if (selectedRecipes.length > 0) {
    const shared = countSharedIngredients(candidateIngredients, selectedIngredientSets);
    if (shared > 0) {
      score += Math.min(shared * 0.5, 3);
      reasons.push(`${shared}_shared`);
    }
  }

  // ── 5. Author diversity: slight penalty for same author (-1) ──
  const selectedAuthors = selectedRecipes.map((r) => r.author).filter(Boolean);
  if (candidate.author && selectedAuthors.includes(candidate.author)) {
    score -= 1;
  }

  // ── 6. Random factor for variety across regenerations ──
  // Range 0-4 reshuffles similarly-scored candidates without
  // overriding the nutrition signal (which scores up to +20).
  score += Math.random() * 4;

  return { score, reasons };
};

/**
 * Build final reasons array for a recipe in the context of the full plan.
 */
const buildFinalReasons = (item, idx, selected, allIngredientSets, config) => {
  const myIngredients = allIngredientSets[idx];
  const otherSets = allIngredientSets.filter((_, j) => j !== idx);
  const shared = countSharedIngredients(myIngredients, otherSets);
  const currentSeason = getCurrentSeason();

  const reasons = [];
  if (item.reasons.includes("locked")) reasons.push("locked");
  if (item.recipe.seasons?.includes(currentSeason)) reasons.push("seasonal");
  if (shared > 0) reasons.push(`${shared}_shared`);

  // Variety
  const otherTypes = selected.filter((_, j) => j !== idx).map((s) => s.recipe.recipeType);
  if (!otherTypes.includes(item.recipe.recipeType)) reasons.push("variety");

  // Nutrition tags matched from goals
  if (config.nutritionGoals && config.nutritionGoals.length > 0) {
    const tags = item.recipe.nutritionTags || [];
    for (const goal of config.nutritionGoals) {
      if (tags.includes(goal)) reasons.push(goal);
    }
  }

  // Balanced macro (check individual recipe)
  const n = getNutrition(item.recipe);
  if (n) {
    const pcts = computeMacroPcts(n.protein, n.carbs, n.fat);
    const balance = macroBalanceScore(pcts.proteinPct, pcts.carbsPct, pcts.fatPct);
    if (balance > 2 && !reasons.includes("balanced")) reasons.push("balanced");
  }

  return { reasons, sharedCount: shared };
};

/**
 * Greedy recipe selection algorithm — nutrition-aware.
 * Returns an array of { recipe, reasons, sharedCount } objects.
 */
export const generateMealPlan = (allRecipes, config, lockedRecipes = [], pantryItems = []) => {
  // If nutrition goals are set but too few recipes match, fall back to unfiltered
  let candidates = filterCandidates(allRecipes, config);
  if (candidates.length < config.numberOfMeals) {
    // Soft fallback: remove nutrition filter, keep diet filter only
    candidates = allRecipes.filter((recipe) => {
      if (config.dietPreference) {
        if (!recipe.diets?.includes(config.dietPreference)) return false;
      }
      return true;
    });
  }

  const pantrySet = new Set(pantryItems.map(normalizeIngredientName));
  const lockedSlugs = new Set(lockedRecipes.map((r) => r.slug));
  const numberOfMeals = config.numberOfMeals;

  const selected = [...lockedRecipes.map((r) => ({
    recipe: r,
    reasons: ["locked"],
  }))];

  const selectedIngredientSets = selected.map((s) => getIngredientNames(s.recipe));

  const hasMainCourse = selected.some((s) => s.recipe.recipeType === "main_course");
  const slotsRemaining = numberOfMeals - selected.length;

  // Top-K weighted random selection: pick from the best candidates
  // instead of always taking the single best one. K=12 gives a wide
  // enough pool for variety while all candidates are still high-quality.
  const TOP_K = 12;
  const SOFTMAX_TEMPERATURE = 3;

  for (let i = 0; i < slotsRemaining; i++) {
    const scoredCandidates = [];

    const preferMainCourse = i === 0 && !hasMainCourse;

    for (const candidate of candidates) {
      if (lockedSlugs.has(candidate.slug)) continue;
      if (selected.some((s) => s.recipe.slug === candidate.slug)) continue;

      const candidateIngredients = getIngredientNames(candidate);
      const { score: rawScore, reasons } = scoreRecipe(
        candidate,
        selected.map((s) => s.recipe),
        config,
        candidateIngredients,
        selectedIngredientSets,
        pantrySet
      );

      let score = rawScore;

      if (preferMainCourse && candidate.recipeType === "main_course") {
        score += 5;
      }

      scoredCandidates.push({ candidate, score, reasons });
    }

    if (scoredCandidates.length === 0) break;

    // Sort by score descending, take the top K
    scoredCandidates.sort((a, b) => b.score - a.score);
    const topK = scoredCandidates.slice(0, Math.min(TOP_K, scoredCandidates.length));

    // Weighted random pick from top K (softmax with temperature to flatten distribution).
    // Temperature > 1 makes the selection more uniform among top candidates,
    // giving variety while still favoring higher-scored (well-balanced) recipes.
    const minScore = topK[topK.length - 1].score;
    const weights = topK.map((c) => Math.exp((c.score - minScore) / SOFTMAX_TEMPERATURE));
    const totalWeight = weights.reduce((sum, w) => sum + w, 0);
    let rand = Math.random() * totalWeight;
    let pick = topK[0];
    for (let j = 0; j < topK.length; j++) {
      rand -= weights[j];
      if (rand <= 0) {
        pick = topK[j];
        break;
      }
    }

    selected.push({ recipe: pick.candidate, reasons: pick.reasons });
    selectedIngredientSets.push(getIngredientNames(pick.candidate));
  }

  // Recalculate final reasons with full plan context
  const allIngredientSets = selected.map((s) => getIngredientNames(s.recipe));
  return selected.map((item, idx) => {
    const { reasons, sharedCount } = buildFinalReasons(
      item, idx, selected, allIngredientSets, config
    );
    return { recipe: item.recipe, reasons, sharedCount };
  });
};

/**
 * Swap a single recipe in the plan.
 */
export const swapRecipe = (allRecipes, config, currentPlan, swapIndex, pantryItems = []) => {
  let candidates = filterCandidates(allRecipes, config);
  if (candidates.length < 2) {
    candidates = allRecipes.filter((recipe) => {
      if (config.dietPreference) {
        if (!recipe.diets?.includes(config.dietPreference)) return false;
      }
      return true;
    });
  }

  const pantrySet = new Set(pantryItems.map(normalizeIngredientName));
  const currentSlugs = new Set(currentPlan.map((item) => item.recipe.slug));
  const keptItems = currentPlan.filter((_, i) => i !== swapIndex);
  const keptIngredientSets = keptItems.map((item) => getIngredientNames(item.recipe));

  let bestCandidate = null;
  let bestScore = -Infinity;
  let bestReasons = [];

  for (const candidate of candidates) {
    if (currentSlugs.has(candidate.slug)) continue;

    const candidateIngredients = getIngredientNames(candidate);
    const { score, reasons } = scoreRecipe(
      candidate,
      keptItems.map((item) => item.recipe),
      config,
      candidateIngredients,
      keptIngredientSets,
      pantrySet
    );

    if (score > bestScore) {
      bestScore = score;
      bestCandidate = candidate;
      bestReasons = reasons;
    }
  }

  if (!bestCandidate) return currentPlan;

  const newPlan = [...currentPlan];
  newPlan[swapIndex] = { recipe: bestCandidate, reasons: bestReasons, sharedCount: 0 };

  const allIngredientSets = newPlan.map((item) => getIngredientNames(item.recipe));
  return newPlan.map((item, idx) => {
    const { reasons, sharedCount } = buildFinalReasons(
      item, idx, newPlan, allIngredientSets, config
    );
    return { recipe: item.recipe, reasons, sharedCount };
  });
};

// ─── Shopping list aggregation ───────────────────────────────────────

export const buildShoppingList = (planItems, servingsPerMeal) => {
  const ingredientMap = new Map();

  for (const { recipe } of planItems) {
    if (!recipe.ingredients || !Array.isArray(recipe.ingredients)) continue;

    const recipeServings = recipe.metadata?.servings || recipe.servings || 4;
    const multiplier = servingsPerMeal / recipeServings;

    for (const ing of recipe.ingredients) {
      if (typeof ing === "string") continue;

      // Use English name as key for deduplication across FR/EN recipes
      const key = normalizeIngredientName(ing.name_en || ing.name);
      if (!key) continue;

      const scaledQuantity = ing.quantity ? ing.quantity * multiplier : null;
      const categoryInfo = getCategoryInfo(ing.category);

      if (ingredientMap.has(key)) {
        const existing = ingredientMap.get(key);
        if (
          existing.unit === ing.unit &&
          existing.quantity != null &&
          scaledQuantity != null
        ) {
          existing.quantity += scaledQuantity;
        } else if (scaledQuantity != null && existing.quantity == null) {
          existing.quantity = scaledQuantity;
          existing.unit = ing.unit;
        }
        existing.recipeCount = (existing.recipeCount || 1) + 1;
      } else {
        ingredientMap.set(key, {
          name: ing.name_en || ing.name,
          name_en: ing.name_en || "",
          quantity: scaledQuantity,
          unit: ing.unit,
          category: categoryInfo.label,
          categoryEmoji: categoryInfo.emoji,
          categoryOrder: categoryInfo.order,
          recipeCount: 1,
        });
      }
    }
  }

  const categoryGroups = new Map();
  for (const item of ingredientMap.values()) {
    const cat = item.category;
    if (!categoryGroups.has(cat)) {
      categoryGroups.set(cat, {
        category: cat,
        emoji: item.categoryEmoji,
        order: item.categoryOrder,
        items: [],
      });
    }
    categoryGroups.get(cat).items.push({
      name: item.name,
      name_en: item.name_en,
      quantity: item.quantity,
      unit: item.unit,
      recipeCount: item.recipeCount,
    });
  }

  const result = Array.from(categoryGroups.values()).sort((a, b) => a.order - b.order);
  for (const group of result) {
    group.items.sort((a, b) => a.name.localeCompare(b.name));
  }

  return result;
};

export const formatQuantity = (quantity, unit) => {
  if (quantity == null) return "";
  const rounded = Math.round(quantity * 10) / 10;
  const formatted = rounded % 1 === 0 ? rounded.toString() : rounded.toFixed(1);
  if (!unit) return formatted;
  return `${formatted} ${unit}`;
};

export const shoppingListToText = (groups) => {
  const lines = [];
  for (const group of groups) {
    lines.push(`\n${group.emoji} ${group.category.toUpperCase()}`);
    for (const item of group.items) {
      const qty = formatQuantity(item.quantity, item.unit);
      lines.push(qty ? `- ${item.name}: ${qty}` : `- ${item.name}`);
    }
  }
  return lines.join("\n").trim();
};
