export default {
  navigation: {
    title: "Recipe Display",
    backToRecipes: "Retour aux recettes",
    addRecipe: "Ajouter une recette",
    views: {
      simple: "Simple",
      graph: "Graph"
    },
    settings: {
      view: "Vue",
      layout: "Disposition",
      preferences: "Préférences",
      units: "Unités",
      language: "Langue",
      darkMode: "Mode sombre",
      lightMode: "Mode clair",
      metricUnits: "Unités métriques",
      imperialUnits: "Unités impériales",
      oneColumn: "Une colonne",
      twoColumns: "Deux colonnes",
      unitsSystem: {
        metric: "Métrique",
        imperial: "Impérial"
      }
    }
  },
  settings: {
    twoColumnLayout: "Vue en deux colonnes",
    singleColumnLayout: "Vue en une colonne"
  },
  home: {
    title: "Mes Recettes",
    search: "Rechercher une recette...",
    noRecipes: "Aucune recette trouvée",
    recipeCard: {
      servings: "{{count}} personnes",
      time: {
        preparation: "Préparation",
        cooking: "Cuisson",
        total: "Total"
      }
    }
  },
  addRecipe: {
    title: "Ajouter une recette",
    sourceLabel: "URL ou texte de la recette",
    sourcePlaceholder: "Entrez l'URL d'un site de recettes ou le texte d'une recette",
    sourceHelper: "Copiez le lien ou le texte de la recette que vous souhaitez ajouter",
    submit: "Générer la recette"
  },
  recipe: {
    time: {
      remaining: "{{count}} restantes",
      total: "Total",
      hour_one: "{{count}} heure",
      hour_other: "{{count}} heures",
      minute: "{{count}} min",
      hourMinute: "{{count}} h {{minutes}} min"
    },
    servings: {
      single: "{{count}} personne",
      multiple: "{{count}} personnes"
    },
    sections: {
      ingredients: "Ingrédients",
      tools: "Ustensiles",
      preparation: "Préparation"
    },
    actions: {
      print: "Imprimer la recette",
      copy: "Copier la recette",
      copyIngredients: "Copier la liste d'ingrédients",
      reset: "Réinitialiser la recette",
      decreaseServings: "Réduire les portions",
      increaseServings: "Augmenter les portions"
    },
    modes: {
      shoppingList: "Mode liste de courses",
      ingredients: "Mode ingrédients"
    },
    units: {
      // Unités de base
      g: "g",
      kg: "kg",
      ml: "ml",
      l: "l",
      // Unités impériales
      oz: "once",
      "fl oz": "once fluide",
      lb: "livre",
      // Unités de volume
      cup: "tasse",
      cups: "tasses",
      tablespoon: "cuillère à soupe",
      tablespoons: "cuillères à soupe",
      teaspoon: "cuillère à café",
      teaspoons: "cuillères à café",
      glass: "verre",
      glasses: "verres",
      // Unités entières
      unit: "unité",
      units: "unités",
      piece: "pièce",
      pieces: "pièces",
      // Unités de poids
      gram: "gramme",
      grams: "grammes",
      kilogram: "kilogramme",
      kilograms: "kilogrammes"
    }
  },
  common: {
    cancel: "Annuler"
  }
};
