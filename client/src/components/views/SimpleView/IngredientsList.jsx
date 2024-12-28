import React, { useMemo } from 'react';
import { Box, Typography, Button, Switch, FormControlLabel, IconButton, Tooltip } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ContentCopyOutlinedIcon from '@mui/icons-material/ContentCopyOutlined';
import { useRecipe } from '../../../contexts/RecipeContext';
import { GRAM_UNITS } from '../../../utils/ingredientScaling';
import { useTranslation } from 'react-i18next';

const IngredientsList = ({ recipe, sortByCategory, setSortByCategory }) => {
  const { t } = useTranslation();
  const { getAdjustedAmount, formatAmount, isIngredientUnused, completedSteps } = useRecipe();

  // Call all hooks at the top level
  const subRecipeOrder = useMemo(() => {
    return Object.entries(recipe.subRecipes || {}).map(([id]) => id);
  }, [recipe.subRecipes]);

  const allIngredients = useMemo(() => {
    if (!recipe.subRecipes || !recipe.ingredients) return [];
    
    return Object.entries(recipe.subRecipes).reduce((acc, [subRecipeId, subRecipe]) => {
      if (!subRecipe.ingredients) return acc;
      
      Object.entries(subRecipe.ingredients).forEach(([ingredientId, data]) => {
        const ingredient = recipe.ingredients[ingredientId];
        if (!ingredient) return;

        const adjustedAmount = getAdjustedAmount(data.amount, ingredient.unit, ingredient.category);
        acc.push({
          id: ingredientId,
          name: ingredient.name,
          amount: adjustedAmount,
          unit: ingredient.unit,
          subRecipeId,
          subRecipeTitle: subRecipe.title,
          category: ingredient.category || 'autres',
        });
      });
      return acc;
    }, []);
  }, [recipe.subRecipes, recipe.ingredients, getAdjustedAmount]);

  const formattedIngredients = useMemo(() => {
    return allIngredients.map(ingredient => ({
      ...ingredient,
      displayAmount: formatAmount(ingredient.amount, ingredient.unit)
    }));
  }, [allIngredients, formatAmount]);

  const categoryOrder = useMemo(() => [
    'base',
    'farine',
    'sucre',
    'œuf',
    'produit-laitier',
    'chocolat',
    'fruit-sec',
    'épices',
    'autres'
  ], []);

  const sortedIngredients = useMemo(() => {
    if (!formattedIngredients.length) return [];

    if (sortByCategory) {
      // Agrégation des ingrédients par nom et unité
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

      const groupedByCategory = Object.values(aggregatedIngredients).reduce((acc, ingredient) => {
        const category = ingredient.category || 'autres';
        if (!acc[category]) {
          acc[category] = [];
        }
        acc[category].push(ingredient);
        return acc;
      }, {});

      // Sort ingredients within each category
      Object.values(groupedByCategory).forEach(ingredients => {
        ingredients.sort((a, b) => a.name.localeCompare(b.name));
      });

      return Object.entries(groupedByCategory)
        .sort(([catA], [catB]) => {
          const indexA = categoryOrder.indexOf(catA);
          const indexB = categoryOrder.indexOf(catB);
          if (indexA === -1 && indexB === -1) return catA.localeCompare(catB);
          if (indexA === -1) return 1;
          if (indexB === -1) return -1;
          return indexA - indexB;
        })
        .flatMap(([_, ingredients]) => ingredients);
    }

    // Sort by subRecipe order
    return formattedIngredients.sort((a, b) => {
      const indexA = subRecipeOrder.indexOf(a.subRecipeId);
      const indexB = subRecipeOrder.indexOf(b.subRecipeId);
      if (indexA === indexB) {
        return a.name.localeCompare(b.name);
      }
      return indexA - indexB;
    });
  }, [formattedIngredients, sortByCategory, subRecipeOrder, categoryOrder, formatAmount]);

  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingIngredients = allIngredients.filter(ing => !isIngredientUnused(ing.name)).length;

  const distributeInColumns = (items, columnCount) => {
    const itemsPerColumn = Math.ceil(items.length / columnCount);
    return Array(columnCount)
      .fill()
      .map((_, index) => items.slice(index * itemsPerColumn, (index + 1) * itemsPerColumn));
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

  // Set pour suivre les catégories déjà affichées
  const displayedCategories = new Set();

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
              {sortByCategory ? t('recipe.modes.shoppingList') : t('recipe.modes.ingredients')}
            </Typography>
          }
          sx={{
            ml: 1,
            mr: 0
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
        {columns.map((column, columnIndex) => (
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
            {column.map((ingredient, index) => {
              const categoryKey = sortByCategory ? ingredient.category : ingredient.subRecipeId;
              const showHeader = !displayedCategories.has(categoryKey);
              if (showHeader) {
                displayedCategories.add(categoryKey);
              }

              // Vérifie si c'est le dernier élément de sa catégorie dans la colonne
              const isLastInCategory = index === column.length - 1 || 
                (sortByCategory ? 
                  column[index + 1]?.category !== ingredient.category :
                  column[index + 1]?.subRecipeId !== ingredient.subRecipeId);

              return (
                <Box 
                  key={`${ingredient.subRecipeId}-${ingredient.name}`}
                  sx={{
                    mb: isLastInCategory ? 4 : 0
                  }}
                >
                  {showHeader && (sortByCategory || Object.keys(recipe.subRecipes).length > 1) && (
                    <Typography 
                      variant="body1" 
                      sx={{ 
                        gridColumn: '1/-1',
                        color: 'text.primary',
                        mb: 1.5,
                        fontStyle: 'italic',
                        textTransform: 'capitalize',
                        fontWeight: 600
                      }}
                    >
                      {sortByCategory ? ingredient.category.replace(/-/g, ' ') : ingredient.subRecipeTitle}
                    </Typography>
                  )}
                  <Box sx={{ 
                    display: 'grid',
                    gridTemplateColumns: '0.4fr 0.6fr',
                    gap: 2,
                    alignItems: 'center',
                    py: 0.25,
                    opacity: isIngredientUnused(ingredient.name) ? 0.5 : 1,
                    textDecoration: isIngredientUnused(ingredient.name) ? 'line-through' : 'none'
                  }}>
                    <Typography 
                      variant="body1"
                      sx={{ 
                        color: 'text.secondary',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {ingredient.displayAmount}
                    </Typography>
                    <Typography
                      variant="body1"
                    >
                      {ingredient.name}
                    </Typography>
                  </Box>
                </Box>
              );
            })}
          </Box>
        ))}
      </Box>
    </>
  );
};

export default IngredientsList;
