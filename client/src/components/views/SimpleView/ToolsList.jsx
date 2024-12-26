import React from 'react';
import { Box, Typography } from '@mui/material';
import { useRecipe } from '../../../contexts/RecipeContext';

const ToolsList = ({ recipe }) => {
  const { isToolUnused, completedSteps } = useRecipe();
  
  // Récupérer tous les outils utilisés dans la recette
  const allTools = Object.entries(recipe.tools || {}).map(([toolId, tool]) => ({
    id: toolId,
    name: tool.name,
    isUnused: isToolUnused(toolId)
  }));

  if (allTools.length === 0) return null;

  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingTools = allTools.filter(tool => !tool.isUnused).length;

  return (
    <>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center',
        mb: 2,
        gap: 1
      }}>
        <Typography variant="h5" component="span">
          Ustensiles
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
          • {hasCompletedSteps ? `${remainingTools}/` : ''}{allTools.length}
        </Typography>
      </Box>

      <Box sx={{ 
        display: 'flex',
        flexWrap: 'wrap',
        gap: 1,
        alignItems: 'center'
      }}>
        {allTools.map((tool, index) => (
          <React.Fragment key={tool.id}>
            <Typography 
              variant="body1"
              sx={{ 
                textDecoration: tool.isUnused ? 'line-through' : 'none',
                color: tool.isUnused ? 'text.disabled' : 'text.primary'
              }}
            >
              {tool.name}
            </Typography>
            {index < allTools.length - 1 && (
              <Typography 
                variant="body2" 
                sx={{ color: 'text.disabled' }}
              >
                •
              </Typography>
            )}
          </React.Fragment>
        ))}
      </Box>
    </>
  );
};

export default ToolsList;
