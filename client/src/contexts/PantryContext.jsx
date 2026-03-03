import React, { createContext, useContext, useCallback, useMemo, useRef } from "react";
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
 * Word-boundary aware substring match.
 * Returns true when `word` appears in `text` surrounded by non-word chars
 * (or string edges). Avoids false positives like "rice" in "licorice".
 */
const containsWholeWord = (text, word) => {
  if (!text || !word) return false;
  if (text === word) return true;
  let idx = text.indexOf(word);
  while (idx !== -1) {
    const before = idx === 0 || /\W/.test(text[idx - 1]);
    const after =
      idx + word.length === text.length || /\W/.test(text[idx + word.length]);
    if (before && after) return true;
    idx = text.indexOf(word, idx + 1);
  }
  return false;
};

/**
 * Check if an ingredient (by its English name) is a pantry-type ingredient.
 */
const isPantryTypeIngredient = (nameEn) => {
  if (!nameEn) return false;
  const normalized = normalizeText(nameEn);
  if (!normalized) return false;
  for (const keyword of pantryTypeSet) {
    if (containsWholeWord(normalized, keyword) || containsWholeWord(keyword, normalized)) {
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
        if (containsWholeWord(normalized, pantryItem) || containsWholeWord(pantryItem, normalized)) {
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
        if (containsWholeWord(nameEn, pantryItem) || containsWholeWord(pantryItem, nameEn)) {
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
   * Uses a WeakMap cache keyed by recipe object reference, invalidated when pantrySet changes.
   */
  const statsCacheRef = useRef({ pantrySet: null, cache: new WeakMap() });

  const getPantryStats = useCallback(
    (recipe) => {
      const EMPTY = { matched: 0, pantryTypeTotal: 0, ratio: 0 };
      if (!recipe?.ingredients || pantrySet.size === 0) return EMPTY;

      if (statsCacheRef.current.pantrySet !== pantrySet) {
        statsCacheRef.current = { pantrySet, cache: new WeakMap() };
      }
      const cache = statsCacheRef.current.cache;
      const cached = cache.get(recipe);
      if (cached) return cached;

      const ingredients = Array.isArray(recipe.ingredients)
        ? recipe.ingredients
        : [];

      let pantryTypeCount = 0;
      let matchCount = 0;
      for (const ingredient of ingredients) {
        const nameEn = getIngredientNameEn(ingredient);
        if (!nameEn) continue;
        const isKnownPantryType = isPantryTypeIngredient(nameEn);
        const matchesPantry = ingredientMatchesPantry(nameEn);
        if (isKnownPantryType || matchesPantry) {
          pantryTypeCount++;
          if (matchesPantry) matchCount++;
        }
      }
      const result = {
        matched: matchCount,
        pantryTypeTotal: pantryTypeCount,
        ratio: pantryTypeCount === 0 ? 0 : matchCount / pantryTypeCount,
      };
      cache.set(recipe, result);
      return result;
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
