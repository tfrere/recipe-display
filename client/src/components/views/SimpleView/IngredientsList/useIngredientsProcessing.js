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
      // RECIPE MODE - Approche plus simple pour les petites recettes

      // 1. Vérifier le nombre total d'ingrédients
      const totalItems = items.length;

      // Si très peu d'ingrédients, utiliser une approche différente
      const isSmallRecipe = totalItems <= columnCount * 5;

      if (isSmallRecipe) {
        // Pour les petites recettes, utiliser une approche simple basée sur l'index
        const columns = Array(columnCount)
          .fill()
          .map(() => []);
        const subRecipeMap = {};

        // Regrouper les ingrédients par sous-recette
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

        // Distribuer les ingrédients équitablement
        let currentIndex = 0;

        orderedSubRecipes.forEach((subRecipe) => {
          // Calculer le nombre d'ingrédients pour chaque colonne
          const itemsPerColumn = Math.max(
            1,
            Math.floor(subRecipe.items.length / columnCount)
          );

          // Trier les ingrédients par catégorie et nom
          subRecipe.items.sort((a, b) => {
            const catIndexA = categoryOrder.indexOf(a.category || "other");
            const catIndexB = categoryOrder.indexOf(b.category || "other");
            if (catIndexA === catIndexB) {
              return a.name.localeCompare(b.name);
            }
            return catIndexA - catIndexB;
          });

          // Distribution équitable sur toutes les colonnes
          const groups = [];
          for (let i = 0; i < columnCount; i++) {
            const startIndex = i * itemsPerColumn;
            const endIndex =
              i === columnCount - 1
                ? subRecipe.items.length
                : Math.min((i + 1) * itemsPerColumn, subRecipe.items.length);

            if (startIndex < endIndex) {
              groups.push({
                key: `${subRecipe.id}-${i}`,
                title: subRecipe.title,
                items: subRecipe.items.slice(startIndex, endIndex),
                showTitle: i === 0, // Seulement la première colonne montre le titre
              });
            }
          }

          // Redistribuer les groupes pour équilibrer
          groups.forEach((group, index) => {
            columns[index % columnCount].push(group);
          });
        });

        return columns;
      }

      // Pour les recettes plus grandes, utiliser cette approche améliorée
      // Étape 3: Distribution plus agressive des chunks
      // Stratégie complètement différente basée sur une répartition en "lames de scie"
      // Cela garantit un meilleur équilibre, quelle que soit la taille des sous-recettes

      // Nouvelle fonction pour distribuer les ingrédients avec un meilleur équilibrage
      const distributeIngredientsEvenly = (allIngredients, columnCount) => {
        // Si très peu d'ingrédients, utiliser une approche différente
        const isSmallRecipe = allIngredients.length <= columnCount * 5;

        if (isSmallRecipe) {
          // Pour les petites recettes, utiliser une approche simple basée sur l'index
          const columns = Array(columnCount)
            .fill()
            .map(() => []);
          const subRecipeMap = {};

          // Regrouper les ingrédients par sous-recette
          allIngredients.forEach((item) => {
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

          // Redistribuer par simple répartition cyclique
          let currentColIndex = 0;

          orderedSubRecipes.forEach((subRecipe) => {
            // Trier les ingrédients par catégorie et nom
            subRecipe.items.sort((a, b) => {
              const catIndexA = categoryOrder.indexOf(a.category || "other");
              const catIndexB = categoryOrder.indexOf(b.category || "other");
              if (catIndexA === catIndexB) {
                return a.name.localeCompare(b.name);
              }
              return catIndexA - catIndexB;
            });

            // Créer un groupe pour cette sous-recette
            const group = {
              key: subRecipe.id,
              title: subRecipe.title,
              items: subRecipe.items,
              showTitle: true,
            };

            // Ajouter à la colonne courante et passer à la suivante
            columns[currentColIndex].push(group);
            currentColIndex = (currentColIndex + 1) % columnCount;
          });

          return columns;
        }

        // Pour les recettes plus grandes, utiliser une approche plus sophistiquée

        // 1. Analyser toutes les sous-recettes et leurs tailles
        const subRecipesById = {};
        allIngredients.forEach((item) => {
          if (!subRecipesById[item.subRecipeId]) {
            subRecipesById[item.subRecipeId] = {
              id: item.subRecipeId,
              title: item.subRecipeTitle || "Main recipe",
              items: [],
            };
          }
          subRecipesById[item.subRecipeId].items.push(item);
        });

        // 2. Calculer la taille idéale par colonne
        const totalIngredients = allIngredients.length;
        const targetPerColumn = Math.ceil(totalIngredients / columnCount);

        // 3. Trier les sous-recettes par ordre puis par taille
        const orderedSubRecipes = subRecipeOrder
          .filter((id) => subRecipesById[id])
          .map((id) => subRecipesById[id]);

        // 4. Préparer les colonnes
        const columns = Array(columnCount)
          .fill()
          .map(() => []);
        const columnSizes = Array(columnCount).fill(0);

        // 5. Fragmenter les grosses sous-recettes et distribuer équitablement
        orderedSubRecipes.forEach((subRecipe, subRecipeIndex) => {
          // Trier les ingrédients par catégorie et nom
          subRecipe.items.sort((a, b) => {
            const catIndexA = categoryOrder.indexOf(a.category || "other");
            const catIndexB = categoryOrder.indexOf(b.category || "other");
            if (catIndexA === catIndexB) {
              return a.name.localeCompare(b.name);
            }
            return catIndexA - catIndexB;
          });

          // Analyser la taille relative de cette sous-recette
          const isLarge = subRecipe.items.length > targetPerColumn * 0.8;

          // Stratégie pour les grandes sous-recettes: fragmenter en plus petits morceaux
          if (isLarge) {
            // 5a. Fragmenter par catégorie si possible
            const categorizedItems = {};
            subRecipe.items.forEach((item) => {
              const cat = item.category || "other";
              if (!categorizedItems[cat]) categorizedItems[cat] = [];
              categorizedItems[cat].push(item);
            });

            // 5b. Regrouper en chunks de taille optimale
            const chunks = [];
            const optimalChunkSize = Math.max(
              3,
              Math.min(5, Math.floor(targetPerColumn * 0.5))
            );
            let currentChunk = [];
            let currentCategory = null;

            // Parcourir les catégories dans l'ordre
            categoryOrder.forEach((category) => {
              if (!categorizedItems[category]) return;

              const categoryItems = categorizedItems[category];

              // Si nouvelle catégorie et le chunk précédent n'est pas vide
              if (currentCategory !== category && currentChunk.length > 0) {
                chunks.push([...currentChunk]);
                currentChunk = [];
              }

              // Ajouter les items de cette catégorie
              categoryItems.forEach((item) => {
                currentChunk.push(item);

                // Si le chunk atteint la taille optimale, le finaliser
                if (currentChunk.length >= optimalChunkSize) {
                  chunks.push([...currentChunk]);
                  currentChunk = [];
                }
              });

              currentCategory = category;
            });

            // Ajouter le dernier chunk s'il n'est pas vide
            if (currentChunk.length > 0) {
              chunks.push(currentChunk);
            }

            // 5c. Distribuer les chunks en zigzag pour équilibrer au mieux
            let chunksAdded = 0;
            chunks.forEach((itemsChunk, chunkIndex) => {
              // Toujours choisir la colonne la moins remplie
              const targetColumn = columnSizes.indexOf(
                Math.min(...columnSizes)
              );

              // Créer un groupe pour ce chunk
              const group = {
                key: `${subRecipe.id}-${chunkIndex}`,
                title: subRecipe.title,
                items: itemsChunk,
                showTitle: chunksAdded === 0, // Seul le premier chunk montre le titre
              };

              // Ajouter à la colonne la moins remplie
              columns[targetColumn].push(group);
              columnSizes[targetColumn] += itemsChunk.length;
              chunksAdded++;
            });
          }
          // Stratégie pour les petites sous-recettes: garder entières et placer intelligemment
          else {
            // Trouver la colonne la moins remplie
            const targetColumn = columnSizes.indexOf(Math.min(...columnSizes));

            // Créer un groupe pour cette sous-recette
            const group = {
              key: subRecipe.id,
              title: subRecipe.title,
              items: subRecipe.items,
              showTitle: true,
            };

            // Ajouter à la colonne la moins remplie
            columns[targetColumn].push(group);
            columnSizes[targetColumn] += subRecipe.items.length;
          }
        });

        // 6. Vérification finale de l'équilibre
        const maxColumnSize = Math.max(...columnSizes);
        const minColumnSize = Math.min(...columnSizes);
        const difference = maxColumnSize - minColumnSize;

        // Si le déséquilibre est trop important, redistribuer
        if (difference > targetPerColumn * 0.3) {
          // Extraire tous les groupes, les trier par taille, et redistribuer
          const allGroups = [];
          columns.forEach((col) => {
            col.forEach((group) => {
              allGroups.push(group);
            });
            col.length = 0; // Vider la colonne
          });

          // Trier par originalIndex (pour préserver l'ordre par sous-recette) puis par taille décroissante
          allGroups.sort((a, b) => {
            // Préserver l'ordre des sous-recettes
            const aId = a.key.split("-")[0];
            const bId = b.key.split("-")[0];
            const aIndex = subRecipeOrder.indexOf(aId);
            const bIndex = subRecipeOrder.indexOf(bId);

            if (aIndex !== bIndex) return aIndex - bIndex;

            // Sinon trier par taille décroissante
            return b.items.length - a.items.length;
          });

          // Réinitialiser les tailles de colonne
          columnSizes.fill(0);

          // Redistribuer en utilisant un algorithme glouton
          allGroups.forEach((group) => {
            // Toujours choisir la colonne la moins remplie
            const targetColumn = columnSizes.indexOf(Math.min(...columnSizes));
            columns[targetColumn].push(group);
            columnSizes[targetColumn] += group.items.length;
          });
        }

        return columns;
      };

      // Remplacer la distribution originale par notre nouvelle approche
      const columns = distributeIngredientsEvenly(
        sortedIngredients,
        columnCount
      );

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
