import React from 'react';
import { Box, Typography, Container, IconButton, Tooltip } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import GroupIcon from '@mui/icons-material/Group';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import PrintOutlinedIcon from '@mui/icons-material/PrintOutlined';
import ContentCopyOutlinedIcon from '@mui/icons-material/ContentCopyOutlined';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import SignalCellularAltIcon from '@mui/icons-material/SignalCellularAlt';
import RecipeImage from '../../common/RecipeImage';
import RecipeChip, { CHIP_TYPES } from '../../common/RecipeChip';
import { useRecipe } from '../../../contexts/RecipeContext';
import { useTheme } from '../../../contexts/ThemeContext';
import { useLayout, LAYOUT_MODES } from '../../../contexts/LayoutContext';
import { TimeDisplay } from './PreparationSteps';
import constants from '@shared/constants.json';

// Convert arrays to lookup objects for easy access
const RECIPE_TYPE_LABELS = Object.fromEntries(
  constants.recipe_types.map(type => [type.id, type.label])
);
const DIET_LABELS = Object.fromEntries(
  constants.diets.map(diet => [diet.id, diet.label])
);
const SEASON_LABELS = Object.fromEntries(
  constants.seasons.map(season => [season.id, season.label])
);

const HEADER_TEXTS = {
  ACTIONS: {
    PRINT: 'Print recipe',
    COPY: 'Copy recipe',
    RESET: 'Reset recipe progress',
    INCREASE_SERVINGS: 'Increase servings',
    DECREASE_SERVINGS: 'Decrease servings'
  },
  SERVINGS: {
    SINGLE: '1 serving',
    MULTIPLE: (count) => `${count} servings`
  }
};

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
          <Box
            sx={{
              position: 'relative',
              width: '100%',
              maxWidth: '1200px',
              aspectRatio: '16/9',
              overflow: 'hidden',
              borderRadius: { xs: 0, sm: '16px' },
              mt: 8, // Ajouté une marge supérieure de 4 unités (32px)
              mb: 2,
              boxShadow: (theme) => 
                theme.palette.mode === 'dark' 
                  ? '0 8px 32px rgba(0, 0, 0, 0.5)'
                  : '0 8px 32px rgba(0, 0, 0, 0.1)',
              '&::after': {
                content: '""',
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: '30%',
                background: 'linear-gradient(to top, rgba(0,0,0,0.4), rgba(0,0,0,0))',
                pointerEvents: 'none'
              }
            }}
          >
            <RecipeImage 
              slug={image} 
              title={title} 
              size="large"
              sx={{
                objectFit: 'cover',
                width: '100%',
                height: '100%'
              }}
            />
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

            {/* Régime alimentaire, Saison et Type de plat */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography 
                variant="body2" 
                color="text.secondary"
                sx={{ 
                  fontWeight: 600,
                  textTransform: 'capitalize'
                }}
              >
                {DIET_LABELS[recipe.metadata?.diet || 'normal']}
                {" • "}
                {SEASON_LABELS[recipe.metadata?.season || 'all']}
                {" • "}
                {RECIPE_TYPE_LABELS[recipe.metadata?.type || 'main']}
              </Typography>
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
                {currentServings === 1 ? HEADER_TEXTS.SERVINGS.SINGLE : HEADER_TEXTS.SERVINGS.MULTIPLE(currentServings)}
              </Typography>
              <Tooltip title={HEADER_TEXTS.ACTIONS.DECREASE_SERVINGS}>
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
              <Tooltip title={HEADER_TEXTS.ACTIONS.INCREASE_SERVINGS}>
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
                <Tooltip title={HEADER_TEXTS.ACTIONS.PRINT}>
                  <IconButton 
                    onClick={() => window.print()} 
                    size="small"
                    color="default"
                    aria-label={HEADER_TEXTS.ACTIONS.PRINT}
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
                <Tooltip title={HEADER_TEXTS.ACTIONS.COPY}>
                  <IconButton
                    onClick={copyRecipeToClipboard}
                    size="small"
                    color="default"
                    aria-label={HEADER_TEXTS.ACTIONS.COPY}
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
                <Tooltip title={HEADER_TEXTS.ACTIONS.RESET}>
                  <span>
                    <IconButton
                      onClick={resetRecipeState}
                      size="small"
                      color="default"
                      disabled={isRecipePristine()}
                      aria-label={HEADER_TEXTS.ACTIONS.RESET}
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
              <Tooltip title={HEADER_TEXTS.ACTIONS.PRINT}>
                <IconButton 
                  onClick={() => window.print()} 
                  size="small"
                  color="default"
                  aria-label={HEADER_TEXTS.ACTIONS.PRINT}
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
              <Tooltip title={HEADER_TEXTS.ACTIONS.COPY}>
                <IconButton
                  onClick={copyRecipeToClipboard}
                  size="small"
                  color="default"
                  aria-label={HEADER_TEXTS.ACTIONS.COPY}
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
              <Tooltip title={HEADER_TEXTS.ACTIONS.RESET}>
                <span>
                  <IconButton
                    onClick={resetRecipeState}
                    size="small"
                    color="default"
                    disabled={isRecipePristine()}
                    aria-label={HEADER_TEXTS.ACTIONS.RESET}
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
