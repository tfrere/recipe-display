import React from 'react';
import { TextField, InputAdornment, Box, Typography } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import NoRecipesIcon from '@mui/icons-material/SentimentDissatisfied';
import { useTranslation } from 'react-i18next';
import { useRecipeList } from '../contexts/RecipeListContext';

const SearchBar = () => {
  const { t } = useTranslation();
  const { searchQuery, setSearchQuery, allRecipes, filteredRecipes } = useRecipeList();

  const isFiltered = searchQuery.length > 0;
  const hasNoResults = isFiltered && filteredRecipes.length === 0;

  return (
    <Box sx={{ width: '100%', maxWidth: 800, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: hasNoResults ? 2 : 0 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder={t('search.byIngredients')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <Typography 
                  variant="body2" 
                  color="text.secondary"
                  sx={{ 
                    fontWeight: isFiltered ? 700 : 400,
                    minWidth: 80,
                    textAlign: 'right'
                  }}
                >
                  {filteredRecipes.length} / {allRecipes.length}
                </Typography>
              </InputAdornment>
            )
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
              backgroundColor: 'background.paper',
              '&:hover': {
                '& > fieldset': {
                  borderColor: 'primary.main',
                },
              },
            },
          }}
        />
      </Box>
      
      {hasNoResults && (
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          gap: 1,
          mt: 2 
        }}>
          <NoRecipesIcon color="action" />
          <Typography variant="body2" color="text.secondary">
            {t('search.noResults')}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default SearchBar;
