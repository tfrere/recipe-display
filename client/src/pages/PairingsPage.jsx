import React from 'react';
import { Box, Typography, Container } from '@mui/material';

const PairingsPage = () => {
  return (
    <Container maxWidth="md">
      <Box
        sx={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          gap: 2
        }}
      >
        <Typography variant="h3" component="h1" gutterBottom>
          Coming Soon
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: '600px' }}>
          The pairings feature will allow discovering complementary ingredients and flavor combinations. 
          This tool will help explore new culinary possibilities and enhance recipe creation.
        </Typography>
      </Box>
    </Container>
  );
};

export default PairingsPage;
