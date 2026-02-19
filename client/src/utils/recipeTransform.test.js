import { describe, it, expect } from "vitest";

/**
 * Test the recipe format transformation logic (uses/produces → subRecipes).
 * These functions are extracted from RecipeContext.jsx for testability.
 */

const transformToSubRecipes = (recipe) => {
  const ingredientsMap = {};
  (recipe.ingredients || []).forEach((ing) => {
    ingredientsMap[ing.id] = ing;
  });

  const producedStates = new Set();
  (recipe.steps || []).forEach((step) => {
    if (step.produces) {
      producedStates.add(step.produces);
    }
  });

  // Helper: transform a single step to internal format
  const transformStep = (step) => {
    const inputs = (step.uses || []).map((ref) => {
      if (ingredientsMap[ref]) {
        const ing = ingredientsMap[ref];
        return {
          inputType: "component",
          ref: ref,
          type: "ingredient",
          amount: ing.quantity,
          unit: ing.unit,
          category: ing.category,
        };
      } else {
        return {
          inputType: "state",
          ref: ref,
          type: "state",
          name: ref.replace(/_/g, " "),
        };
      }
    });

    const output = step.produces
      ? {
          inputType: "state",
          ref: step.produces,
          type: "state",
          state: step.produces,
          name: step.produces.replace(/_/g, " "),
        }
      : null;

    return {
      id: step.id,
      action: step.action,
      time: step.duration || step.time,
      stepType: step.stepType,
      stepMode: step.isPassive ? "passive" : "active",
      isPassive: step.isPassive || false,
      inputs,
      output,
      uses: step.uses,
      produces: step.produces,
      requires: step.requires,
      tools: step.requires || [],
    };
  };

  // Group steps by subRecipe field
  const stepsByGroup = {};
  const groupOrder = [];
  (recipe.steps || []).forEach((step) => {
    const group = step.subRecipe || "main";
    if (!stepsByGroup[group]) {
      stepsByGroup[group] = [];
      groupOrder.push(group);
    }
    stepsByGroup[group].push(step);
  });

  // Build subRecipes array, one per group
  const subRecipes = groupOrder.map((groupName) => {
    const groupSteps = stepsByGroup[groupName];
    const transformedSteps = groupSteps.map(transformStep);

    // Collect ingredients used in this sub-recipe's steps
    const groupIngredientsByRef = {};
    groupSteps.forEach((step) => {
      (step.uses || []).forEach((ref) => {
        if (ingredientsMap[ref] && !groupIngredientsByRef[ref]) {
          const ing = ingredientsMap[ref];
          groupIngredientsByRef[ref] = {
            inputType: "component",
            ref: ref,
            type: "ingredient",
            amount: ing.quantity,
            unit: ing.unit,
            category: ing.category,
            name: ing.name,
          };
        }
      });
    });

    const title =
      groupName === "main"
        ? recipe.metadata?.title || "Recipe"
        : groupName.charAt(0).toUpperCase() + groupName.slice(1);

    return {
      id: groupName,
      title,
      ingredients: Object.values(groupIngredientsByRef),
      steps: transformedSteps,
    };
  });

  return {
    ...recipe,
    subRecipes,
  };
};

// Sample recipe - single subRecipe (all default to "main")
const sampleRecipe = {
  metadata: {
    title: "Blanquette de veau",
    author: "Cuisine Traditionnelle",
    servings: 4,
    prepTime: "PT30M",
    cookTime: "PT1H30M",
    difficulty: "moyen",
    imageUrl: null,
  },
  ingredients: [
    { id: "veau", name: "Veau (épaule)", quantity: 800, unit: "g", category: "meat" },
    { id: "carottes", name: "Carottes", quantity: 3, unit: "unit", category: "produce" },
    { id: "oignon", name: "Oignon", quantity: 1, unit: "unit", category: "produce" },
    { id: "bouquet_garni", name: "Bouquet garni", quantity: 1, unit: "unit", category: "spice" },
    { id: "beurre", name: "Beurre", quantity: 40, unit: "g", category: "dairy" },
    { id: "farine", name: "Farine", quantity: 40, unit: "g", category: "pantry" },
    { id: "creme_fraiche", name: "Crème fraîche", quantity: 200, unit: "ml", category: "dairy" },
    { id: "jaune_oeuf", name: "Jaune d'œuf", quantity: 2, unit: "unit", category: "egg" },
    { id: "citron", name: "Jus de citron", quantity: 1, unit: "tbsp", category: "produce" },
  ],
  tools: ["cocotte", "fouet", "casserole"],
  steps: [
    {
      id: "step_decoupe",
      action: "Découper le veau en morceaux de 3-4 cm",
      stepType: "prep",
      isPassive: false,
      duration: "PT15M",
      uses: ["veau"],
      produces: "veau_decoupe",
      requires: [],
    },
    {
      id: "step_cuisson",
      action: "Faire cuire la viande avec les carottes, l'oignon et le bouquet garni dans l'eau frémissante pendant 1h30",
      stepType: "cook",
      isPassive: true,
      duration: "PT1H30M",
      uses: ["veau_decoupe", "carottes", "oignon", "bouquet_garni"],
      produces: "viande_cuite",
      requires: ["cocotte"],
    },
    {
      id: "step_roux",
      action: "Préparer un roux blanc avec le beurre et la farine",
      stepType: "cook",
      isPassive: false,
      duration: "PT5M",
      uses: ["beurre", "farine"],
      produces: "roux_blanc",
      requires: ["casserole", "fouet"],
    },
    {
      id: "step_sauce",
      action: "Mouiller le roux avec le bouillon de cuisson filtré, ajouter la crème fraîche, le jaune d'œuf et le jus de citron",
      stepType: "combine",
      isPassive: false,
      duration: "PT10M",
      uses: ["roux_blanc", "viande_cuite", "creme_fraiche", "jaune_oeuf", "citron"],
      produces: "blanquette_terminee",
      requires: ["fouet"],
    },
  ],
  finalState: "blanquette_terminee",
  originalText: "Blanquette de veau traditionnelle...",
};

// Sample recipe with multiple subRecipes
const sampleMultiSubRecipe = {
  metadata: {
    title: "Tarte aux pommes",
    servings: 6,
    difficulty: "medium",
    recipeType: "dessert",
  },
  ingredients: [
    { id: "farine", name: "Farine", quantity: 250, unit: "g", category: "pantry" },
    { id: "beurre", name: "Beurre", quantity: 125, unit: "g", category: "dairy" },
    { id: "eau", name: "Eau froide", quantity: 50, unit: "ml", category: "beverage" },
    { id: "pommes", name: "Pommes", quantity: 6, unit: "pieces", category: "produce" },
    { id: "sucre", name: "Sucre", quantity: 80, unit: "g", category: "pantry" },
    { id: "cannelle", name: "Cannelle", quantity: 1, unit: "tsp", category: "spice" },
  ],
  tools: ["four"],
  steps: [
    {
      id: "step_pate_1",
      action: "Mélanger la farine et le beurre froid coupé en dés",
      stepType: "combine",
      subRecipe: "pate",
      uses: ["farine", "beurre"],
      produces: "sable",
      requires: [],
    },
    {
      id: "step_pate_2",
      action: "Ajouter l'eau et former une boule, réfrigérer 30 min",
      stepType: "rest",
      isPassive: true,
      duration: "PT30M",
      subRecipe: "pate",
      uses: ["sable", "eau"],
      produces: "pate_reposee",
      requires: [],
    },
    {
      id: "step_garniture_1",
      action: "Éplucher et couper les pommes en fines tranches",
      stepType: "prep",
      duration: "PT10M",
      subRecipe: "garniture",
      uses: ["pommes"],
      produces: "pommes_tranchees",
      requires: [],
    },
    {
      id: "step_garniture_2",
      action: "Mélanger les pommes avec le sucre et la cannelle",
      stepType: "combine",
      subRecipe: "garniture",
      uses: ["pommes_tranchees", "sucre", "cannelle"],
      produces: "garniture_pommes",
      requires: [],
    },
    {
      id: "step_assemblage",
      action: "Étaler la pâte, disposer la garniture, cuire 35 min à 180°C",
      stepType: "cook",
      duration: "PT35M",
      temperature: 180,
      subRecipe: "assemblage",
      uses: ["pate_reposee", "garniture_pommes"],
      produces: "tarte_cuite",
      requires: ["four"],
    },
  ],
  finalState: "tarte_cuite",
};

describe("transformToSubRecipes - single group", () => {
  const transformed = transformToSubRecipes(sampleRecipe);

  it("should create a single 'main' subRecipe when no subRecipe field", () => {
    expect(transformed.subRecipes).toHaveLength(1);
    expect(transformed.subRecipes[0].id).toBe("main");
  });

  it("should use recipe title as main subRecipe title", () => {
    expect(transformed.subRecipes[0].title).toBe("Blanquette de veau");
  });

  it("should extract all ingredients used in steps", () => {
    const ingredients = transformed.subRecipes[0].ingredients;
    expect(ingredients.length).toBe(9);
  });

  it("should preserve ingredient amounts from quantity field", () => {
    const ingredients = transformed.subRecipes[0].ingredients;
    const veau = ingredients.find((i) => i.ref === "veau");
    expect(veau).toBeDefined();
    expect(veau.amount).toBe(800);
    expect(veau.unit).toBe("g");
    expect(veau.category).toBe("meat");
  });

  it("should keep null amount for 'to taste' ingredients (no 0tsp)", () => {
    // Test with a recipe that has ingredients without quantities
    const recipeWithNullQty = {
      ...sampleRecipe,
      ingredients: [
        ...sampleRecipe.ingredients,
        { id: "sel", name: "Sel", quantity: null, unit: null, category: "spice" },
      ],
      steps: [
        ...sampleRecipe.steps,
        {
          id: "step_assaisonnement",
          action: "Assaisonner de sel",
          stepType: "combine",
          uses: ["sel", "blanquette_terminee"],
          produces: "blanquette_assaisonnee",
          requires: [],
        },
      ],
    };
    const result = transformToSubRecipes(recipeWithNullQty);
    const mainSub = result.subRecipes[0];
    const sel = mainSub.ingredients.find((i) => i.ref === "sel");
    expect(sel).toBeDefined();
    expect(sel.amount).toBeNull();
    expect(sel.unit).toBeNull();
  });

  it("should transform steps with correct internal structure", () => {
    const steps = transformed.subRecipes[0].steps;
    expect(steps).toHaveLength(4);

    const firstStep = steps[0];
    expect(firstStep.id).toBe("step_decoupe");
    expect(firstStep.action).toContain("Découper le veau");
    expect(firstStep.stepType).toBe("prep");
  });

  it("should convert isPassive to stepMode", () => {
    const steps = transformed.subRecipes[0].steps;

    const activeStep = steps.find((s) => s.id === "step_decoupe");
    expect(activeStep.stepMode).toBe("active");
    expect(activeStep.isPassive).toBe(false);

    const passiveStep = steps.find((s) => s.id === "step_cuisson");
    expect(passiveStep.stepMode).toBe("passive");
    expect(passiveStep.isPassive).toBe(true);
  });

  it("should map duration (ISO 8601) to time field", () => {
    const steps = transformed.subRecipes[0].steps;
    const cuisson = steps.find((s) => s.id === "step_cuisson");
    expect(cuisson.time).toBe("PT1H30M");
  });

  it("should build inputs from uses[] - ingredients", () => {
    const steps = transformed.subRecipes[0].steps;
    const firstStep = steps[0]; // uses: ["veau"]

    expect(firstStep.inputs).toHaveLength(1);
    expect(firstStep.inputs[0].type).toBe("ingredient");
    expect(firstStep.inputs[0].ref).toBe("veau");
    expect(firstStep.inputs[0].amount).toBe(800);
  });

  it("should build inputs from uses[] - states from previous steps", () => {
    const steps = transformed.subRecipes[0].steps;
    const cuisson = steps[1]; // uses: ["veau_decoupe", "carottes", "oignon", "bouquet_garni"]

    const stateInput = cuisson.inputs.find((i) => i.ref === "veau_decoupe");
    expect(stateInput).toBeDefined();
    expect(stateInput.type).toBe("state");

    const ingredientInput = cuisson.inputs.find((i) => i.ref === "carottes");
    expect(ingredientInput).toBeDefined();
    expect(ingredientInput.type).toBe("ingredient");
  });

  it("should build output from produces", () => {
    const steps = transformed.subRecipes[0].steps;
    const firstStep = steps[0];

    expect(firstStep.output).toBeDefined();
    expect(firstStep.output.type).toBe("state");
    expect(firstStep.output.state).toBe("veau_decoupe");
    expect(firstStep.output.ref).toBe("veau_decoupe");
  });

  it("should map requires to tools", () => {
    const steps = transformed.subRecipes[0].steps;
    const cuisson = steps.find((s) => s.id === "step_cuisson");
    expect(cuisson.tools).toEqual(["cocotte"]);
    expect(cuisson.requires).toEqual(["cocotte"]);
  });

  it("should preserve original fields (uses, produces, requires)", () => {
    const steps = transformed.subRecipes[0].steps;
    const sauce = steps.find((s) => s.id === "step_sauce");

    expect(sauce.uses).toEqual([
      "roux_blanc",
      "viande_cuite",
      "creme_fraiche",
      "jaune_oeuf",
      "citron",
    ]);
    expect(sauce.produces).toBe("blanquette_terminee");
    expect(sauce.requires).toEqual(["fouet"]);
  });

  it("should preserve metadata and other root fields", () => {
    expect(transformed.metadata.title).toBe("Blanquette de veau");
    expect(transformed.metadata.servings).toBe(4);
    expect(transformed.finalState).toBe("blanquette_terminee");
    expect(transformed.originalText).toBeDefined();
  });
});

describe("transformToSubRecipes - multiple sub-recipes", () => {
  const transformed = transformToSubRecipes(sampleMultiSubRecipe);

  it("should create one subRecipe per group", () => {
    expect(transformed.subRecipes).toHaveLength(3);
  });

  it("should preserve group order from steps", () => {
    expect(transformed.subRecipes[0].id).toBe("pate");
    expect(transformed.subRecipes[1].id).toBe("garniture");
    expect(transformed.subRecipes[2].id).toBe("assemblage");
  });

  it("should capitalize non-main subRecipe titles", () => {
    expect(transformed.subRecipes[0].title).toBe("Pate");
    expect(transformed.subRecipes[1].title).toBe("Garniture");
    expect(transformed.subRecipes[2].title).toBe("Assemblage");
  });

  it("should assign correct steps to each subRecipe", () => {
    expect(transformed.subRecipes[0].steps).toHaveLength(2); // pate: 2 steps
    expect(transformed.subRecipes[1].steps).toHaveLength(2); // garniture: 2 steps
    expect(transformed.subRecipes[2].steps).toHaveLength(1); // assemblage: 1 step
  });

  it("should assign ingredients per subRecipe based on uses", () => {
    const pateIngs = transformed.subRecipes[0].ingredients;
    const garnitureIngs = transformed.subRecipes[1].ingredients;
    const assemblageIngs = transformed.subRecipes[2].ingredients;

    // Pâte uses: farine, beurre, eau
    expect(pateIngs.map((i) => i.ref).sort()).toEqual(["beurre", "eau", "farine"]);

    // Garniture uses: pommes, sucre, cannelle
    expect(garnitureIngs.map((i) => i.ref).sort()).toEqual(["cannelle", "pommes", "sucre"]);

    // Assemblage uses only states (pate_reposee, garniture_pommes) - no raw ingredients
    expect(assemblageIngs).toHaveLength(0);
  });

  it("should handle cross-subRecipe state references in uses", () => {
    const assemblageSteps = transformed.subRecipes[2].steps;
    const assemblyStep = assemblageSteps[0];

    // This step uses states from other sub-recipes
    const pateInput = assemblyStep.inputs.find((i) => i.ref === "pate_reposee");
    expect(pateInput).toBeDefined();
    expect(pateInput.type).toBe("state");

    const garnitureInput = assemblyStep.inputs.find((i) => i.ref === "garniture_pommes");
    expect(garnitureInput).toBeDefined();
    expect(garnitureInput.type).toBe("state");
  });

  it("should handle isPassive correctly in sub-recipe steps", () => {
    const pateSteps = transformed.subRecipes[0].steps;
    const reposStep = pateSteps.find((s) => s.id === "step_pate_2");
    expect(reposStep.isPassive).toBe(true);
    expect(reposStep.stepMode).toBe("passive");
  });

  it("should handle requires (tools) in sub-recipe steps", () => {
    const assemblageSteps = transformed.subRecipes[2].steps;
    expect(assemblageSteps[0].tools).toEqual(["four"]);
  });
});
