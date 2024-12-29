import React from 'react';
import { Box, Typography, Container, IconButton, Tooltip } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import GroupIcon from '@mui/icons-material/Group';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import SignalCellularAltIcon from '@mui/icons-material/SignalCellularAlt';
import PrintOutlinedIcon from '@mui/icons-material/PrintOutlined';
import ContentCopyOutlinedIcon from '@mui/icons-material/ContentCopyOutlined';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import RecipeImage from '../../common/RecipeImage';
import RecipeChip, { CHIP_TYPES } from '../../common/RecipeChip';
import { useRecipe } from '../../../contexts/RecipeContext';
import { useTheme } from '../../../contexts/ThemeContext';
import { useLayout, LAYOUT_MODES } from '../../../contexts/LayoutContext';
import { useTranslation } from 'react-i18next';
import { TimeDisplay } from './PreparationSteps';

const formatTime = (minutes) => {
  // Arrondir au multiple de 5 le plus proche
  minutes = Math.round(minutes / 5) * 5;
  
  if (minutes < 60) {
    return `${minutes}min`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  if (remainingMinutes === 0) {
    return `${hours}h`;
  }
  
  return `${hours}h${remainingMinutes}`;
};

const RecipeHeader = ({ recipe }) => {
  const { currentServings, updateServings, getRemainingTime, resetRecipeState, isRecipePristine, calculateTotalTime } = useRecipe();
  const { darkMode, toggleDarkMode } = useTheme();
  const { layoutMode } = useLayout();
  const { t } = useTranslation();

  const handleServingsChange = (delta) => {
    const newServings = currentServings + delta;
    if (newServings >= 1) {
      updateServings(newServings);
    }
  };

  const copyRecipeToClipboard = () => {
    const recipeText = `${recipe.title}

${recipe.description || ''}

Pour ${recipe.servings} personnes${recipe.difficulty ? ` • ${recipe.difficulty}` : ''}${recipe.totalTime ? ` • ${recipe.totalTime}` : ''}

Ingrédients :
${Object.entries(recipe.ingredients || {})
  .map(([_, ingredient]) => `- ${ingredient.amount} ${ingredient.unit} ${ingredient.name}`)
  .join('\n')}

Préparation :
${Object.entries(recipe.steps || {})
  .map(([_, step], index) => `${index + 1}. ${step.action}${step.time ? ` (${step.time})` : ''}`)
  .join('\n')}`;

    navigator.clipboard.writeText(recipeText).then(() => {
      // Vous pourriez ajouter une notification ici si vous le souhaitez
      console.log('Recette copiée dans le presse-papiers');
    });
  };

  if (!recipe) {
    return null;
  }

  const { title, image, description, difficulty } = recipe;

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
        {/* Image */}
        {image && (
          <Box sx={{ 
            width: '100%', 
            maxWidth: 600, 
            height: 300, 
            position: 'relative',
            borderRadius: 2,
            overflow: 'hidden',
            '@media print': { display: 'none' } 
          }}>
            <RecipeImage slug={image} title={title} size="large" />
          </Box>
        )}

        {/* Title and Description */}
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column',
          alignItems: 'center',
          gap: 2,
          '@media print': { display: 'none' }
        }}>
          <Typography 
            variant={layoutMode === LAYOUT_MODES.TWO_COLUMN ? "h4" : "h3"} 
            component="h1" 
            align="center"
          >
            {title}
          </Typography>
          
          {description && (
            <Typography variant="body1" color="text.secondary" align="center" sx={{ maxWidth: 800 }}>
              {description}
            </Typography>
          )}
        </Box>

        {/* Metadata and Controls */}
        <Box sx={{ 
          display: 'flex',
          flexDirection: layoutMode === LAYOUT_MODES.TWO_COLUMN ? 'column' : 'row',
          gap: 2,
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          '@media print': { display: 'none' }
        }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 2,
            width: layoutMode === LAYOUT_MODES.TWO_COLUMN ? '100%' : 'auto',
            justifyContent: layoutMode === LAYOUT_MODES.TWO_COLUMN ? 'space-between' : 'flex-start'
          }}>
            {/* Temps */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccessTimeIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {calculateTotalTime(recipe)}
              </Typography>
            </Box>

            {layoutMode !== LAYOUT_MODES.TWO_COLUMN && (
              <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>
            )}

            {/* Difficulté */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SignalCellularAltIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                {recipe.difficulty}
              </Typography>
            </Box>

            {layoutMode !== LAYOUT_MODES.TWO_COLUMN && (
              <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>
            )}

            {/* Régime alimentaire et Saison */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <RecipeChip 
                label={t(`recipe.diet.${recipe.diet || 'normal'}`)} 
                type={CHIP_TYPES.DIET}
                size="small"
              />
              <RecipeChip 
                label={t(`recipe.season.${recipe.season || 'spring'}`)} 
                type={CHIP_TYPES.SEASON}
                size="small"
              />
              <RecipeChip 
                label={t(`recipe.type.${recipe.recipeType || 'main'}`)} 
                type={CHIP_TYPES.RECIPE_TYPE}
                size="small"
              />
            </Box>

            {layoutMode !== LAYOUT_MODES.TWO_COLUMN && (
              <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>
            )}

            {/* Personnes */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <GroupIcon fontSize="small" color="action" />
              <Typography 
                variant="body2" 
                color="text.secondary"
                sx={{ 
                  fontWeight: currentServings !== recipe.servings ? 700 : 400 
                }}
              >
                {t('recipe.servings.' + (currentServings > 1 ? 'multiple' : 'single'), { count: currentServings })}
              </Typography>
              <Tooltip title={t('recipe.actions.decreaseServings')}>
                <IconButton 
                  size="small"
                  onClick={() => handleServingsChange(-1)}
                  disabled={currentServings <= 1}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    '&:hover': {
                      borderColor: 'action.hover'
                    }
                  }}
                >
                  <RemoveIcon sx={{ fontSize: '1rem' }} />
                </IconButton>
              </Tooltip>
              <Tooltip title={t('recipe.actions.increaseServings')}>
                <IconButton 
                  size="small"
                  onClick={() => handleServingsChange(1)}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    '&:hover': {
                      borderColor: 'action.hover'
                    }
                  }}
                >
                  <AddIcon sx={{ fontSize: '1rem' }} />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {layoutMode === LAYOUT_MODES.TWO_COLUMN && (
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 2,
              width: '100%',
              justifyContent: 'center'
            }}>
              {/* Boutons d'action */}
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Tooltip title={t('recipe.actions.print')}>
                  <IconButton 
                    onClick={() => window.print()} 
                    size="small"
                    color="default"
                    aria-label={t('recipe.actions.print')}
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      '&:hover': {
                        borderColor: 'action.hover'
                      }
                    }}
                  >
                    <PrintOutlinedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title={t('recipe.actions.copy')}>
                  <IconButton
                    onClick={copyRecipeToClipboard}
                    size="small"
                    color="default"
                    aria-label={t('recipe.actions.copy')}
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
                <Tooltip title={t('recipe.actions.reset')}>
                  <span>
                    <IconButton
                      onClick={resetRecipeState}
                      size="small"
                      color="default"
                      disabled={isRecipePristine()}
                      aria-label={t('recipe.actions.reset')}
                      sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        '&:hover': {
                          borderColor: 'action.hover'
                        }
                      }}
                    >
                      <RestartAltIcon fontSize="small" />
                    </IconButton>
                  </span>
                </Tooltip>
              </Box>
            </Box>
          )}

          {layoutMode !== LAYOUT_MODES.TWO_COLUMN && (
            <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>
          )}

          {layoutMode !== LAYOUT_MODES.TWO_COLUMN && (
            /* Boutons d'action */
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title={t('recipe.actions.print')}>
                <IconButton 
                  onClick={() => window.print()} 
                  size="small"
                  color="default"
                  aria-label={t('recipe.actions.print')}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    '&:hover': {
                      borderColor: 'action.hover'
                    }
                  }}
                >
                  <PrintOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={t('recipe.actions.copy')}>
                <IconButton
                  onClick={copyRecipeToClipboard}
                  size="small"
                  color="default"
                  aria-label={t('recipe.actions.copy')}
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
              <Tooltip title={t('recipe.actions.reset')}>
                <span>
                  <IconButton
                    onClick={resetRecipeState}
                    size="small"
                    color="default"
                    disabled={isRecipePristine()}
                    aria-label={t('recipe.actions.reset')}
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      '&:hover': {
                        borderColor: 'action.hover'
                      }
                    }}
                  >
                    <RestartAltIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
          )}
        </Box>
      </Box>
    </Container>
  );
};

export default RecipeHeader;
