export const NUTRITION_TAG_KEYS = {
  "high-protein": "nutrition.highProtein",
  "low-calorie": "nutrition.light",
  "high-fiber": "nutrition.highFiber",
  "indulgent": "nutrition.indulgent",
  "balanced": "nutrition.balanced",
  "iron-rich": "nutrition.ironRich",
  "calcium-rich": "nutrition.calciumRich",
};

export const NUTRITION_TAG_CRITERIA_KEYS = {
  "high-protein": "nutrition.tagCriteria.high-protein",
  "low-calorie": "nutrition.tagCriteria.low-calorie",
  "high-fiber": "nutrition.tagCriteria.high-fiber",
  "indulgent": "nutrition.tagCriteria.indulgent",
  "balanced": "nutrition.tagCriteria.balanced",
  "iron-rich": "nutrition.tagCriteria.iron-rich",
  "calcium-rich": "nutrition.tagCriteria.calcium-rich",
};

export const CONFIDENCE_KEYS = {
  high: "nutrition.confidenceHigh",
  medium: "nutrition.confidenceMedium",
  low: "nutrition.confidenceLow",
  none: "nutrition.confidenceNone",
};

export const CONFIDENCE_COLORS = {
  high: "#66bb6a",
  medium: "#ffa726",
  low: "#ef5350",
  none: "#bdbdbd",
};

export const MACRO_COLORS = {
  protein: "#66bb6a",
  carbs: "#ffa726",
  fat: "#ef5350",
  fiber: "#8d6e63",
  sugar: "#ce93d8",
  saturatedFat: "#e57373",
};

export const MINERAL_COLORS = {
  calcium: "#4dd0e1",
  iron: "#a1887f",
  magnesium: "#81c784",
  potassium: "#ffb74d",
  sodium: "#90a4ae",
  zinc: "#7986cb",
};

export const MINERAL_UNITS = {
  calcium: "mg",
  iron: "mg",
  magnesium: "mg",
  potassium: "mg",
  sodium: "mg",
  zinc: "mg",
};

// FDA Daily Values (2020) for a 2000 kcal diet
export const DAILY_VALUES = {
  protein: 50,        // g
  carbs: 275,         // g
  fat: 78,            // g
  fiber: 28,          // g
  sugar: 50,          // g (added sugars DV)
  saturatedFat: 20,   // g
  sodium: 2300,       // mg
  calcium: 1300,      // mg
  iron: 18,           // mg
  magnesium: 420,     // mg
  potassium: 4700,    // mg
  zinc: 11,           // mg
};

export const pctDV = (value, key) => {
  const dv = DAILY_VALUES[key];
  if (!dv || value == null) return null;
  return Math.round((value / dv) * 100);
};

export const UNRESOLVED_KEYS = {
  no_match: "nutrition.unresolvedNoMatch",
  no_weight: "nutrition.unresolvedNoWeight",
  no_translation: "nutrition.unresolvedNoTranslation",
};

export const roundCalories = (cal) => Math.round(cal / 10) * 10;

export const formatMacro = (value, confidence) => {
  if (confidence === "low") return `~${Math.round(value)}`;
  if (confidence === "medium") return `~${Math.round(value * 10) / 10}`;
  return Math.round(value * 10) / 10;
};

export const formatQty = (qty, unit, grams) => {
  if (qty == null && grams == null) return "";
  const parts = [];
  if (qty != null) {
    const q = qty % 1 === 0 ? qty : Math.round(qty * 10) / 10;
    parts.push(unit ? `${q} ${unit}` : `${q}`);
  }
  if (grams != null && unit && unit !== "g" && unit !== "kg" && unit !== "ml" && unit !== "l") {
    parts.push(`(${Math.round(grams)}g)`);
  }
  return parts.join(" ");
};
