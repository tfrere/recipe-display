import React from 'react';
import { Box } from '@mui/material';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const RecipeImage = ({ slug, title, size = 'medium', sx = {} }) => {
  if (!slug) return null;

  return (
    <Box
      component="img"
      src={`${API_BASE_URL}/api/images/${size}/${slug}`}
      alt={title}
      loading="lazy"
      sx={{
        objectFit: 'cover',
        width: '100%',
        height: '100%',
        ...sx
      }}
    />
  );
};

export default RecipeImage;
