import { parseTimeToMinutes } from "../../../utils/timeUtils";

/* ═══════════════════════════════════════════════════════════════════
   Data helpers for CookingMode
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Flatten all sub-recipe steps into a single ordered array,
 * resolving ingredient refs and produced-state inputs.
 */
export const flattenSteps = (recipe) => {
  if (!recipe?.subRecipes) return [];

  const subRecipes = Array.isArray(recipe.subRecipes)
    ? recipe.subRecipes
    : Object.values(recipe.subRecipes || {});

  const producesMap = {};
  subRecipes.forEach((sr) => {
    (sr.steps || []).forEach((step) => {
      if (step.produces) {
        producesMap[step.produces] = {
          stepId: step.id,
          subRecipeTitle: sr.title || sr.id || "Main",
          name: step.produces.replace(/_/g, " "),
        };
      }
    });
  });

  const allIngredientRefs = new Set();
  subRecipes.forEach((sr) => {
    (sr.ingredients || []).forEach((ing) => allIngredientRefs.add(ing.ref));
  });

  const steps = [];
  subRecipes.forEach((sr) => {
    (sr.steps || []).forEach((step) => {
      const ingredients = (sr.ingredients || []).filter((ing) =>
        (step.uses || []).includes(ing.ref)
      );

      const stateInputs = (step.uses || [])
        .filter((ref) => producesMap[ref] && !allIngredientRefs.has(ref))
        .map((ref) => ({
          ref,
          name: producesMap[ref].name,
          isProducedState: true,
          fromSubRecipe: producesMap[ref].subRecipeTitle,
        }));

      steps.push({
        ...step,
        subRecipeTitle: sr.title || sr.id || "Main",
        ingredients: [...ingredients, ...stateInputs],
      });
    });
  });

  return steps;
};

/** Estimate total remaining time from a given step index. */
export const estimateRemainingTime = (steps, fromIdx) => {
  let total = 0;
  for (let i = fromIdx; i < steps.length; i++) {
    const raw = steps[i].time || steps[i].duration || null;
    if (raw) total += parseTimeToMinutes(raw);
  }
  return total;
};

export const formatRemainingTime = (minutes) => {
  if (minutes <= 0) return null;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (h > 0 && m > 0) return `~${h}h${String(m).padStart(2, "0")}`;
  if (h > 0) return `~${h}h`;
  return `~${m} min`;
};

export const formatTemperature = (temp) => {
  if (temp == null) return null;
  const str = String(temp);
  if (/^\d+$/.test(str)) return `${str}\u00B0C`;
  return str;
};

export const formatTimerDisplay = (seconds) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0)
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

/** Group steps by subRecipeTitle, keeping global indices. */
export const groupStepsBySubRecipe = (steps) => {
  const groups = [];
  let currentGroup = null;

  steps.forEach((step, globalIdx) => {
    if (!currentGroup || currentGroup.title !== step.subRecipeTitle) {
      currentGroup = { title: step.subRecipeTitle, startIdx: globalIdx, steps: [] };
      groups.push(currentGroup);
    }
    currentGroup.steps.push({ ...step, globalIdx });
  });

  return groups;
};

/** Check if action text explicitly mentions a time duration (FR + EN). */
export const hasExplicitTimeMention = (actionText, isPassive) => {
  const TU =
    "(?:min(?:ute)?s?|h(?:eure)?s?|sec(?:onde)?s?|hours?)";
  const WN =
    "(?:une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|vingt|trente|quarante|cinquante|soixante|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty)";

  return (
    new RegExp(`\\d+\\s*${TU}\\b`, "i").test(actionText) ||
    /\b(pendant|durant|for)\s+\d+/i.test(actionText) ||
    new RegExp(`\\b${WN}\\s+${TU}\\b`, "i").test(actionText) ||
    new RegExp(`\\b(?:pendant|durant|for)\\s+${WN}\\s+${TU}\\b`, "i").test(actionText) ||
    isPassive === true
  );
};

/**
 * Dynamic font size — optimized for kitchen readability.
 * Must be readable from ~1m away on a phone screen.
 */
export const getActionFontSize = (textLength) => {
  if (textLength < 50) return { xs: "1.55rem", md: "2.15rem" };
  if (textLength < 100) return { xs: "1.35rem", md: "1.75rem" };
  if (textLength < 180) return { xs: "1.15rem", md: "1.45rem" };
  return { xs: "1.05rem", md: "1.25rem" };
};

/** Check if recipe has multiple distinct sub-recipes. */
export const hasMultipleSubRecipes = (steps) => {
  const titles = new Set(steps.map((s) => s.subRecipeTitle));
  return titles.size > 1;
};
