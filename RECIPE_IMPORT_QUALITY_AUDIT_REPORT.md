# Recipe Import Pipeline Quality Audit Report

**Date:** 2026-02-18  
**Scope:** `/server/data/recipes/*.recipe.json`  
**Total recipes analyzed:** 4,691

---

## 1. Inventory Summary

| Metric | Count |
|--------|-------|
| Total recipe JSON files | 4,691 |
| Recipes with nutrition data | 4,690 |
| Recipes with empty ingredients | 1 |
| Recipes missing image | 25 (0.5%) |

---

## 2. Deep-Dive Recipe Assessment (8–10 Diverse Recipes)

The following recipes were manually audited across cuisines, difficulties, and types.

### 2.1 Zucchini Carpaccio Salad (Starter, Easy)

**Verdict: Good**

- **Quantities:** Realistic (1 cup parsley, ¼ cup olive oil, 3 zucchini, etc.)
- **Categories:** Basil/parsley → produce ✓; olive oil → condiment ✓; feta → dairy ✓
- **Step DAG:** Logical flow: make vinaigrette → shave zucchini → toss → plate
- **Times:** PT20M total for a simple salad is appropriate
- **Difficulty:** Easy ✓
- **Diets:** Vegetarian ✓ (has feta; omnivorous is reasonable)
- **Seasons:** Summer/autumn ✓
- **Nutrition:** 289 kcal/serving, reasonable for a dressed salad with feta
- **Nutrition tags:** "low-calorie" consistent with 289 kcal ✓

### 2.2 Wonton Soup (Main, Medium)

**Verdict: Good with minor note**

- **Quantities:** Reasonable (10 oz tofu, 5 tbsp cream cheese, 1 packet wrappers)
- **Categories:** Tofu → pantry (debatable; could be "other"); miso → condiment ✓
- **Step DAG:** Solid: filling → assembly → broth → boil → serve. Parallel paths modeled correctly
- **Times:** PT36M active, 0 passive ✓
- **Diets:** Tagged vegetarian ✓ (cream cheese present; vegan would be wrong)
- **Nutrition:** 555 kcal/serving, confidence high. Slightly high for 2 servings but plausible

### 2.3 Yudofu (Simmered Tofu) (Main, Easy)

**Verdict: Needs improvement**

- **Quantities:** All `null` – no quantities for tofu, soy sauce, daikon, etc. Recipe cannot be reproduced without guessing
- **Categories:** Tofu → pantry; Japanese pickles → condiment ✓
- **Step DAG:** Minimal but correct: simmer → serve with garnish
- **Diets:** Vegan ✓ (no animal products)
- **Nutrition:** 0 calories, confidence **low**. Correct given missing quantities
- **Optional ingredients:** Tempura, rice, pickles listed as optional – these are serving suggestions, not core recipe

### 2.4 Yellow Cake with Chocolate Frosting (Dessert, Medium)

**Verdict: Good**

- **Quantities:** Realistic (400g sugar, 280g flour, 770g powdered sugar, 228g cream cheese)
- **Step DAG:** Strong structure: prep pans → preheat → whip eggs → mix batter → bake → cool → frosting → assemble. **Preheat correctly modeled** with `requires: ["preheated_oven"]` on bake step
- **Times:** PT1H10M total, PT50M active, PT20M passive ✓
- **Nutrition:** 921 kcal/serving (12 servings). Rich cake with buttercream – plausible
- **Nutrition tags:** "indulgent" ✓

### 2.5 Zucchini Grilled Corn Salad (Starter, Easy)

**Verdict: Good**

- **Quantities:** Mixed – 2 ears corn, 2 zucchini, 1 avocado; some "big splash", "splash", "handful" – acceptable for dressings
- **Step DAG:** Grill corn || make dressing || peel zucchini → combine → rest
- **Seasons:** Summer/autumn ✓
- **Nutrition:** 214 kcal/serving ✓

### 2.6 Yogurt-Marinated Lamb Kebabs (Main, Medium)

**Verdict: Good**

- **Quantities:** 1 lb yogurt, 2 lb lamb, 14 oz Greek yogurt – realistic
- **Times:** PT12H40M total (overnight marinade), PT40M active – correct
- **Step DAG:** Marinade → marinate (rest) → grill. Tzatziki prepared in parallel ✓
- **Difficulty:** Medium ✓
- **Nutrition:** 305 kcal/serving – possibly low for lamb + tzatziki + pita, but tagged "low-calorie"

### 2.7 Yellow Tomato Bloody Mary (Drink, Easy)

**Verdict: Minor diet inconsistency**

- **Quantities:** 2 tomatoes, 2 oz vodka, 1.5 tbsp lemon juice ✓
- **Shallots:** 0.5 tsp – unit odd (typically tbsp or whole shallots)
- **Diets:** Tagged vegan – vodka is vegan, but optional feta garnish makes it non-vegan. Minor edge case
- **Nutrition:** 228 kcal for 1 serving ✓

### 2.8 Winter Squash Soup with Gruyère Croutons (Main, Medium)

**Verdict: Good**

- **Quantities:** 4 cups butternut + 4 cups acorn squash; 24.25 "inches-thick" baguette slices – unit parsing odd but understandable
- **Step DAG:** Sauté → add broth/squash → simmer → purée → add cream. Croutons: preheat broiler → butter bread → broil → add cheese → broil. **Preheat correctly modeled**
- **Nutrition:** 642 kcal/serving – high but plausible for soup + cheesy croutons

### 2.9 Zuni Cafe's Roasted Chicken (Main, Medium)

**Verdict: Nutrition suspect**

- **Step DAG:** Excellent: salt → rest 24h → preheat → roast (multi-phase) → rest → bread salad (parallel) → serve
- **Nutrition:** **234.6 kcal/serving** – likely **too low**. A 3 lb chicken yields ~800–1000 kcal; bread salad with olive oil, cheese, pine nuts adds more. Expected range: 500–700 kcal/serving for a full meal with bread salad.

### 2.10 Zucchini Noodles & Avocado-Miso Sauce (Main, Easy)

**Verdict: Nutrition error**

- **Recipe:** Raw zucchini noodles, avocado sauce, mango, edamame, almonds. Described as "light 30-minute dinner"
- **Nutrition:** **1,255 kcal per serving** – clearly **wrong**. A bowl of zucchini, half an avocado, ¼ cup hemp seeds, mango, edamame, almonds would typically be 400–600 kcal. Likely per-recipe vs per-serving confusion, or ingredient double-counting.

---

## 3. Patterns of Systematic Errors

### 3.1 Nutrition

| Issue | Count | % |
|-------|-------|---|
| Confidence **high** | 1,997 | 42.6% |
| Confidence **medium** | 2,467 | 52.6% |
| Confidence **low** | 226 | 4.8% |
| >1500 kcal/serving | 42 | 0.9% |
| Desserts <200 kcal (suspicious) | 205 | 4.4% |
| Zero calories (non-low-conf) | 1 | — |

**Findings:**
- **Salads/noodles overestimated:** Light dishes (salads, zucchini noodles) sometimes show 1000–6000+ kcal. Examples:
  - **Tempeh Taco Salad:** 6,010 kcal
  - **Nancy's Chopped Salad:** 2,745 kcal
  - Kale/Clementine/Feta Salad: 1,247 kcal
  - Zucchini Noodles & Avocado-Miso: 1,255 kcal
- Likely causes: serving-size confusion, per-recipe vs per-serving, or OpenNutrition lookup errors (e.g., wrong match for "zucchini" or "avocado").

### 3.2 Diets

- **337 recipes** tagged "vegan" contain animal-product keywords (cheese, cream, butter, eggs, honey, chicken, etc.)
- This is often correct when those ingredients are optional or when the keyword appears in a sub-recipe name, but manual review suggests **some are genuine misclassifications** (e.g., Wonton Soup has cream cheese and is vegetarian, not vegan – correctly not tagged vegan).

### 3.3 Ingredient Categories

- **Tofu** → "pantry" in Wonton Soup, Yudofu. Pantry is defensible for shelf-stable tofu; "other" or a dedicated "plant-protein" category would be clearer.
- **Miso** → "condiment" ✓
- No observed misclassifications of major allergens or core ingredients.

### 3.4 Step DAG

- **25 recipes** have steps that reference ingredients or states not yet defined
- Most recipes have correct DAG structure: preheat modeled with `requires`, parallel sub-recipes (sauce, salad) handled correctly
- Blanquette de veau (example_recipe.json): roux → velouté → whipped cream fold-in is correctly sequenced

### 3.5 Quantities

- **Yudofu** and similar minimal recipes: many `null` quantities when original text says "to taste" or is vague
- Unit oddities: "24.25 inches-thick" for bread; "0.5 tsp" for shallots

---

## 4. Specific Quality Checks

### 4.1 Empty or Missing Ingredients

- **1 recipe** has empty ingredients list

### 4.2 Step–Ingredient Reference Errors

- **25 recipes** have at least one step referencing a non-existent ingredient or state ID

### 4.3 Nutrition Confidence "Low"

- **4.8%** of recipes have `nutritionPerServing.confidence: "low"`
- Typically when quantities are missing (e.g., Yudofu) or ingredients are hard to resolve

### 4.4 Suspicious Calorie Counts

| Severity | Examples |
|----------|----------|
| Critical (>2000 kcal for light dish) | Tempeh Taco Salad (6,010), Nancy's Chopped Salad (2,745) |
| High (1000–2000 kcal for salad/noodles) | Kale-Clementine-Feta Salad (1,247), Zucchini Noodles Avocado-Miso (1,255), Roasted Broccoli & Cranberry Salad (1,286) |
| Low (likely underestimates) | Zuni Cafe Roasted Chicken (235 kcal for full meal with bread salad) |

### 4.5 Missing Images

- **25 recipes** (0.5%) lack both `imageUrl` and `image`

---

## 5. Recommendations

1. **Nutrition validation**
   - Add sanity checks: flag salads/noodles >800 kcal and main courses <200 kcal
   - Review OpenNutrition matching for ingredients with ambiguous names (e.g., "zucchini" as veggie vs pasta)
   - Verify per-serving vs per-recipe calculations

2. **Diet consistency**
   - Cross-check vegan/vegetarian tags against ingredient list
   - Exclude optional garnishes when inferring diet, or tag "vegan-option" when vegan without garnishes

3. **Ingredient completeness**
   - For recipes with many `null` quantities, consider defaults or "to taste" handling
   - Improve unit parsing (e.g., "inches-thick" → "slice" or "piece")

4. **Graph validation**
   - Extend validation to catch forward references and orphan states
   - Consider a batch validation step post-import

5. **Low-confidence nutrition**
   - Surfacing confidence in the UI for the 4.8% low-confidence recipes
   - Optionally trigger manual review for critical recipes (e.g., diets, allergens)

---

## 6. Summary

| Dimension | Assessment |
|-----------|------------|
| Ingredient quantities | Generally good; some nulls in minimal recipes |
| Ingredient categories | Largely correct; tofu → pantry acceptable |
| Step DAG | Strong overall; preheat and parallel sub-recipes modeled well |
| Times | Reasonable |
| Difficulty | Appropriate |
| Diets | 337 potential vegan misclassifications; needs sampling review |
| Seasons | Plausible |
| Nutrition | Major issues: 42 >1500 kcal, many salads/noodles overestimated, some underestimates |
| Nutrition tags | Sometimes inconsistent (e.g., "low-calorie" on moderate dishes) |

The pipeline produces **structurally sound recipes** with valid DAGs and mostly correct metadata. The **primary weakness is nutrition estimation**, especially for salads and vegetable-based dishes, where per-serving logic or ingredient matching appears to fail. A targeted nutrition validation layer would materially improve output quality.
