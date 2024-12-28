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
      remaining: "{{count}} remaining",
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
      shoppingList: "Shopping list mode",
      ingredients: "Ingredients mode"
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
  home: {
    title: "My Recipes",
    search: "Search for a recipe...",
    noRecipes: "No recipes found",
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
  },
  common: {
    cancel: "Cancel"
  }
};
