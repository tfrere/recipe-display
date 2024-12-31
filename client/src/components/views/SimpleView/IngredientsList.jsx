import React, { useMemo } from 'react';
import { Box, Typography, Button, Switch, FormControlLabel, IconButton, Tooltip } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ContentCopyOutlinedIcon from '@mui/icons-material/ContentCopyOutlined';
import { useRecipe } from '../../../contexts/RecipeContext';
import { GRAM_UNITS } from '../../../utils/ingredientScaling';
import { useTranslation } from 'react-i18next';
import { CATEGORY_ORDER, CATEGORY_LABELS } from '@shared/constants/ingredients';

const IngredientsList = ({ recipe, sortByCategory, setSortByCategory }) => {
  const { t } = useTranslation();
  const { getAdjustedAmount, formatAmount, isIngredientUnused, completedSteps } = useRecipe();

  // 1. Ordre des sous-recettes tel que défini dans la recette
  const subRecipeOrder = useMemo(() => {
    return Object.entries(recipe.subRecipes || {}).map(([id]) => id);
  }, [recipe.subRecipes]);

  // 2. Ordre des catégories pour le tri
  const categoryOrder = useMemo(() => CATEGORY_ORDER, []);

  // 3. Construction de la liste complète des ingrédients avec leurs propriétés
  const allIngredients = useMemo(() => {
    if (!recipe.subRecipes || !recipe.ingredients) return [];
    
    return Object.entries(recipe.subRecipes).reduce((acc, [subRecipeId, subRecipe]) => {
      if (!subRecipe.ingredients) return acc;
      
      Object.entries(subRecipe.ingredients).forEach(([ingredientId, data]) => {
        const ingredient = recipe.ingredients[ingredientId];
        if (!ingredient) return;

        // Log pour voir la catégorie de chaque ingrédient
        console.log(`Ingrédient ${ingredient.name}: catégorie = ${ingredient.category}`);

        acc.push({
          id: ingredientId,
          name: ingredient.name,
          amount: getAdjustedAmount(data.amount, ingredient.unit, ingredient.category),
          unit: ingredient.unit,
          state: data.state,
          subRecipeId,
          subRecipeTitle: subRecipe.title,
          category: ingredient.category || 'autres',
        });
      });
      return acc;
    }, []);
  }, [recipe.subRecipes, recipe.ingredients, getAdjustedAmount]);

  // 4. Formatage des ingrédients (quantités, états, etc.)
  const formattedIngredients = useMemo(() => {
    return allIngredients.map(ingredient => ({
      ...ingredient,
      displayAmount: formatAmount(ingredient.amount, ingredient.unit),
      isUnused: isIngredientUnused(ingredient.id, ingredient.subRecipeId),
      displayState: ingredient.state
    }));
  }, [allIngredients, formatAmount, isIngredientUnused]);

  // 5. Tri des ingrédients selon le mode (shopping list ou sous-recettes)
  const sortedIngredients = useMemo(() => {
    if (!formattedIngredients.length) return [];

    if (sortByCategory) {
      // Mode shopping list : grouper par catégorie
      // 5.a. Agréger les ingrédients identiques
      const aggregatedIngredients = formattedIngredients.reduce((acc, ingredient) => {
        const key = `${ingredient.name}|${ingredient.unit || ''}|${ingredient.category}`;
        if (!acc[key]) {
          acc[key] = { ...ingredient };
        } else {
          acc[key].amount += ingredient.amount;
          acc[key].displayAmount = formatAmount(acc[key].amount, acc[key].unit);
        }
        return acc;
      }, {});

      // 5.b. Grouper par catégorie
      const groupedByCategory = Object.values(aggregatedIngredients).reduce((acc, ingredient) => {
        const category = ingredient.category || 'autres';
        if (!acc[category]) acc[category] = [];
        acc[category].push(ingredient);
        return acc;
      }, {});

      // 5.c. Trier les ingrédients dans chaque catégorie
      Object.values(groupedByCategory).forEach(ingredients => {
        ingredients.sort((a, b) => a.name.localeCompare(b.name));
      });

      // 5.d. Trier les catégories et aplatir la liste
      return Object.entries(groupedByCategory)
        .sort(([catA], [catB]) => {
          const indexA = categoryOrder.indexOf(catA || 'autres');
          const indexB = categoryOrder.indexOf(catB || 'autres');
          return indexA - indexB;
        })
        .flatMap(([_, ingredients]) => ingredients);
    }

    // Mode sous-recettes : grouper par sous-recette
    const groupedBySubRecipe = formattedIngredients.reduce((acc, ingredient) => {
      const subRecipeId = ingredient.subRecipeId;
      if (!acc[subRecipeId]) acc[subRecipeId] = [];
      acc[subRecipeId].push(ingredient);
      return acc;
    }, {});

    // Trier les sous-recettes selon l'ordre défini
    return subRecipeOrder
      .filter(id => groupedBySubRecipe[id])
      .flatMap(id => groupedBySubRecipe[id]);

  }, [formattedIngredients, sortByCategory, subRecipeOrder, categoryOrder, formatAmount]);

  // 6. Distribution des ingrédients en colonnes pour l'affichage
  const distributeInColumns = (items, columnCount) => {
    // 6.a. Grouper par sous-recette ou catégorie selon le mode
    const groups = items.reduce((acc, item) => {
      const key = sortByCategory ? item.category : item.subRecipeId;
      if (!acc[key]) {
        acc[key] = {
          key: key,
          title: sortByCategory ? key.replace(/-/g, ' ') : recipe.subRecipes[key].title,
          items: []
        };
      }
      acc[key].items.push(item);
      return acc;
    }, {});

    // 6.b. En mode sous-recette, trier les ingrédients de chaque groupe par catégorie
    if (!sortByCategory) {
      Object.values(groups).forEach(group => {
        console.log('Avant tri - Ingrédients du groupe:', group.title, group.items.map(i => ({ name: i.name, category: i.category })));
        // Trier les ingrédients par catégorie puis par nom
        const sortedItems = group.items.sort((a, b) => {
          const catIndexA = categoryOrder.indexOf(a.category || 'autres');
          const catIndexB = categoryOrder.indexOf(b.category || 'autres');
          console.log(`Comparaison: ${a.name}(${a.category}, ${catIndexA}) vs ${b.name}(${b.category}, ${catIndexB})`);
          if (catIndexA === catIndexB) {
            return a.name.localeCompare(b.name);
          }
          return catIndexA - catIndexB;
        });
        group.items = sortedItems;
        console.log('Après tri - Ingrédients du groupe:', group.title, group.items.map(i => ({ name: i.name, category: i.category })));
      });
    }

    // 6.c. Répartir les groupes en colonnes équilibrées
    const groupsList = Object.values(groups).sort((a, b) => b.items.length - a.items.length);
    const columns = Array(columnCount).fill().map(() => ({
      groups: [],
      totalItems: 0
    }));

    groupsList.forEach(group => {
      const targetColumn = columns.reduce((min, col, index) => 
        col.totalItems < columns[min].totalItems ? index : min
      , 0);
      columns[targetColumn].groups.push(group);
      columns[targetColumn].totalItems += group.items.length;
    });

    return columns.map(col => col.groups);
  };

  const columns = distributeInColumns(sortedIngredients, 3);

  const handleCopyIngredients = () => {
    // Utilise les ingrédients déjà triés et agrégés
    const ingredientsList = sortedIngredients
      .map(ingredient => {
        const amount = ingredient.displayAmount;
        const unit = ingredient.unit ? ` ${ingredient.unit}` : '';
        return `${amount}${unit} ${ingredient.name}`;
      })
      .join('\n');
    
    navigator.clipboard.writeText(ingredientsList);
  };

  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingIngredients = allIngredients.filter(ing => !ing.isUnused).length;

  return (
    <>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center',
        mb: 3,
        gap: 1.5
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
          <Typography variant="h5" component="span">
            {t('recipe.sections.ingredients')}
          </Typography>
          <Typography 
            variant="body2" 
            sx={{ 
              color: 'text.disabled',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5
            }}
          >
            • {hasCompletedSteps ? `${remainingIngredients}/` : ''}{allIngredients.length}
          </Typography>
        </Box>
        {sortByCategory && (
          <Tooltip title={t('recipe.actions.copyIngredients')}>
            <IconButton
              onClick={handleCopyIngredients}
              size="small"
              color="default"
              aria-label={t('recipe.actions.copyIngredients')}
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                '&:hover': {
                  borderColor: 'action.hover'
                }
              }}
            >
              <ContentCopyOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={sortByCategory}
              onChange={(e) => setSortByCategory(e.target.checked)}
              sx={{
                '& .MuiSwitch-track': {
                  bgcolor: 'background.paper',
                  border: '1px solid',
                  borderColor: 'divider',
                  opacity: 1
                },
                '& .MuiSwitch-thumb': {
                  bgcolor: 'background.paper',
                  border: '1px solid',
                  borderColor: 'text.secondary'
                },
                '& .Mui-checked': {
                  '& .MuiSwitch-thumb': {
                    bgcolor: 'background.paper'
                  },
                  '& + .MuiSwitch-track': {
                    bgcolor: 'background.paper',
                    opacity: 1
                  }
                }
              }}
            />
          }
          label={
            <Typography 
              variant="body2" 
              color="text.secondary"
            >
              {t('recipe.modes.shoppingList')}
            </Typography>
          }
          labelPlacement="start"
          sx={{
            ml: 1,
            mr: 0,
            gap: 1
          }}
        />
      </Box>

      <Box 
        sx={{ 
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: '1fr 1fr',
            md: '1fr 1fr 1fr'
          },
          gap: 3
        }}
      >
        {columns.map((columnGroups, columnIndex) => (
          <Box 
            key={columnIndex} 
            sx={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: 0.5,
              borderRight: columnIndex < columns.length - 1 ? '1px solid' : 'none',
              borderColor: 'divider',
              pr: 3,
              '@media (max-width: 600px)': {
                borderRight: 'none',
                pr: 0
              }
            }}
          >
            {columnGroups.map((group) => (
              <Box key={group.key} sx={{ mb: 4 }}>
                {(sortByCategory || Object.keys(recipe.subRecipes).length > 1) && (
                  <Typography 
                    variant="body1" 
                    sx={{ 
                      color: 'text.primary',
                      mb: 1.5,
                      fontStyle: 'italic',
                      textTransform: 'capitalize',
                      fontWeight: 600
                    }}
                  >
                    {group.title}
                  </Typography>
                )}
                {group.items.map((ingredient) => {
                  return (
                  <Box 
                    key={`${ingredient.subRecipeId}-${ingredient.name}`}
                    sx={{ 
                      display: 'grid',
                      gridTemplateColumns: '0.3fr 0.7fr',
                      gap: 2,
                      alignItems: 'start',
                      py: 0.25,
                      mb: 0.75,  
                      opacity: ingredient.isUnused ? 0.5 : 1,
                      textDecoration: ingredient.isUnused ? 'line-through' : 'none'
                    }}
                  >
                    <Typography 
                      variant="body1" 
                      sx={{ 
                        color: 'text.secondary',
                        textAlign: 'left'
                      }}
                    >
                      {ingredient.displayAmount}
                    </Typography>
                    <Box>
                      <Typography 
                        variant="body1" 
                        component="span"
                      >
                        {ingredient.name}{ingredient.displayState && `,`}
                      </Typography>
                      {ingredient.displayState && (
                        <Typography 
                          variant="body1" 
                          component="div" 
                          sx={{ 
                            color: 'text.secondary',
                            fontSize: '0.95em',
                            mt: -0.5,
                            ml: 0
                          }}
                        >
                          {ingredient.displayState}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  );
                })}
              </Box>
            ))}
          </Box>
        ))}
      </Box>
    </>
  );
};

export default IngredientsList;
