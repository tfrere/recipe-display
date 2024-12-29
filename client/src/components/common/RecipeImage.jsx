import React from 'react';
import { Box } from '@mui/material';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const RecipeImage = ({ slug, title, size = 'medium', sx = {} }) => {
  if (!slug) return null;

  const baseUrl = `${API_BASE_URL}/api/images`;
  const imageUrl = `${baseUrl}/${size}/${slug}`;

  return (
    <Box
      component="img"
      src={imageUrl}
      alt={title || "Recipe"}
      loading="lazy"
      srcSet={`
        ${baseUrl}/small/${slug} 400w,
        ${baseUrl}/medium/${slug} 800w,
        ${baseUrl}/large/${slug} 1200w
      `}
      sizes="(max-width: 400px) 100vw,
             (max-width: 800px) 800px,
             1200px"
      sx={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        ...sx
      }}
    />
  );
};

export default RecipeImage;
