import { describe, it, expect } from "vitest";
import {
  convertIngredient,
  formatConvertedQuantity,
} from "./unitConversion";

// ---------------------------------------------------------------------------
// convertIngredient — original mode
// ---------------------------------------------------------------------------

describe("convertIngredient — original mode", () => {
  it("returns the scaled quantity unchanged", () => {
    const ing = { quantity: 2, unit: "cup", category: "grain", name_en: "flour" };
    const result = convertIngredient(ing, "original", 4);
    expect(result).toEqual({ quantity: 4, unit: "cup", converted: false });
  });
});

// ---------------------------------------------------------------------------
// convertIngredient — to metric
// ---------------------------------------------------------------------------

describe("convertIngredient — to metric (same axis only)", () => {
  it("converts oz to grams", () => {
    const ing = { unit: "oz" };
    const result = convertIngredient(ing, "metric", 4);
    expect(result.unit).toBe("g");
    expect(result.quantity).toBe(110);
    expect(result.converted).toBe(true);
  });

  it("converts lb to grams", () => {
    const ing = { unit: "lb" };
    const result = convertIngredient(ing, "metric", 2);
    expect(result.unit).toBe("g");
    expect(result.quantity).toBe(910);
    expect(result.converted).toBe(true);
  });

  it("converts cup to ml (volume stays volume)", () => {
    const ing = { unit: "cup" };
    const result = convertIngredient(ing, "metric", 1);
    expect(result.unit).toBe("ml");
    expect(result.quantity).toBe(240);
    expect(result.converted).toBe(true);
  });

  it("converts cup of flour to ml, not grams (no ewg for display)", () => {
    const ing = {
      unit: "cup",
      category: "grain",
      name_en: "all-purpose flour",
      estimatedWeightGrams: 125,
    };
    const result = convertIngredient(ing, "metric", 1);
    expect(result.unit).toBe("ml");
    expect(result.quantity).toBe(240);
    expect(result.converted).toBe(true);
  });

  it("converts tbsp to ml", () => {
    const ing = { unit: "tbsp" };
    const result = convertIngredient(ing, "metric", 2);
    expect(result.unit).toBe("ml");
    expect(result.quantity).toBe(30);
    expect(result.converted).toBe(true);
  });

  it("converts tsp to ml", () => {
    const ing = { unit: "tsp" };
    const result = convertIngredient(ing, "metric", 0.5);
    expect(result.unit).toBe("ml");
    expect(result.quantity).toBe(3);
    expect(result.converted).toBe(true);
  });

  it("skips conversion when unit is already metric", () => {
    const ing = { unit: "g" };
    const result = convertIngredient(ing, "metric", 200);
    expect(result.converted).toBe(false);
    expect(result.unit).toBe("g");
    expect(result.quantity).toBe(200);
  });

  it("converts pint to ml", () => {
    const ing = { unit: "pint" };
    const result = convertIngredient(ing, "metric", 1);
    expect(result.unit).toBe("ml");
    expect(result.quantity).toBe(470);
    expect(result.converted).toBe(true);
  });

  it("converts large volume to liters", () => {
    const ing = { unit: "cup" };
    const result = convertIngredient(ing, "metric", 5);
    expect(result.unit).toBe("l");
    expect(result.quantity).toBe(1.2);
    expect(result.converted).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// convertIngredient — to imperial
// ---------------------------------------------------------------------------

describe("convertIngredient — to imperial", () => {
  it("converts grams to oz", () => {
    const ing = { quantity: 200, unit: "g", category: "meat", name_en: "beef" };
    const result = convertIngredient(ing, "imperial", 200);
    expect(result.unit).toBe("oz");
    expect(result.quantity).toBe(7);
    expect(result.converted).toBe(true);
  });

  it("converts kg to lb", () => {
    const ing = { quantity: 1, unit: "kg", category: "meat", name_en: "lamb" };
    const result = convertIngredient(ing, "imperial", 1);
    expect(result.unit).toBe("lb");
    expect(result.quantity).toBe(2.25);
    expect(result.converted).toBe(true);
  });

  it("converts ml to cups", () => {
    const ing = { quantity: 500, unit: "ml", category: "dairy", name_en: "milk" };
    const result = convertIngredient(ing, "imperial", 500);
    expect(result.unit).toBe("cup");
    expect(result.converted).toBe(true);
  });

  it("converts small ml to tbsp", () => {
    const ing = { quantity: 15, unit: "ml", category: "condiment", name_en: "soy sauce" };
    const result = convertIngredient(ing, "imperial", 15);
    expect(result.unit).toBe("tbsp");
    expect(result.quantity).toBe(1);
    expect(result.converted).toBe(true);
  });

  it("skips conversion when unit is already imperial", () => {
    const ing = { quantity: 2, unit: "cup", category: "dairy", name_en: "milk" };
    const result = convertIngredient(ing, "imperial", 2);
    expect(result.converted).toBe(false);
    expect(result.unit).toBe("cup");
  });
});

// ---------------------------------------------------------------------------
// convertIngredient — edge cases
// ---------------------------------------------------------------------------

describe("convertIngredient — edge cases", () => {
  it("handles null quantity", () => {
    const ing = { quantity: null, unit: "cup", category: "grain", name_en: "flour" };
    const result = convertIngredient(ing, "metric", null);
    expect(result.converted).toBe(false);
    expect(result.quantity).toBeNull();
  });

  it("handles missing unit", () => {
    const ing = { quantity: 2, unit: null, category: "produce", name_en: "eggs" };
    const result = convertIngredient(ing, "metric", 2);
    expect(result.converted).toBe(false);
  });

  it("handles non-convertible unit (piece)", () => {
    const ing = { quantity: 3, unit: "piece", category: "produce", name_en: "garlic cloves" };
    const result = convertIngredient(ing, "metric", 3);
    expect(result.converted).toBe(false);
    expect(result.quantity).toBe(3);
    expect(result.unit).toBe("piece");
  });

  it("handles modifier units (heaping cup)", () => {
    const ing = {
      quantity: 1,
      unit: "heaping cup",
      category: "dairy",
      name_en: "milk",
    };
    const result = convertIngredient(ing, "metric", 1);
    expect(result.converted).toBe(true);
    expect(result.unit).toBe("ml");
  });
});

// ---------------------------------------------------------------------------
// formatConvertedQuantity
// ---------------------------------------------------------------------------

describe("formatConvertedQuantity", () => {
  it("formats cups with fractions", () => {
    expect(formatConvertedQuantity(0.5, "cup")).toBe("½ cup");
    expect(formatConvertedQuantity(1.5, "cup")).toBe("1½ cup");
  });

  it("formats grams as integers", () => {
    expect(formatConvertedQuantity(125, "g")).toBe("125 g");
  });

  it("formats ml as integers", () => {
    expect(formatConvertedQuantity(240, "ml")).toBe("240 ml");
  });

  it("returns dash for zero/null", () => {
    expect(formatConvertedQuantity(0, "g")).toBe("-");
    expect(formatConvertedQuantity(null, "g")).toBe("-");
  });
});
