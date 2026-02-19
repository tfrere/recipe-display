"""
Extract ingredient-specific portion weights from USDA FoodData Central.

Sources:
  - Foundation Foods (Dec 2025) — high-quality, preferred
  - SR Legacy (Apr 2018) — broad coverage

Produces a curated portion_weights.json (~500-800 clean ingredient names)
with structure: { "ingredient_name": { "unit": grams_per_unit, ... }, ... }
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
FOUNDATION_PATH = SCRIPT_DIR / "usda_data" / "foundation_foods" / "FoodData_Central_foundation_food_json_2025-12-18.json"
SR_LEGACY_PATH = SCRIPT_DIR / "usda_data" / "sr_legacy" / "FoodData_Central_sr_legacy_food_json_2018-04.json"
OUTPUT_PATH = SCRIPT_DIR / ".." / "src" / "recipe_scraper" / "data" / "portion_weights.json"

# ── Skip patterns: foods irrelevant to recipe cooking ──────────────────
SKIP_PATTERNS = [
    "infant formula", "baby food", "babyfood", "gerber", "toddler",
    "mcdonald", "burger king", "wendy's", "taco bell",
    "pizza hut", "subway", "kfc", "arby's", "applebee's",
    "chick-fil-a", "denny's", "popeyes", "domino's",
    "fast foods", "restaurant",
    "usda commodity",
    "cereals, ready-to-eat",
    "supplement", "protein powder",
    "formulated bar",
]

# ── Modifier → canonical unit mapping ──────────────────────────────────
_CUP_VARIANTS = [
    "cup", "cups", "cup, chopped", "cup chopped",
    "cup, chopped or diced", "cup, diced", "cup, cubes",
    "cup, sliced", "cup slices", "cup, shredded",
    "cup, mashed", "cup, pureed", "cup, halves",
    "cup, pieces", "cup, sections, with juice",
    "cup, whole", "cup, crumbled", "cup, packed",
    "cup (1 NLEA serving)", "cup (8 fl oz)", "cup, raw",
    "cup, melted",
]
_TBSP_VARIANTS = ["tbsp", "tablespoon"]
_TSP_VARIANTS = ["tsp", "teaspoon"]

UNIT_EXACT = {}
for v in _CUP_VARIANTS:
    UNIT_EXACT[v] = "cup"
for v in _TBSP_VARIANTS:
    UNIT_EXACT[v] = "tbsp"
for v in _TSP_VARIANTS:
    UNIT_EXACT[v] = "tsp"
UNIT_EXACT["oz"] = "oz"
UNIT_EXACT["fl oz"] = "fl_oz"
UNIT_EXACT["lb"] = "lb"

PIECE_EXACT = {
    "medium": "piece", "large": "piece", "small": "piece",
    "slice": "slice", "slice, medium": "slice",
    "clove": "clove",
    "sprig": "sprig", "sprigs": "sprig",
    "leaf": "leaf", "leaves": "leaf",
    "stalk": "stalk", "stalk, medium": "stalk",
    "ear": "piece", "ear, medium": "piece",
    "bunch": "bunch",
    "head": "head", "head, medium": "head",
    "bulb": "bulb",
    "fruit": "piece", "item": "piece", "piece": "piece",
    "patty": "piece", "link": "piece",
    "ring": "piece", "strip": "piece",
    "fillet": "piece", "breast": "piece",
    "drumstick": "piece", "thigh": "piece", "wing": "piece",
}

# ── USDA description → clean recipe name ──────────────────────────────
# State qualifiers to strip from the end of names
_COOKING_STATES = {
    "raw", "cooked", "boiled", "baked", "roasted", "fried",
    "steamed", "grilled", "canned", "dried", "frozen",
    "fresh", "whole", "ground", "mature seeds", "dry",
    "enriched", "unenriched", "drained", "solids and liquids",
    "with bone", "meat only", "boneless", "skinless",
    "unprepared", "prepared", "plain", "with salt", "without salt",
    "with added ascorbic acid", "without added ascorbic acid",
    "salted", "unsalted",
}

# Explicit name overrides: USDA prefix → our name
_NAME_OVERRIDES = {
    "cheese, cheddar": "cheddar cheese",
    "cheese, parmesan": "parmesan cheese",
    "cheese, mozzarella": "mozzarella cheese",
    "cheese, swiss": "swiss cheese",
    "cheese, feta": "feta cheese",
    "cheese, gouda": "gouda cheese",
    "cheese, brie": "brie cheese",
    "cheese, cream": "cream cheese",
    "cheese, cottage": "cottage cheese",
    "cheese, ricotta": "ricotta cheese",
    "cheese, goat": "goat cheese",
    "cheese, gruyere": "gruyere cheese",
    "cheese, blue": "blue cheese",
    "cheese, provolone": "provolone cheese",
    "cheese, camembert": "camembert cheese",
    "cheese, colby": "colby cheese",
    "cheese, monterey": "monterey jack cheese",
    "cheese, neufchatel": "neufchatel cheese",
    "nuts, almonds": "almonds",
    "nuts, cashew nuts": "cashews",
    "nuts, walnuts": "walnuts",
    "nuts, pecans": "pecans",
    "nuts, pine nuts": "pine nuts",
    "nuts, pistachios": "pistachios",
    "nuts, macadamia nuts": "macadamia nuts",
    "nuts, hazelnuts or filberts": "hazelnuts",
    "nuts, brazil nuts": "brazil nuts",
    "nuts, coconut meat": "coconut",
    "nuts, coconut milk": "coconut milk",
    "nuts, coconut cream": "coconut cream",
    "nuts, coconut water": "coconut water",
    "seeds, sesame seeds": "sesame seeds",
    "seeds, sunflower seed kernels": "sunflower seeds",
    "seeds, pumpkin and squash seed kernels": "pumpkin seeds",
    "seeds, flaxseed": "flaxseed",
    "seeds, chia seeds": "chia seeds",
    "oil, olive": "olive oil",
    "oil, coconut": "coconut oil",
    "oil, sesame": "sesame oil",
    "oil, canola": "canola oil",
    "oil, vegetable": "vegetable oil",
    "oil, peanut": "peanut oil",
    "oil, sunflower": "sunflower oil",
    "oil, soybean": "soybean oil",
    "oil, corn": "corn oil",
    "oil, avocado": "avocado oil",
    "beans, black": "black beans",
    "beans, kidney": "kidney beans",
    "beans, white": "white beans",
    "beans, lima": "lima beans",
    "beans, navy": "navy beans",
    "beans, pinto": "pinto beans",
    "beans, snap": "green beans",
    "peas, green": "green peas",
    "peas, split": "split peas",
    "peppers, sweet": "bell pepper",
    "peppers, hot chili": "chili pepper",
    "peppers, jalapeno": "jalapeno",
    "peppers, serrano": "serrano pepper",
    "lettuce, iceberg": "iceberg lettuce",
    "lettuce, cos or romaine": "romaine lettuce",
    "coriander (cilantro) leaves": "cilantro",
    "wheat flour, white": "all-purpose flour",
    "wheat flour, whole-grain": "whole wheat flour",
    "rice, white, long-grain": "rice",
    "rice, brown, long-grain": "brown rice",
    "milk, whole": "whole milk",
    "milk, reduced fat, fluid, 2% milkfat": "milk",
    "cream, fluid, heavy whipping": "heavy cream",
    "cream, heavy whipping": "heavy cream",
    "cream, sour": "sour cream",
    "yogurt, plain": "yogurt",
    "yogurt, greek": "greek yogurt",
    "egg, whole": "egg",
    "egg, white": "egg white",
    "egg, yolk": "egg yolk",
    "butter, salted": "butter",
    "butter, without salt": "unsalted butter",
    "lemon juice": "lemon juice",
    "lime juice": "lime juice",
    "vinegar, distilled": "vinegar",
    "vinegar, balsamic": "balsamic vinegar",
    "vinegar, cider": "apple cider vinegar",
    "soy sauce made from soy and wheat (shoyu)": "soy sauce",
    "fish sauce": "fish sauce",
    "sauce, hoisin": "hoisin sauce",
    "sauce, teriyaki": "teriyaki sauce",
    "sauce, hot chile": "hot sauce",
    "sauce, worcestershire": "worcestershire sauce",
    "sauce, barbecue": "barbecue sauce",
    "mustard, prepared": "mustard",
    "ketchup": "ketchup",
    "mayonnaise": "mayonnaise",
    "tomato products, canned, paste": "tomato paste",
    "tomato paste": "tomato paste",
    "tomato products, canned, sauce": "tomato sauce",
    "tomato sauce": "tomato sauce",
    "tomato products, canned, puree": "tomato puree",
    "tomato puree": "tomato puree",
    "broccoli": "broccoli",
    "cauliflower": "cauliflower",
    "spinach": "spinach",
    "kale": "kale",
    "cabbage": "cabbage",
    "carrots": "carrots",
    "celery": "celery",
    "cucumber": "cucumber",
    "zucchini": "zucchini",
    "eggplant": "eggplant",
    "potatoes": "potatoes",
    "sweet potato": "sweet potato",
    "corn, sweet": "corn",
    "mushrooms": "mushrooms",
    "avocados": "avocado",
    "beets": "beets",
    "radishes": "radishes",
    "turnips": "turnips",
    "squash, summer": "summer squash",
    "squash, winter": "winter squash",
    "pumpkin": "pumpkin",
    "asparagus": "asparagus",
    "artichokes": "artichokes",
    "leeks": "leeks",
    "shallots": "shallots",
    "scallions": "scallions",
    "ginger root": "ginger",
    "spices, ginger": "ground ginger",
    "spices, cinnamon": "cinnamon",
    "spices, cumin seed": "cumin",
    "spices, paprika": "paprika",
    "spices, turmeric": "turmeric",
    "spices, nutmeg": "nutmeg",
    "spices, pepper, black": "black pepper",
    "spices, pepper, white": "white pepper",
    "spices, pepper, red or cayenne": "cayenne pepper",
    "spices, cayenne pepper": "cayenne pepper",
    "spices, oregano": "dried oregano",
    "spices, thyme": "dried thyme",
    "spices, basil": "dried basil",
    "spices, rosemary": "dried rosemary",
    "spices, garlic powder": "garlic powder",
    "spices, onion powder": "onion powder",
    "spices, chili powder": "chili powder",
    "spices, curry powder": "curry powder",
    "spices, coriander seed": "ground coriander",
    "spices, cardamom": "cardamom",
    "spices, cloves": "cloves",
    "spices, allspice": "allspice",
    "spices, fennel seed": "fennel seeds",
    "spices, mustard seed": "mustard seeds",
    "spices, saffron": "saffron",
    "cocoa, dry powder": "cocoa powder",
    "baking chocolate, unsweetened": "unsweetened chocolate",
    "chocolate, dark": "dark chocolate",
    "sugars, granulated": "sugar",
    "sugars, brown": "brown sugar",
    "sugars, powdered": "powdered sugar",
    "syrups, maple": "maple syrup",
    "molasses": "molasses",
    "cornstarch": "cornstarch",
    "baking powder": "baking powder",
    "leavening agents, baking powder": "baking powder",
    "baking powder": "baking powder",
    "leavening agents, baking soda": "baking soda",
    "baking soda": "baking soda",
    "gelatin, dry powder": "gelatin",
    "tofu": "tofu",
    "tempeh": "tempeh",
    "hummus": "hummus",
    "tahini": "tahini",
}


def simplify_name(description: str) -> str | None:
    """Convert USDA description to a usable recipe ingredient name."""
    desc = description.lower().strip()

    # Check explicit overrides (longest prefix match)
    for prefix, clean_name in sorted(_NAME_OVERRIDES.items(), key=lambda x: -len(x[0])):
        if desc.startswith(prefix):
            return clean_name

    # Remove parenthetical details
    desc = re.sub(r'\([^)]*\)', '', desc).strip()

    # Split on commas and strip cooking states from the end
    parts = [p.strip() for p in desc.split(",")]
    while len(parts) > 1 and any(s in parts[-1] for s in _COOKING_STATES):
        parts.pop()

    name = parts[0].strip()  # Take the primary name
    if not name or len(name) < 2:
        return None

    # Skip if still too generic or contains brand names
    if name in {"cereals", "snacks", "candies", "cookies", "crackers", "cake", "pie"}:
        return None

    name = name.rstrip(",").strip()
    return name if len(name) < 50 else None


def normalize_modifier(modifier: str) -> tuple:
    """Parse USDA modifier → (canonical_unit, 1.0) or (None, None)."""
    mod = modifier.lower().strip()
    if not mod:
        return None, None

    if mod in UNIT_EXACT:
        return UNIT_EXACT[mod], 1.0
    if mod in PIECE_EXACT:
        return PIECE_EXACT[mod], 1.0

    # Handle "unit, qualifier" patterns: "tsp, ground", "cup, fluid", etc.
    base = mod.split(",")[0].strip()
    if base in UNIT_EXACT:
        return UNIT_EXACT[base], 1.0
    if base in PIECE_EXACT:
        return PIECE_EXACT[base], 1.0

    # Prefix-match for cup variants
    if mod.startswith("cup"):
        return "cup", 1.0

    # Prefix-match for piece variants
    for pattern, unit in PIECE_EXACT.items():
        if mod.startswith(pattern):
            return unit, 1.0

    return None, None


def extract_portions(foods: list) -> dict:
    """Extract portion weight data from USDA foods list."""
    result = defaultdict(dict)

    for food in foods:
        desc = food.get("description", "")
        if any(skip in desc.lower() for skip in SKIP_PATTERNS):
            continue

        portions = food.get("foodPortions", [])
        if not portions:
            continue

        name = simplify_name(desc)
        if not name:
            continue

        for portion in portions:
            modifier = portion.get("modifier", "")
            gram_weight = portion.get("gramWeight", 0)
            amount = portion.get("amount", 1.0)

            if not modifier or not gram_weight or gram_weight <= 0:
                continue

            unit_key, _ = normalize_modifier(modifier)
            if unit_key is None:
                continue

            grams_per_unit = round(gram_weight / max(amount, 0.01), 1)
            if grams_per_unit <= 0 or grams_per_unit > 5000:
                continue

            if unit_key not in result[name]:
                result[name][unit_key] = grams_per_unit

    return dict(result)


def merge_data(foundation: dict, sr_legacy: dict) -> dict:
    """Merge Foundation Foods (priority) with SR Legacy."""
    merged = defaultdict(dict)
    for name, units in sr_legacy.items():
        for unit, grams in units.items():
            merged[name][unit] = grams
    for name, units in foundation.items():
        for unit, grams in units.items():
            merged[name][unit] = grams
    return dict(merged)


def add_aliases(data: dict) -> dict:
    """Generate useful plural/singular aliases."""
    extra = {}
    for name, units in list(data.items()):
        # "carrots" -> also match "carrot"
        if name.endswith("s") and not name.endswith("ss") and not name.endswith("us"):
            singular = name[:-1]
            if singular not in data and singular not in extra:
                extra[singular] = units
        # "avocado" -> also match "avocados"
        if not name.endswith("s"):
            plural = name + "s"
            if plural not in data and plural not in extra:
                extra[plural] = units

    data.update(extra)
    return data


# ── Post-extraction corrections ────────────────────────────────────────
# Override values where USDA data matches wrong variant
# (e.g., cherry tomato instead of medium tomato)
_MANUAL_OVERRIDES = {
    "heavy cream": {"cup": 238.0, "tbsp": 15.0, "fl_oz": 29.8},
    "tomatoes": {"piece": 149.0, "cup": 180.0, "slice": 20.0, "tbsp": 15.0},
    "tomato": {"piece": 149.0, "cup": 180.0, "slice": 20.0, "tbsp": 15.0},
    "carrots": {"piece": 61.0, "cup": 128.0, "slice": 3.0, "tbsp": 9.7},
    "carrot": {"piece": 61.0, "cup": 128.0, "slice": 3.0, "tbsp": 9.7},
    "potatoes": {"piece": 150.0, "cup": 150.0},
    "potato": {"piece": 150.0, "cup": 150.0},
    "egg": {"piece": 50.0, "cup": 243.0, "tbsp": 15.0},
    "eggs": {"piece": 50.0, "cup": 243.0, "tbsp": 15.0},
    "lentils": {"cup": 192.0, "tbsp": 12.0},
    "lentil": {"cup": 192.0, "tbsp": 12.0},
    "onion": {"piece": 110.0, "cup": 160.0, "slice": 14.0},
    "celery": {"stalk": 40.0, "cup": 101.0, "tbsp": 7.5},
}


def main():
    print("Loading Foundation Foods...")
    with open(FOUNDATION_PATH) as f:
        ff_foods = json.load(f).get("FoundationFoods", [])
    print(f"  {len(ff_foods)} foods")

    print("Loading SR Legacy...")
    with open(SR_LEGACY_PATH) as f:
        sr_foods = json.load(f).get("SRLegacyFoods", [])
    print(f"  {len(sr_foods)} foods")

    print("\nExtracting portions...")
    ff_portions = extract_portions(ff_foods)
    sr_portions = extract_portions(sr_foods)
    print(f"  Foundation: {len(ff_portions)} ingredients")
    print(f"  SR Legacy: {len(sr_portions)} ingredients")

    merged = merge_data(ff_portions, sr_portions)

    # Keep only entries with at least one useful unit
    useful = {"cup", "tbsp", "tsp", "piece", "slice", "clove", "head", "bunch", "bulb", "sprig", "leaf", "stalk"}
    filtered = {k: v for k, v in merged.items() if any(u in useful for u in v)}
    filtered = add_aliases(filtered)

    # Apply manual overrides for known-wrong entries
    for name, overrides in _MANUAL_OVERRIDES.items():
        if name in filtered:
            filtered[name].update(overrides)
        else:
            filtered[name] = overrides

    sorted_data = dict(sorted(filtered.items()))

    output = {
        "_meta": {
            "description": "Ingredient-specific unit-to-gram conversions from USDA FoodData Central",
            "sources": [
                "USDA Foundation Foods (December 2025)",
                "USDA SR Legacy (April 2018)",
            ],
            "license": "Public Domain (CC0 1.0 Universal)",
            "generated_at": datetime.now().isoformat(),
            "total_ingredients": len(sorted_data),
        },
        **sorted_data,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten {len(sorted_data)} ingredients to {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")

    # Validation: check key recipe ingredients
    print("\n=== Key ingredient validation ===")
    must_have = [
        "rice", "all-purpose flour", "sugar", "butter", "olive oil",
        "honey", "chickpeas", "lentils", "onions", "garlic",
        "tomatoes", "cheddar cheese", "parmesan cheese", "feta cheese",
        "almonds", "walnuts", "oats", "cilantro", "basil",
        "parsley", "heavy cream", "yogurt", "quinoa",
        "coconut milk", "soy sauce", "bread", "egg",
        "brown sugar", "maple syrup", "tofu", "broccoli",
        "spinach", "carrots", "potatoes", "avocado",
        "cumin", "paprika", "cinnamon", "black pepper",
        "tomato paste", "baking powder", "cornstarch",
    ]
    found = 0
    for ingredient in must_have:
        if ingredient in sorted_data:
            print(f"  OK  {ingredient}: {sorted_data[ingredient]}")
            found += 1
        else:
            print(f"  MISS {ingredient}")
    print(f"\nCoverage: {found}/{len(must_have)} ({100*found/len(must_have):.0f}%)")


if __name__ == "__main__":
    main()
