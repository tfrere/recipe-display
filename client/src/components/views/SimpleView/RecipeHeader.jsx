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

const RecipeHeader = ({ recipe, onPrint }) => {
  const { currentServings, updateServings, getRemainingTime, resetRecipeState, isRecipePristine, completedSteps } = useRecipe();
  const { darkMode, toggleDarkMode } = useTheme();

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
            <RecipeImage imageName={image} />
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
          <Typography variant="h3" component="h1" align="center">
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
          gap: 2,
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          '@media print': { display: 'none' }
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Temps */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccessTimeIcon fontSize="small" color="action" />
              <Typography 
                variant="body2" 
                color="text.secondary"
                sx={{ 
                  fontWeight: getRemainingTime() !== null && Object.keys(completedSteps).length > 0 ? 700 : 400 
                }}
              >
                {(() => {
                  const remainingTime = getRemainingTime();
                  const hasCompletedSteps = Object.keys(completedSteps).length > 0;
                  if (remainingTime !== null && hasCompletedSteps) {
                    return (
                      <>
                        <TimeDisplay minutes={remainingTime} /> restantes
                      </>
                    );
                  }
                  const totalTime = recipe.totalTime.match(/(\d+)h?/)?.[1] * (recipe.totalTime.includes('h') ? 60 : 1) || 0;
                  return <TimeDisplay minutes={totalTime} />;
                })()}
              </Typography>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>

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
                {currentServings} {currentServings > 1 ? 'personnes' : 'personne'}
              </Typography>
              <Tooltip title="Réduire les portions">
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
              <Tooltip title="Augmenter les portions">
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
            <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>

            {/* Difficulté */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SignalCellularAltIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                {recipe.difficulty}
              </Typography>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ opacity: 0.5 }}>•</Typography>

            {/* Boutons d'action */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Imprimer la recette">
                <IconButton 
                  onClick={() => window.print()} 
                  size="small"
                  color="default"
                  aria-label="Imprimer la recette"
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
              <Tooltip title="Copier la recette">
                <IconButton
                  onClick={copyRecipeToClipboard}
                  size="small"
                  color="default"
                  aria-label="Copier la recette"
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
              <Tooltip title="Réinitialiser la recette">
                <span>
                  <IconButton
                    onClick={resetRecipeState}
                    size="small"
                    color="default"
                    disabled={isRecipePristine()}
                    aria-label="Réinitialiser la recette"
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
        </Box>
      </Box>
    </Container>
  );
};

export default RecipeHeader;