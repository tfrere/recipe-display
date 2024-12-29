import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  Typography,
  Paper,
  Chip,
  Divider,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

const SearchResults = ({ results, onResultClick }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (!results.length) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">
          {t('search.noResults')}
        </Typography>
      </Box>
    );
  }

  const handleResultClick = (recipe) => {
    if (onResultClick) {
      onResultClick(recipe);
    }
    navigate(`/recipe/${recipe.slug}`);
  };

  return (
    <Paper 
      elevation={2}
      sx={{ 
        mt: 1,
        maxHeight: 400,
        overflow: 'auto',
        borderRadius: 2,
      }}
    >
      <List sx={{ p: 0 }}>
        {results.map((recipe, index) => (
          <React.Fragment key={recipe.slug}>
            <ListItem
              button
              onClick={() => handleResultClick(recipe)}
              sx={{
                '&:hover': {
                  bgcolor: 'action.hover',
                },
              }}
            >
              <ListItemText
                primary={
                  <Typography variant="subtitle1" component="div">
                    {recipe.title}
                  </Typography>
                }
                secondary={
                  <Box sx={{ mt: 0.5 }}>
                    {recipe.categories?.map((category, i) => (
                      <Chip
                        key={i}
                        label={t(`recipe.categories.${category}`)}
                        size="small"
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    ))}
                  </Box>
                }
              />
            </ListItem>
            {index < results.length - 1 && (
              <Divider component="li" />
            )}
          </React.Fragment>
        ))}
      </List>
    </Paper>
  );
};

export default SearchResults;
