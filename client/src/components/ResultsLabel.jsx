import React from 'react';
import { Box, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useRecipeList } from '../contexts/RecipeListContext';

const ResultsLabel = () => {
  const { t } = useTranslation();
  const { resultsType, getCurrentSeason } = useRecipeList();

  const currentSeason = getCurrentSeason();

  return (
    <Box>
      <Typography 
        variant="h6" 
        sx={{ 
          color: 'text.primary',
        }}
      >
        {resultsType === 'random_seasonal' 
          ? t('results.randomSeasonal', { season: t(`season.${currentSeason}`.toLowerCase()) })
          : t('results.filtered')}
      </Typography>
    </Box>
  );
};

export default ResultsLabel;
