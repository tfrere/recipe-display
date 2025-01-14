import React from 'react';
import { Box, Typography } from '@mui/material';
import { useRecipeList } from '../contexts/RecipeListContext';
import { useConstants } from '../contexts/ConstantsContext';

const ResultsLabel = () => {
  const { resultsType, getCurrentSeason } = useRecipeList();
  const { constants } = useConstants();

  const SEASON_LABELS = Object.fromEntries(
    constants.seasons.map(season => [season.id, season.label])
  );
  
  const RESULTS_TEXTS = {
    SEASONS: SEASON_LABELS,
    ALL: 'All seasons',
    RESULTS: 'results',
    QUICK: 'Quick recipes',
    RANDOM_SEASONAL: (season) => `Random ${season.toLowerCase()} recipes`,
    FILTERED: 'Filtered recipes'
  };

  const currentSeason = getCurrentSeason();
  const seasonText = RESULTS_TEXTS.SEASONS[currentSeason];

  return (
    <Box>
      <Typography 
        variant="body1" 
        sx={{ 
          color: 'text.secondary',
          fontSize: '1rem',
          fontWeight: 500,
          opacity: 0.8
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
