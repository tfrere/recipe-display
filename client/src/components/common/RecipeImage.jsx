import React from 'react';
import { Box } from '@mui/material';

const RecipeImage = ({ imageName, size = 'medium', sx = {} }) => {
  if (!imageName) return null;

  const baseUrl = 'http://localhost:8080/api/images';
  const imageUrl = `${baseUrl}/${size}/${imageName}`;

  return (
    <Box
      component="img"
      src={imageUrl}
      alt="Recipe"
      loading="lazy"
      srcSet={`
        ${baseUrl}/small/${imageName} 400w,
        ${baseUrl}/medium/${imageName} 800w,
        ${baseUrl}/large/${imageName} 1200w
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
