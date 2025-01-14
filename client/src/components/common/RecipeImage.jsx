import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';
import KitchenOutlinedIcon from '@mui/icons-material/KitchenOutlined';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const PlaceholderBox = () => (
  <Box
    sx={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      bgcolor: 'background.default',
      color: 'text.secondary',
    }}
  >
    <KitchenOutlinedIcon sx={{ fontSize: 48 }} />
  </Box>
);

const RecipeImage = ({ slug, title, size = 'medium', sx = {}, onLoad }) => {
  const [error, setError] = useState(false);
  const [loadedImage, setLoadedImage] = useState(null);

  useEffect(() => {
    setError(false);
    setLoadedImage(null);
    
    if (slug) {
      const img = new Image();
      img.src = `${API_BASE_URL}/api/images/${size}/${slug}`;
      img.onload = () => {
        setLoadedImage(img.src);
        if (onLoad) {
          onLoad(img.naturalWidth / img.naturalHeight);
        }
      };
      img.onerror = () => setError(true);

      return () => {
        img.onload = null;
        img.onerror = null;
      };
    }
  }, [slug, size, onLoad]);

  if (error) {
    return <PlaceholderBox />;
  }

  if (!loadedImage) {
    return <PlaceholderBox />;
  }

  return (
    <Box
      component="img"
      src={loadedImage}
      alt={title || ''}
      sx={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        opacity: 1,
        transition: 'opacity 0.3s ease-in-out',
        ...sx
      }}
    />
  );
};

// Utiliser une fonction de comparaison personnalisée pour React.memo
export default React.memo(RecipeImage, (prevProps, nextProps) => {
  return prevProps.slug === nextProps.slug && 
         prevProps.size === nextProps.size && 
         prevProps.title === nextProps.title;
});
