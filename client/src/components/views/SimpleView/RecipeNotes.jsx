import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { useTranslation } from 'react-i18next';
import NotesIcon from '@mui/icons-material/Notes';

const RecipeNotes = ({ notes }) => {
  const { t } = useTranslation();

  if (!notes) return null;

  return (
    <Paper 
      elevation={0} 
      sx={{ 
        p: 3,
        bgcolor: 'background.default',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <NotesIcon color="action" />
        <Typography variant="h6" component="h2">
          {t('recipe.notes')}
        </Typography>
      </Box>
      <Typography 
        variant="body1" 
        color="text.secondary"
        sx={{ 
          whiteSpace: 'pre-wrap',
          fontStyle: 'italic'
        }}
      >
        {notes}
      </Typography>
    </Paper>
  );
};

export default RecipeNotes;
