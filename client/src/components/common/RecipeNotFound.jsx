import React from 'react';
import { Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

const StyledBox = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  padding: theme.spacing(3),
  textAlign: 'center',
  backgroundColor: theme.palette.background.default,
  color: theme.palette.text.primary,
}));

const RecipeNotFound = () => {
  return (
    <StyledBox>
      <Typography variant="h4" component="h1" gutterBottom>
        Recipe Not Found
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Sorry, we couldn't find the recipe you're looking for.
      </Typography>
    </StyledBox>
  );
};

export default RecipeNotFound;
