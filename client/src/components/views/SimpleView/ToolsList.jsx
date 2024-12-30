import React from 'react';
import { Box, Typography } from '@mui/material';
import { useRecipe } from '../../../contexts/RecipeContext';
import { useTranslation } from 'react-i18next';

const ToolsList = ({ recipe }) => {
  const { isToolUnused, completedSteps, tools } = useRecipe();
  const { t } = useTranslation();
  
  if (tools.length === 0) return null;

  const hasCompletedSteps = Object.keys(completedSteps || {}).length > 0;
  const remainingTools = tools.filter(tool => !isToolUnused(tool.id)).length;

  return (
    <>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center',
        mb: 2,
        gap: 1
      }}>
        <Typography variant="h5" component="span">
          {t('recipe.sections.tools')}
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
          • {hasCompletedSteps ? `${remainingTools}/` : ''}{tools.length}
        </Typography>
      </Box>

      <Box sx={{ 
        display: 'flex',
        flexWrap: 'wrap',
        gap: 1,
        alignItems: 'center',
        mb: 4
      }}>
        {tools.map((tool, index) => (
          <React.Fragment key={tool.id}>
            <Typography
              variant="body1"
              sx={{
                color: isToolUnused(tool.id) ? 'text.disabled' : 'text.primary',
                textDecoration: isToolUnused(tool.id) ? 'line-through' : 'none'
              }}
            >
              {tool.name}
            </Typography>
            {index < tools.length - 1 && (
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
