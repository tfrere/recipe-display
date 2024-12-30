export default {
  navigation: {
    title: "Recipe Display",
    backToRecipes: "Back to recipes",
    addRecipe: "Add recipe",
    views: {
      simple: "Simple",
      graph: "Graph"
    },
    settings: {
      view: "View",
      layout: "Layout",
      preferences: "Preferences",
      units: "Units",
      language: "Language",
      darkMode: "Dark mode",
      lightMode: "Light mode",
      metricUnits: "Metric units",
      imperialUnits: "Imperial units",
      oneColumn: "One column",
      twoColumns: "Two columns",
      unitsSystem: {
        metric: "Metric",
        imperial: "Imperial"
      }
    }
  },
  recipe: {
    time: {
      remaining: "{{time}} remaining",
      total: "Total",
      hour_one: "{{count}} hour",
      hour_other: "{{count}} hours",
      minute: "{{count}} min",
      hourMinute: "{{count}} h {{minutes}} min"
    },
    servings: {
      single: "{{count}} serving",
      multiple: "{{count}} servings"
    },
    sections: {
      ingredients: "Ingredients",
      tools: "Tools",
      preparation: "Preparation"
    },
    actions: {
      print: "Print recipe",
      copy: "Copy recipe",
      copyIngredients: "Copy ingredients list",
      reset: "Reset recipe",
      decreaseServings: "Decrease servings",
      increaseServings: "Increase servings"
    },
    modes: {
      shoppingList: "Shopping List",
      ingredients: "Shopping List"
    },
    diet: {
      normal: "Normal",
      vegetarian: "Vegetarian",
      vegan: "Vegan"
    },
    season: {
      spring: "Spring",
      summer: "Summer",
      autumn: "Autumn",
      winter: "Winter"
    },
    dishType: {
      appetizer: "Appetizer",
      starter: "Starter",
      main: "Main Course",
      side: "Side Dish",
      dessert: "Dessert",
      snack: "Snack",
      breakfast: "Breakfast",
      drink: "Drink"
    },
    type: {
      appetizer: "Appetizer",
      starter: "Starter",
      main: "Main",
      dessert: "Dessert"
    },
    categories: {
      produce: "Produce",
      dairy: "Dairy",
      "pantry-savory": "Pantry - Savory",
      "pantry-sweet": "Pantry - Sweet",
      condiments: "Condiments",
      beverages: "Beverages"
    },
    units: {
      // Base units
      g: "g",
      kg: "kg",
      ml: "ml",
      l: "l",
      // Imperial units
      oz: "oz",
      "fl oz": "fl oz",
      lb: "lb",
      cup: "cup",
      cups: "cups",
      // Volume units
      tablespoon: "tablespoon",
      tablespoons: "tablespoons",
      teaspoon: "teaspoon",
      teaspoons: "teaspoons",
      glass: "glass",
      glasses: "glasses",
      // Short units
      tsp: "tsp",
      tbsp: "tbsp",
      // Integer units
      unit: "unit",
      units: "units",
      piece: "piece",
      pieces: "pieces",
      // Weight units
      gram: "gram",
      grams: "grams",
      kilogram: "kilogram",
      kilograms: "kilograms"
    }
  },
  search: {
    placeholder: 'Search for a recipe...',
    byIngredients: "Search by ingredients...",
    noResults: 'No recipes found',
    results_one: '1 recipe found',
    results_other: '{{count}} recipes found',
    reset_filters: 'Reset filters',
  },
  filters: {
    filterBy: 'Filter by',
    diet: "Diet",
    difficulty: "Difficulty",
    season: "Season",
    quick: "Preparation time",
    quickRecipes: "Quick recipes",
    other: "Other filters"
  },
  results: {
    randomSeasonal: "Random {{season}} Recipes",
    filtered: "Filtered Results"
  },
  diet: {
    vegan: "Vegan",
    vegetarian: "Vegetarian",
    normal: "Regular",
    pescatarian: "Pescatarian"
  },
  difficulty: {
    easy: "Easy",
    medium: "Medium",
    hard: "Hard"
  },
  season: {
    spring: "Spring",
    summer: "Summer",
    autumn: "Autumn",
    winter: "Winter",
    all: "All seasons"
  },
  recipeType: {
    main: "Main course",
    side: "Side dish",
    dessert: "Dessert",
    appetizer: "Appetizer",
    breakfast: "Breakfast",
    snack: "Snack",
    drink: "Drink"
  },
  common: {
    cancel: "Cancel",
    loading: "Loading...",
    error: "An error occurred",
    back: "Back"
  },
  home: {
    title: "My Recipes",
    subtitle: "Discover a collection of delicious recipes",
    search: "Search for a recipe...",
    noRecipes: "No recipes found",
    no_recipes: 'No recipes found',
    no_recipes_description: 'Try modifying your filters or search to find recipes.',
    recipeCard: {
      servings: "{{count}} servings",
      time: {
        preparation: "Preparation",
        cooking: "Cooking",
        total: "Total"
      }
    }
  },
  addRecipe: {
    title: "Add a recipe",
    sourceLabel: "Recipe URL or text",
    sourcePlaceholder: "Enter a recipe website URL or recipe text",
    sourceHelper: "Copy the link or text of the recipe you want to add",
    submit: "Generate recipe"
  }
};
