import { useMemo } from "react";
import { useRecipe } from "../../../../contexts/RecipeContext";
import { useConstants } from "../../../../contexts/ConstantsContext";

/**
 * Custom hook for processing ingredients data
 */
export const useIngredientsProcessing = (recipe, sortByCategory) => {
  const { constants } = useConstants();
  const {
    getAdjustedAmount,
    formatAmount,
    isIngredientUnused,
    completedSteps,
  } = useRecipe();

  // Wait for constants to be loaded
  if (!constants) {
    return {
      columns: [],
      allIngredients: [],
      hasCompletedSteps: false,
      remainingIngredients: 0,
    };
  }

  // Extract constants needed for ingredient processing
  const CATEGORY_ORDER = constants.ingredients.categories.map((cat) => cat.id);
  const CATEGORY_LABELS = Object.fromEntries(
    constants.ingredients.categories.map((cat) => [cat.id, cat.label])
  );

  // 1. Get sub-recipe order as defined in the recipe
  const subRecipeOrder = useMemo(() => {
    return recipe.subRecipes.map((subRecipe) => subRecipe.id);
  }, [recipe.subRecipes]);

  // 2. Get category order for sorting
  const categoryOrder = useMemo(() => CATEGORY_ORDER, []);

  // 3. Build complete ingredients list with all properties
  const allIngredients = useMemo(() => {
    if (!recipe.subRecipes || !recipe.ingredients) return [];

    return recipe.subRecipes.reduce((acc, subRecipe) => {
      if (!subRecipe.ingredients) return acc;

      subRecipe.ingredients.forEach((data) => {
        const ingredient = recipe.ingredients.find(
          (ing) => ing.id === data.ref
        );
        if (!ingredient) return;

        // Priority to the unit specified in the sub-recipe ingredient
        const unit = data.unit || ingredient.unit;

        acc.push({
          id: data.ref,
          name: ingredient.name,
          amount: getAdjustedAmount(data.amount, unit, ingredient.category),
          unit: unit,
          state: data.state,
          subRecipeId: subRecipe.id,
          subRecipeTitle: subRecipe.title,
          category: ingredient.category || "other",
          initialState: data.initialState,
        });
      });
      return acc;
    }, []);
  }, [recipe.subRecipes, recipe.ingredients, getAdjustedAmount]);

  // 4. Format ingredients (quantities, states, etc.)
  const formattedIngredients = useMemo(() => {
    return allIngredients.map((ingredient) => {
      // Format amount with appropriate unit
      const displayAmount = formatAmount(ingredient.amount, ingredient.unit);

      return {
        ...ingredient,
        displayAmount,
        isUnused: isIngredientUnused(ingredient.id, ingredient.subRecipeId),
        displayState: ingredient.state,
        initialState: ingredient.initialState,
      };
    });
  }, [allIngredients, formatAmount, isIngredientUnused]);

  // 5. Sort ingredients based on mode (shopping list or sub-recipes)
  const sortedIngredients = useMemo(() => {
    if (!formattedIngredients.length) return [];

    if (sortByCategory) {
      // SHOPPING LIST MODE

      // 5.a. Aggregate identical ingredients
      const aggregatedIngredients = formattedIngredients.reduce(
        (acc, ingredient) => {
          const key = `${ingredient.name}|${ingredient.unit || ""}|${
            ingredient.category
          }`;
          if (!acc[key]) {
            acc[key] = { ...ingredient };
          } else {
            acc[key].amount += ingredient.amount;
            acc[key].displayAmount = formatAmount(
              acc[key].amount,
              acc[key].unit
            );
          }
          return acc;
        },
        {}
      );

      // 5.b. Group by category
      const groupedByCategory = Object.values(aggregatedIngredients).reduce(
        (acc, ingredient) => {
          const category = ingredient.category || "other";
          if (!acc[category]) acc[category] = [];
          acc[category].push(ingredient);
          return acc;
        },
        {}
      );

      // 5.c. Sort ingredients within each category by name
      Object.values(groupedByCategory).forEach((ingredients) => {
        ingredients.sort((a, b) => a.name.localeCompare(b.name));
      });

      // 5.d. Sort categories and flatten the list
      return Object.entries(groupedByCategory)
        .sort(([catA], [catB]) => {
          const indexA = categoryOrder.indexOf(catA || "other");
          const indexB = categoryOrder.indexOf(catB || "other");
          return indexA - indexB;
        })
        .flatMap(([_, ingredients]) => ingredients);
    }

    // RECIPE MODE: group by sub-recipe
    const groupedBySubRecipe = formattedIngredients.reduce(
      (acc, ingredient) => {
        const subRecipeId = ingredient.subRecipeId;
        if (!acc[subRecipeId]) acc[subRecipeId] = [];
        acc[subRecipeId].push(ingredient);
        return acc;
      },
      {}
    );

    // Sort sub-recipes according to defined order
    return subRecipeOrder
      .filter((id) => groupedBySubRecipe[id])
      .flatMap((id) => groupedBySubRecipe[id]);
  }, [
    formattedIngredients,
    sortByCategory,
    subRecipeOrder,
    categoryOrder,
    formatAmount,
  ]);

  // 6. Distribute ingredients into columns for display
  const distributeInColumns = (items, columnCount) => {
    if (sortByCategory) {
      // SHOPPING LIST MODE - Original implementation (by category)
      // 6.a. Group by category
      const groups = items.reduce((acc, item) => {
        const key = item.category;
        if (!acc[key]) {
          acc[key] = {
            key: key,
            title: CATEGORY_LABELS[key] || key.replace(/-/g, " "),
            items: [],
          };
        }
        acc[key].items.push(item);
        return acc;
      }, {});

      // 6.b. Distribute groups to balance columns
      const groupsList = Object.values(groups).sort(
        (a, b) => b.items.length - a.items.length
      );
      const columns = Array(columnCount)
        .fill()
        .map(() => ({
          groups: [],
          totalItems: 0,
        }));

      groupsList.forEach((group) => {
        const targetColumn = columns.reduce(
          (min, col, index) =>
            col.totalItems < columns[min].totalItems ? index : min,
          0
        );
        columns[targetColumn].groups.push(group);
        columns[targetColumn].totalItems += group.items.length;
      });

      return columns.map((col) => col.groups);
    } else {
      // RECIPE MODE - Nouvelle approche pour répartir les ingrédients avec conservation des sous-recettes

      // 1. Créer un tableau pour chaque colonne
      const columns = Array(columnCount)
        .fill()
        .map(() => []);

      // 2. Calculer le nombre idéal d'ingrédients par colonne
      const totalIngredients = items.length;
      const itemsPerColumn = Math.ceil(totalIngredients / columnCount);

      // 3. Trier les ingrédients par sous-recette (en conservant l'ordre original)
      const subRecipeMap = {};

      // Grouper les ingrédients par sous-recette
      items.forEach((item) => {
        if (!subRecipeMap[item.subRecipeId]) {
          subRecipeMap[item.subRecipeId] = {
            id: item.subRecipeId,
            title: item.subRecipeTitle,
            items: [],
          };
        }
        subRecipeMap[item.subRecipeId].items.push(item);
      });

      // Trier les sous-recettes selon l'ordre original
      const orderedSubRecipes = subRecipeOrder
        .filter((id) => subRecipeMap[id])
        .map((id) => subRecipeMap[id]);

      // 4. Distribuer les ingrédients dans les colonnes
      let currentColumn = 0;
      let currentItemCount = 0;
      let currentSubRecipeIndex = 0;
      let currentIngredientIndex = 0;

      // Garder une trace des sous-recettes déjà affichées
      const displayedSubRecipes = new Set();

      // Déterminer si on doit afficher les titres des sous-recettes (seulement s'il y a plus d'une sous-recette)
      const shouldDisplaySubRecipeTitles = orderedSubRecipes.length > 1;

      // Parcourir toutes les sous-recettes
      while (currentSubRecipeIndex < orderedSubRecipes.length) {
        const subRecipe = orderedSubRecipes[currentSubRecipeIndex];

        // Si on a parcouru tous les ingrédients de cette sous-recette, passer à la suivante
        if (currentIngredientIndex >= subRecipe.items.length) {
          currentSubRecipeIndex++;
          currentIngredientIndex = 0;
          continue;
        }

        // Si on a atteint la limite d'ingrédients pour cette colonne et qu'il y a encore des ingrédients
        if (
          currentItemCount >= itemsPerColumn &&
          currentColumn < columnCount - 1
        ) {
          currentColumn++;
          currentItemCount = 0;
        }

        // Déterminer si on doit créer un nouveau groupe
        let shouldCreateNewGroup = true;

        // Vérifier si le dernier groupe appartient à la même sous-recette
        if (columns[currentColumn].length > 0) {
          const lastGroup =
            columns[currentColumn][columns[currentColumn].length - 1];
          if (lastGroup.key.startsWith(subRecipe.id)) {
            shouldCreateNewGroup = false;
          }
        }

        // Déterminer si on doit afficher le titre (uniquement pour la première apparition et s'il y a plusieurs sous-recettes)
        const shouldShowTitle =
          shouldDisplaySubRecipeTitles &&
          !displayedSubRecipes.has(subRecipe.id);

        // Marquer cette sous-recette comme ayant été affichée
        if (shouldShowTitle) {
          displayedSubRecipes.add(subRecipe.id);
        }

        // Créer un nouveau groupe ou utiliser le dernier groupe de cette sous-recette
        let group;

        if (shouldCreateNewGroup) {
          group = {
            key: `${subRecipe.id}-${currentColumn}`,
            title: subRecipe.title,
            items: [],
            showTitle: shouldShowTitle,
          };
          columns[currentColumn].push(group);
        } else {
          // Récupérer le dernier groupe de cette sous-recette
          group = columns[currentColumn][columns[currentColumn].length - 1];
        }

        // Ajouter l'ingrédient courant au groupe
        group.items.push(subRecipe.items[currentIngredientIndex]);

        // Passer à l'ingrédient suivant
        currentIngredientIndex++;
        currentItemCount++;
      }

      return columns;
    }
  };

  // Distribute ingredients into 3 columns for display
  const columns = distributeInColumns(sortedIngredients, 3);

  // Statistics for display
  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingIngredients = allIngredients.filter(
    (ing) => !ing.isUnused
  ).length;

  return {
    columns,
    allIngredients,
    sortedIngredients,
    hasCompletedSteps,
    remainingIngredients,
    CATEGORY_LABELS,
  };
};
