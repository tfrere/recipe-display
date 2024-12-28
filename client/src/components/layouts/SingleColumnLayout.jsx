import React from 'react';
import { Box, Container } from '@mui/material';

const SingleColumnLayout = ({ header, content }) => {
  return (
    <Box
      sx={{
        height: 'calc(100vh - 64px)', // Hauteur totale moins la navbar
        overflow: 'auto',
        p: { xs: 2, sm: 3, md: 4 },
      }}
    >
      <Container 
        sx={{ 
          maxWidth: '1000px !important',
          display: 'flex',
          flexDirection: 'column',
          gap: 3
        }}
      >
        {header}
        {content}
      </Container>
    </Box>
  );
};

export default SingleColumnLayout;
