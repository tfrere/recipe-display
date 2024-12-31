import React from 'react';
import { Box } from '@mui/material';

const TwoColumnLayout = ({ header, content }) => {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr', // Deux colonnes égales
        height: 'calc(100vh - 64px)', // Hauteur totale moins la navbar
        overflow: 'hidden'
      }}
    >
      {/* Colonne de gauche - Header */}
      <Box
        sx={{
          p: 3,
          borderRight: '1px solid',
          borderColor: 'divider',
          overflow: 'auto',
          bgcolor: 'background.paper',
          display: 'flex',
          flexDirection: 'column',
          gap: 2
        }}
      >
        {header}
      </Box>

      {/* Colonne de droite - Contenu */}
      <Box
        sx={{
          p: 3,
          overflow: 'auto'
        }}
      >
        {content}
      </Box>
    </Box>
  );
};

export default TwoColumnLayout;
