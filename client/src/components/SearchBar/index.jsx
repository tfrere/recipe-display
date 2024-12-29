import React from 'react';
import { Box, Fade, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import SearchBar from './SearchBar';
import SearchResults from './SearchResults';
import { useRecipeSearch } from '../../hooks/useRecipeSearch';

const SearchBarWithResults = ({ recipes, onResultClick }) => {
  const { t } = useTranslation();
  const {
    searchTerm,
    setSearchTerm,
    searchResults,
  } = useRecipeSearch(recipes);

  const showResults = searchTerm.length > 0;

  return (
    <Box sx={{ position: 'relative', width: '100%', zIndex: 1000 }}>
      <SearchBar
        value={searchTerm}
        onChange={setSearchTerm}
        onClear={() => setSearchTerm('')}
      />
      
      {showResults && (
        <>
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mb: 1,
              color: 'text.secondary',
              textAlign: 'right',
            }}
          >
            {t('search.results', {
              count: searchResults.length
            })}
          </Typography>
          
          <Fade in={showResults}>
            <Box>
              <SearchResults
                results={searchResults}
                onResultClick={onResultClick}
              />
            </Box>
          </Fade>
        </>
      )}
    </Box>
  );
};

export default SearchBarWithResults;
