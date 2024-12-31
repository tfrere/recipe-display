import React from 'react';
import { Box, Typography } from '@mui/material';
import { useRecipeList } from '../contexts/RecipeListContext';
import constants from '@shared/constants.json';

const SEASON_LABELS = Object.fromEntries(
  constants.seasons.map(season => [season.id, season.label])
);

const RESULTS_TEXTS = {
  SEASONS: SEASON_LABELS,
  ALL: 'All seasons',
  RESULTS: 'results',
  QUICK: 'Quick recipes',
  RANDOM_SEASONAL: (season) => `Random recipes for ${season}`,
  FILTERED: 'Filtered recipes'
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
