import { roundGrams, roundToFraction, getFractionDisplay } from "./ingredientScaling";

// ---------------------------------------------------------------------------
// Conversion factor tables
// ---------------------------------------------------------------------------

const TO_ML = {
  cup: 240,
  tbsp: 15,
  tsp: 5,
  "fl oz": 29.57,
  pint: 473,
  quart: 946,
  gallon: 3785,
  cl: 10,
  dl: 100,
  ml: 1,
  l: 1000,
  cs: 15,
  cc: 5,
};

const TO_G = {
  oz: 28.35,
  lb: 453.6,
  g: 1,
  kg: 1000,
};

// ---------------------------------------------------------------------------
// Unit classification
// ---------------------------------------------------------------------------

const VOLUME_UNITS = new Set(Object.keys(TO_ML));
const WEIGHT_UNITS = new Set(Object.keys(TO_G));

const METRIC_UNITS = new Set(["g", "kg", "ml", "l", "cl", "dl"]);
const IMPERIAL_UNITS = new Set([
  "cup", "tbsp", "tsp", "fl oz", "pint", "quart", "gallon", "oz", "lb",
]);

// ---------------------------------------------------------------------------
// Unit modifier normalization
// Strips "heaping", "scant", etc. to extract the base convertible unit
// ---------------------------------------------------------------------------

const MODIFIER_PREFIXES = [
  "heaping", "scant", "generous", "level", "packed",
  "rounded", "healthy", "big", "large", "small",
];

function normalizeUnitModifier(unit) {
  if (!unit) return { baseUnit: null, modifier: null };
  const lower = unit.toLowerCase().trim();

  for (const prefix of MODIFIER_PREFIXES) {
    if (lower.startsWith(prefix + " ")) {
      const rest = lower.slice(prefix.length + 1).trim();
      const singular = rest
        .replace(/^cups$/, "cup")
        .replace(/^tablespoons?$/, "tbsp")
        .replace(/^teaspoons?$/, "tsp");
      if (VOLUME_UNITS.has(singular) || WEIGHT_UNITS.has(singular)) {
        return { baseUnit: singular, modifier: prefix };
      }
    }
  }

  const singularized = lower
    .replace(/^cups$/, "cup")
    .replace(/^tablespoons?$/, "tbsp")
    .replace(/^teaspoons?$/, "tsp");
  if (VOLUME_UNITS.has(singularized) || WEIGHT_UNITS.has(singularized)) {
    return { baseUnit: singularized, modifier: null };
  }

  return { baseUnit: lower, modifier: null };
}

// ---------------------------------------------------------------------------
// Kitchen-practical rounding
// ---------------------------------------------------------------------------

function roundMl(ml) {
  if (ml >= 1000) return { quantity: Math.round(ml / 100) / 10, unit: "l" };
  if (ml >= 500) return { quantity: Math.round(ml / 25) * 25, unit: "ml" };
  if (ml >= 100) return { quantity: Math.round(ml / 10) * 10, unit: "ml" };
  if (ml >= 15) return { quantity: Math.round(ml / 5) * 5, unit: "ml" };
  return { quantity: Math.round(ml), unit: "ml" };
}

function roundMetricWeight(grams) {
  if (grams >= 1000) return { quantity: Math.round(grams / 100) / 10, unit: "kg" };
  return { quantity: roundGrams(grams), unit: "g" };
}

function roundImperialWeight(grams) {
  if (grams >= 907) {
    const lb = grams / 453.6;
    return { quantity: Math.round(lb * 4) / 4, unit: "lb" };
  }
  const oz = grams / 28.35;
  return { quantity: Math.round(oz * 2) / 2, unit: "oz" };
}

function roundImperialVolume(ml) {
  const cups = ml / 240;
  if (cups >= 0.2) {
    const rounded = roundToFraction(cups);
    return { quantity: rounded, unit: "cup" };
  }
  const tbsp = ml / 15;
  if (tbsp >= 0.5) {
    const rounded = Math.round(tbsp * 2) / 2;
    return { quantity: rounded, unit: "tbsp" };
  }
  const tsp = ml / 5;
  if (tsp >= 0.25) {
    const rounded = roundToFraction(tsp);
    return { quantity: rounded, unit: "tsp" };
  }
  return { quantity: roundToFraction(tsp), unit: "tsp" };
}

// ---------------------------------------------------------------------------
// Display formatting helpers
// ---------------------------------------------------------------------------

export function formatConvertedQuantity(quantity, unit) {
  if (quantity == null || quantity === 0) return "-";

  if (unit === "cup" || unit === "tsp") {
    return `${getFractionDisplay(quantity)} ${unit}`;
  }
  if (unit === "tbsp") {
    return `${getFractionDisplay(quantity)} ${unit}`;
  }

  const formatted = quantity.toString();

  return `${formatted} ${unit}`;
}

// ---------------------------------------------------------------------------
// Main conversion function
// ---------------------------------------------------------------------------

/**
 * Convert an ingredient to the target unit system.
 * Only converts within the same measurement axis:
 *   - volume ↔ volume (cup → ml, ml → cup)
 *   - weight ↔ weight (oz → g, g → oz)
 * No cross-dimension conversion (cup → grams via estimatedWeightGrams).
 * estimatedWeightGrams is reserved for nutrition calculations only.
 *
 * @param {object} ingredient - ingredient object (only .unit is used)
 * @param {"original"|"metric"|"imperial"} targetSystem
 * @param {number} scaledQuantity - already-scaled quantity (after servings adjustment)
 * @param {string} [unitOverride] - unit to use instead of ingredient.unit
 * @returns {{ quantity: number|null, unit: string|null, converted: boolean }}
 */
export function convertIngredient(ingredient, targetSystem, scaledQuantity, unitOverride) {
  const rawUnit = unitOverride || ingredient.unit;

  if (targetSystem === "original") {
    return { quantity: scaledQuantity, unit: rawUnit, converted: false };
  }

  if (scaledQuantity == null || !rawUnit) {
    return { quantity: scaledQuantity, unit: rawUnit, converted: false };
  }

  const { baseUnit } = normalizeUnitModifier(rawUnit);
  if (!baseUnit) {
    return { quantity: scaledQuantity, unit: rawUnit, converted: false };
  }

  const isVol = VOLUME_UNITS.has(baseUnit);
  const isWt = WEIGHT_UNITS.has(baseUnit);

  if (!isVol && !isWt) {
    return { quantity: scaledQuantity, unit: rawUnit, converted: false };
  }

  const isMetricUnit = METRIC_UNITS.has(baseUnit);
  const isImperialUnit = IMPERIAL_UNITS.has(baseUnit);

  if (targetSystem === "metric" && isMetricUnit) {
    return { quantity: scaledQuantity, unit: rawUnit, converted: false };
  }
  if (targetSystem === "imperial" && isImperialUnit) {
    return { quantity: scaledQuantity, unit: rawUnit, converted: false };
  }

  // -------------------------------------------------------------------------
  // TO METRIC — same axis only
  // -------------------------------------------------------------------------
  if (targetSystem === "metric") {
    if (isWt) {
      const grams = scaledQuantity * TO_G[baseUnit];
      return { ...roundMetricWeight(grams), converted: true };
    }
    if (isVol) {
      const ml = scaledQuantity * TO_ML[baseUnit];
      return { ...roundMl(ml), converted: true };
    }
  }

  // -------------------------------------------------------------------------
  // TO IMPERIAL — same axis only
  // -------------------------------------------------------------------------
  if (targetSystem === "imperial") {
    if (isWt) {
      const grams = scaledQuantity * TO_G[baseUnit];
      return { ...roundImperialWeight(grams), converted: true };
    }
    if (isVol) {
      const ml = scaledQuantity * TO_ML[baseUnit];
      return { ...roundImperialVolume(ml), converted: true };
    }
  }

  return { quantity: scaledQuantity, unit: rawUnit, converted: false };
}

