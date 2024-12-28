import React from 'react';
import { Box, Typography } from '@mui/material';
import { useRecipe } from '../../../contexts/RecipeContext';
import { highlightMatches } from '../../../utils/textUtils.jsx';
import { useTranslation } from 'react-i18next';

const parseTime = (timeString) => {
  if (!timeString) return 0;
  const match = timeString.match(/(\d+)\s*min/);
  return match ? parseInt(match[1], 10) : 0;
};

export const TimeDisplay = ({ minutes, sx = {} }) => {
  const { t } = useTranslation();
  
  if (!minutes) return null;
  
  if (minutes < 60) {
    return (
      <Box component="span" sx={{ display: 'inline', ...sx }}>
        {t('recipe.time.minute', { count: minutes })}
      </Box>
    );
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  if (remainingMinutes === 0) {
    return (
      <Box component="span" sx={{ display: 'inline', ...sx }}>
        {t('recipe.time.hour', { count: hours })}
      </Box>
    );
  }
  
  return (
    <Box component="span" sx={{ display: 'inline', ...sx }}>
      {t('recipe.time.hourMinute', { count: hours, minutes: remainingMinutes })}
    </Box>
  );
};

const PreparationSteps = ({ recipe }) => {
  const { 
    completedSteps, 
    toggleStepCompletion, 
    completedSubRecipes,
    toggleSubRecipeCompletion,
    getSubRecipeRemainingTime,
    getSubRecipeStats,
    getCompletedSubRecipesCount
  } = useRecipe();
  const { t } = useTranslation();

  const handleSubRecipeClick = (subRecipeId, steps) => {
    const isCompleted = !completedSubRecipes[subRecipeId];
    toggleSubRecipeCompletion(subRecipeId, isCompleted);
    
    // Si on marque comme complété, on coche toutes les étapes
    steps.forEach(step => {
      if (isCompleted !== !!completedSteps[step.id]) {
        toggleStepCompletion(step.id, isCompleted, subRecipeId);
      }
    });
  };

  const numSubRecipes = Object.keys(recipe.subRecipes || {}).length;
  const isSingleSubRecipe = numSubRecipes === 1;
  
  // Pour le cas d'une sous-recette unique, utiliser getSubRecipeStats
  const singleSubRecipeStats = isSingleSubRecipe 
    ? getSubRecipeStats(Object.keys(recipe.subRecipes)[0])
    : null;

  // Utiliser getCompletedSubRecipesCount pour le nombre de sous-recettes complétées
  const completedSubRecipesCount = getCompletedSubRecipesCount();

  return (
    <Box sx={{ pb: 12 }}>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center',
        mb: 4,
        gap: 1
      }}>
        <Typography variant="h5" component="span">
          {t('recipe.sections.preparation')}
        </Typography>
        {isSingleSubRecipe ? (
          <Typography 
            variant="body2" 
            sx={{ 
              color: 'text.disabled',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5
            }}
          >
            • {singleSubRecipeStats.completedStepsCount > 0 ? `${singleSubRecipeStats.completedStepsCount}/` : ''}{singleSubRecipeStats.totalSteps}
          </Typography>
        ) : (
          <Typography 
            variant="body2" 
            sx={{ 
              color: 'text.disabled',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5
            }}
          >
            • {completedSubRecipesCount > 0 ? `${completedSubRecipesCount}/` : ''}{numSubRecipes}
          </Typography>
        )}
      </Box>

      {Object.entries(recipe.subRecipes || {}).map(([subRecipeId, subRecipe], index) => {
        const remainingTime = getSubRecipeRemainingTime(subRecipeId);
        const isSubRecipeCompleted = completedSubRecipes[subRecipeId];

        return (
          <Box key={subRecipeId} sx={{ mb: index < Object.keys(recipe.subRecipes).length - 1 ? 8 : 0 }}>
            <Box
              sx={{
                mb: 3,
                cursor: 'pointer',
                '&:hover': {
                  opacity: 0.8,
                }
              }}
              onClick={() => handleSubRecipeClick(subRecipeId, Object.values(subRecipe.steps || {}))}
            >
              {numSubRecipes > 1 && (
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  mb: 2
                }}>
                  <Box sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    gap: 1
                  }}>
                    <Typography 
                      variant="h6" 
                      sx={{ 
                        fontWeight: 600,
                        textDecoration: isSubRecipeCompleted ? 'line-through' : 'none',
                        color: isSubRecipeCompleted ? 'text.disabled' : 'text.primary'
                      }}
                    >
                      {subRecipe.title}
                    </Typography>
                    {(() => {
                      const stats = getSubRecipeStats(subRecipeId);
                      return (
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            color: 'text.disabled',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.5
                          }}
                        >
                          • {stats.completedStepsCount > 0 ? `${stats.completedStepsCount}/` : ''}{stats.totalSteps}
                        </Typography>
                      );
                    })()}
                  </Box>
                  {remainingTime > 0 && (
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        ml: 2,
                        textDecoration: isSubRecipeCompleted ? 'line-through' : 'none',
                        color: 'text.secondary',
                        fontWeight: 700
                      }}
                    >
                      <TimeDisplay minutes={remainingTime} />
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
            {Object.entries(subRecipe.steps || {}).map(([stepId, step], index) => {
              const isCompleted = completedSteps[step.id];
              
              return (
                <Box 
                  key={stepId}
                  onClick={() => toggleStepCompletion(step.id, !isCompleted, subRecipeId)}
                  sx={{
                    display: 'flex',
                    gap: 1.5,
                    mb: 2,
                    cursor: 'pointer',
                    '&:last-child': {
                      mb: 0
                    }
                  }}
                >
                  <Typography 
                    sx={{ 
                      color: 'text.disabled',
                      minWidth: '24px',
                      textDecoration: isCompleted ? 'line-through' : 'none',
                      fontSize: '1.1rem'
                    }}
                  >
                    {index + 1}.
                  </Typography>
                  <Typography 
                    variant="body1"
                    sx={{
                      textDecoration: isCompleted ? 'line-through' : 'none',
                      color: isCompleted ? 'text.disabled' : 'text.primary',
                      flex: 1,
                      fontSize: '1.1rem',
                      lineHeight: 1.5
                    }}
                  >
                    {highlightMatches(step.action, recipe, {
                      inputs: step.inputs || [],
                      tools: step.tools || [],
                      output: step.output
                    })}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        );
      })}
    </Box>
  );
};

export default PreparationSteps;
