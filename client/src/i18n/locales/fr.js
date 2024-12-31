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
  search: {
    placeholder: 'Rechercher une recette...',
    byIngredients: "Rechercher par ingrédients...",
    noResults: 'Aucune recette trouvée',
    results_one: '1 recette trouvée',
    results_other: '{{count}} recettes trouvées',
    reset_filters: 'Réinitialiser les filtres',
  },
  filters: {
    diet: "Régime alimentaire",
    difficulty: "Difficulté",
    season: "Saison",
    quick: "Temps de préparation",
    quickRecipes: "Recettes rapides",
    other: "Autres filtres",
    filterBy: 'Filtrer par'
  },
  results: {
    randomSeasonal: "Recettes aléatoires de {{season}}",
    filtered: "Résultats filtrés"
  },
  diet: {
    vegan: "Végan",
    vegetarian: "Végétarien",
    normal: "Classique",
    pescatarian: "Pescétarien"
  },
  difficulty: {
    easy: "Facile",
    medium: "Moyen",
    hard: "Difficile"
  },
  season: {
    spring: "Printemps",
    summer: "Été",
    autumn: "Automne",
    winter: "Hiver",
    all: "Toute saison"
  },
  recipeType: {
    main: "Plat principal",
    side: "Accompagnement",
    dessert: "Dessert",
    appetizer: "Entrée",
    breakfast: "Petit-déjeuner",
    snack: "En-cas",
    drink: "Boisson"
  },
  common: {
    cancel: "Annuler",
    loading: "Chargement...",
    error: "Une erreur est survenue"
  },
  home: {
    title: "Mes Recettes",
    search: "Rechercher une recette...",
    no_recipes: 'Aucune recette trouvée',
    no_recipes_description: 'Essayez de modifier vos filtres ou votre recherche pour trouver des recettes.',
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
    sourceLabel: "URL de la recette",
    sourcePlaceholder: "https://example.com/recipe",
    sourceHelper: "Collez l'URL d'une recette que vous souhaitez ajouter",
    submit: "Ajouter",
    success: "Recette ajoutée avec succès !",
    error: {
      generation: "Erreur lors de la génération de la recette",
      noResponse: "Pas de réponse du serveur. Vérifiez votre connexion.",
      request: "Erreur de configuration de la requête"
    },
    steps: {
      fetchingUrl: "Récupération de la page web...",
      analyzingContent: "Analyse du contenu...",
      extractingRecipe: "Extraction de la recette...",
      translating: "Traduction en français...",
      processingImages: "Traitement des images...",
      savingRecipe: "Enregistrement de la recette..."
    }
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
      ingredients: "Liste de courses",
      shoppingList: "Liste de courses"
    },
    diet: {
      normal: "Normal",
      vegetarian: "Végétarien",
      vegan: "Vegan"
    },
    season: {
      spring: "Printemps",
      summer: "Été",
      autumn: "Automne",
      winter: "Hiver"
    },
    dishType: {
      appetizer: "Entrée",
      starter: "Entrée",
      main: "Plat principal",
      side: "Accompagnement",
      dessert: "Dessert",
      snack: "En-cas",
      breakfast: "Petit-déjeuner",
      drink: "Boisson"
    },
    quick: "Recettes rapides",
    type: {
      appetizer: "Apéritif",
      starter: "Entrée",
      main: "Plat",
      dessert: "Dessert"
    },
    categories: {
      produce: "Fruits et Légumes",
      dairy: "Crèmerie",
      meat: "Boucherie",
      fish: "Poissonnerie",
      frozen: "Surgelés",
      "pantry-savory": "Épicerie Salée",
      "pantry-sweet": "Épicerie Sucrée",
      condiments: "Condiments",
      beverages: "Boissons"
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
    },
    difficulty: {
      easy: 'Facile',
      medium: 'Moyen',
      hard: 'Difficile'
    },
    notes: 'Notes de l\'auteur'
  }
};
