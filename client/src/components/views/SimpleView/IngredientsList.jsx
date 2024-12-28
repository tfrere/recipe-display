import React from 'react';
import { Box, Typography, Button, Switch, FormControlLabel, IconButton } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useRecipe } from '../../../contexts/RecipeContext';
import { GRAM_UNITS } from '../../../utils/ingredientScaling';

const IngredientsList = ({ recipe, sortByCategory, setSortByCategory }) => {
  const { getAdjustedAmount, formatAmount, isIngredientUnused, completedSteps } = useRecipe();
  
  const subRecipeOrder = Object.entries(recipe.subRecipes || {}).map(([id]) => id);
  const allIngredients = Object.entries(recipe.subRecipes || {}).reduce((acc, [subRecipeId, subRecipe]) => {
    Object.entries(subRecipe.ingredients || {}).forEach(([ingredientId, data]) => {
      const ingredient = recipe.ingredients[ingredientId];
      const adjustedAmount = getAdjustedAmount(data.amount, ingredient.unit, ingredient.category);
      acc.push({
        id: ingredientId,
        name: ingredient.name,
        amount: adjustedAmount,
        unit: ingredient.unit,
        subRecipeId,
        subRecipeTitle: subRecipe.title,
        category: ingredient.category || 'autres',
        displayAmount: formatAmount(adjustedAmount, ingredient.unit)
      });
    });
    return acc;
  }, []);

  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingIngredients = allIngredients.filter(ing => !isIngredientUnused(ing.name)).length;

  let sortedIngredients;
  if (sortByCategory) {
    const categoryOrder = [
      'base',
      'farine',
      'sucre',
      'œuf',
      'produit-laitier',
      'chocolat',
      'fruit-sec',
      'épices',
      'autres'
    ];

    // Agrégation des ingrédients par nom et unité
    const aggregatedIngredients = allIngredients.reduce((acc, ingredient) => {
      // Crée une clé unique pour chaque combinaison nom+unité
      const key = `${ingredient.name}|${ingredient.unit || ''}|${ingredient.category}`;
      if (!acc[key]) {
        acc[key] = {
          ...ingredient,
          amount: 0,
        };
      }
      acc[key].amount += ingredient.amount;
      // Recalcule le displayAmount avec la nouvelle quantité totale
      acc[key].displayAmount = formatAmount(acc[key].amount, ingredient.unit);
      return acc;
    }, {});

    const groupedByCategory = Object.values(aggregatedIngredients).reduce((acc, ingredient) => {
      const category = ingredient.category;
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(ingredient);
      return acc;
    }, {});

    Object.values(groupedByCategory).forEach(ingredients => {
      ingredients.sort((a, b) => a.name.localeCompare(b.name));
    });

    sortedIngredients = Object.entries(groupedByCategory)
      .sort(([catA], [catB]) => {
        const indexA = categoryOrder.indexOf(catA);
        const indexB = categoryOrder.indexOf(catB);
        if (indexA === -1 && indexB === -1) return catA.localeCompare(catB);
        if (indexA === -1) return 1;
        if (indexB === -1) return -1;
        return indexA - indexB;
      })
      .flatMap(([category, ingredients]) => ingredients);
  } else {
    sortedIngredients = allIngredients.sort((a, b) => {
      const indexA = subRecipeOrder.indexOf(a.subRecipeId);
      const indexB = subRecipeOrder.indexOf(b.subRecipeId);
      if (indexA === indexB) {
        return a.name.localeCompare(b.name);
      }
      return indexA - indexB;
    });
  }

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
            Ingrédients
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
          <Button
            variant="outlined"
            color="inherit"
            size="small"
            onClick={handleCopyIngredients}
            startIcon={<ContentCopyIcon sx={{ fontSize: '1.1rem' }} />}
            sx={{ 
              color: 'text.secondary',
              borderColor: 'divider',
              '&:hover': {
                bgcolor: 'action.hover',
                borderColor: 'text.secondary'
              },
              py: 0.5
            }}
          >
            Copier la liste
          </Button>
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
              sx={{ 
                color: 'text.secondary'
              }}
            >
              Mode liste de courses
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
          <Box key={columnIndex} sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
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
