import React from 'react';
import { Box, Typography } from '@mui/material';
import { useRecipeList } from '../contexts/RecipeListContext';

const RESULTS_TEXTS = {
  RANDOM_SEASONAL: (season) => `Random recipes for ${season}`,
  FILTERED: 'Filtered recipes',
  SEASONS: {
    WINTER: 'winter',
    SPRING: 'spring',
    SUMMER: 'summer',
    FALL: 'fall'
  }
};

const ResultsLabel = () => {
  const { resultsType, getCurrentSeason } = useRecipeList();

  const currentSeason = getCurrentSeason();
  const seasonText = RESULTS_TEXTS.SEASONS[currentSeason.toUpperCase()];

  return (
    <Box>
      <Typography 
        variant="h6" 
        sx={{ 
          color: 'text.primary',
        }}
      >
        {resultsType === 'random_seasonal' 
          ? RESULTS_TEXTS.RANDOM_SEASONAL(seasonText)
          : RESULTS_TEXTS.FILTERED}
      </Typography>
    </Box>
  );
};

export default ResultsLabel;
