import React, { createContext, useContext, useCallback, useMemo } from "react";
import useLocalStorage from "../hooks/useLocalStorage";

const PantryContext = createContext();

export const usePantry = () => {
  const context = useContext(PantryContext);
  if (!context) {
    throw new Error("usePantry must be used within a PantryProvider");
  }
  return context;
};

const normalizeText = (text) => {
  if (!text) return "";
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
};

/**
 * All known pantry-type keywords (English).
 * Used to determine if a recipe ingredient is "pantry-like" (non-fresh).
 * This is a broad superset -- if an ingredient's name_en contains any of these,
 * it counts as a pantry-type ingredient for ratio calculation.
 */
const PANTRY_TYPE_KEYWORDS = [
  "salt", "pepper", "cumin", "paprika", "curry", "cinnamon", "nutmeg",
  "turmeric", "espelette", "cayenne", "ginger", "ras el hanout", "allspice",
  "sumac", "coriander", "cardamom", "za'atar", "chili", "saffron",
  "fenugreek", "caraway", "star anise", "five spice", "garam masala",
  "tandoori", "chipotle",
  "thyme", "rosemary", "basil", "oregano", "herbes de provence", "bay leaf",
  "parsley", "dill", "sage", "tarragon", "chives", "mint",
  "olive oil", "sunflower oil", "sesame oil", "butter", "ghee",
  "coconut oil", "rapeseed oil", "peanut oil", "walnut oil", "grapeseed oil", "lard", "oil",
  "mustard", "soy sauce", "vinegar", "honey", "tabasco", "worcestershire",
  "tomato paste", "fish sauce", "tahini", "harissa", "sriracha", "miso",
  "oyster sauce", "curry paste", "sambal", "maple syrup", "teriyaki",
  "flour", "sugar", "cornstarch", "breadcrumbs", "yeast", "baking soda",
  "baking powder", "lentils", "chickpeas", "oats", "seeds", "peanuts",
  "cashews", "almonds", "pine nuts", "raisins", "coconut", "cocoa",
  "chocolate",
  "spaghetti", "penne", "fusilli", "tagliatelle", "linguine", "farfalle",
  "rigatoni", "lasagna", "noodles", "udon", "soba", "vermicelli",
  "rice", "semolina", "bulgur", "quinoa", "polenta", "couscous", "pasta",
  "coconut milk", "tomatoes", "stock", "bouillon", "coconut cream",
  "canned", "sardines", "anchovies", "capers", "olives", "pickles", "tuna",
];

const pantryTypeSet = new Set(PANTRY_TYPE_KEYWORDS.map(normalizeText));

/**
 * Check if an ingredient (by its English name) is a pantry-type ingredient.
 */
const isPantryTypeIngredient = (nameEn) => {
  if (!nameEn) return false;
  const normalized = normalizeText(nameEn);
  if (!normalized) return false;
  for (const keyword of pantryTypeSet) {
    if (normalized.includes(keyword) || keyword.includes(normalized)) {
      return true;
    }
  }
  return false;
};

export const PantryProvider = ({ children }) => {
  const [pantryItems, setPantryItems] = useLocalStorage(
    "cookbook_pantry_items",
    []
  );

  const pantrySet = useMemo(() => {
    return new Set(pantryItems.map(normalizeText));
  }, [pantryItems]);

  const addItem = useCallback(
    (name) => {
      const normalized = normalizeText(name);
      if (!normalized) return;
      setPantryItems((prev) => {
        if (prev.some((item) => normalizeText(item) === normalized)) {
          return prev;
        }
        return [...prev, name.trim()];
      });
    },
    [setPantryItems]
  );

  const removeItem = useCallback(
    (name) => {
      const normalized = normalizeText(name);
      setPantryItems((prev) =>
        prev.filter((item) => normalizeText(item) !== normalized)
      );
    },
    [setPantryItems]
  );

  const toggleItem = useCallback(
    (name) => {
      const normalized = normalizeText(name);
      if (pantrySet.has(normalized)) {
        removeItem(name);
      } else {
        addItem(name);
      }
    },
    [pantrySet, addItem, removeItem]
  );

  const hasItem = useCallback(
    (nameEn) => {
      const normalized = normalizeText(nameEn);
      if (!normalized) return false;
      for (const pantryItem of pantrySet) {
        if (normalized.includes(pantryItem) || pantryItem.includes(normalized)) {
          return true;
        }
      }
      return false;
    },
    [pantrySet]
  );

  const hasExactItem = useCallback(
    (name) => {
      return pantrySet.has(normalizeText(name));
    },
    [pantrySet]
  );

  /**
   * Get the English name of an ingredient.
   */
  const getIngredientNameEn = (ingredient) => {
    if (typeof ingredient === "object" && ingredient?.name_en) {
      return normalizeText(ingredient.name_en);
    }
    return "";
  };

  /**
   * Check if a single ingredient matches the user's pantry (English only).
   */
  const ingredientMatchesPantry = useCallback(
    (nameEn) => {
      if (!nameEn) return false;
      for (const pantryItem of pantrySet) {
        if (nameEn.includes(pantryItem) || pantryItem.includes(nameEn)) {
          return true;
        }
      }
      return false;
    },
    [pantrySet]
  );

  /**
   * Count how many pantry-type ingredients in a recipe match the user's pantry.
   */
  const getPantryMatchCount = useCallback(
    (recipe) => {
      if (!recipe?.ingredients || pantrySet.size === 0) return 0;
      const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];
      let matchCount = 0;
      for (const ingredient of ingredients) {
        const nameEn = getIngredientNameEn(ingredient);
        if (!nameEn) continue;
        if (ingredientMatchesPantry(nameEn)) matchCount++;
      }
      return matchCount;
    },
    [pantrySet, ingredientMatchesPantry]
  );

  /**
   * Get detailed pantry stats for a recipe: matched count, pantry-type total, and ratio.
   */
  const getPantryStats = useCallback(
    (recipe) => {
      if (!recipe?.ingredients || pantrySet.size === 0) {
        return { matched: 0, pantryTypeTotal: 0, ratio: 0 };
      }
      const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];

      let pantryTypeCount = 0;
      let matchCount = 0;
      for (const ingredient of ingredients) {
        const nameEn = getIngredientNameEn(ingredient);
        if (!nameEn) continue;
        if (isPantryTypeIngredient(nameEn)) {
          pantryTypeCount++;
          if (ingredientMatchesPantry(nameEn)) matchCount++;
        }
      }
      return {
        matched: matchCount,
        pantryTypeTotal: pantryTypeCount,
        ratio: pantryTypeCount === 0 ? 0 : matchCount / pantryTypeCount,
      };
    },
    [pantrySet, ingredientMatchesPantry]
  );

  /**
   * Ratio of matched pantry items over pantry-type ingredients only (excludes fresh).
   */
  const getPantryMatchRatio = useCallback(
    (recipe) => getPantryStats(recipe).ratio,
    [getPantryStats]
  );

  const value = useMemo(
    () => ({
      pantryItems,
      pantrySet,
      addItem,
      removeItem,
      toggleItem,
      hasItem,
      hasExactItem,
      getPantryMatchCount,
      getPantryMatchRatio,
      getPantryStats,
      pantrySize: pantryItems.length,
    }),
    [
      pantryItems,
      pantrySet,
      addItem,
      removeItem,
      toggleItem,
      hasItem,
      hasExactItem,
      getPantryMatchCount,
      getPantryMatchRatio,
      getPantryStats,
    ]
  );

  return (
    <PantryContext.Provider value={value}>{children}</PantryContext.Provider>
  );
};

export default PantryProvider;
