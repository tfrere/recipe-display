const HOME_TEXTS = {
  NO_RECIPES: {
    TITLE: 'No recipes found',
    DESCRIPTION: 'Try adding a new recipe by clicking the + button in the top right corner'
  },
  COMMON: {
    LOADING: 'Loading...',
    ERROR: 'An error occurred while loading recipes'
  }
};

import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Container,
  CircularProgress,
  Alert,
  Paper,
} from "@mui/material";
import { Link } from "react-router-dom";
import RecipeImage from "../components/common/RecipeImage";
import SearchBarWithResults from '../components/SearchBar/index';
import FilterTags from '../components/FilterTags';
import ResultsLabel from '../components/ResultsLabel';
import { useRecipeList } from '../contexts/RecipeListContext';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import BoltIcon from '@mui/icons-material/Bolt';
import RecipeHeader from '../components/views/SimpleView/RecipeHeader';

const NoRecipes = () => {
  return (
    <Paper 
      elevation={0}
      sx={{ 
        py: 8,
        px: 4,
        textAlign: 'center',
        bgcolor: 'transparent',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2
      }}
    >
      <RestaurantIcon sx={{ fontSize: 64, color: 'text.secondary', opacity: 0.5 }} />
      <Typography variant="h6" color="text.secondary">
        {HOME_TEXTS.NO_RECIPES.TITLE}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 500 }}>
        {HOME_TEXTS.NO_RECIPES.DESCRIPTION}
      </Typography>
    </Paper>
  );
};

const HomePage = () => {
  const { filteredRecipes, loading, error } = useRecipeList();

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>{HOME_TEXTS.COMMON.LOADING}</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ py: 8 }}>
        <Alert severity="error">{HOME_TEXTS.COMMON.ERROR}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ pt: 8, pb: 4, width: '100%' }}>
        <SearchBarWithResults recipes={filteredRecipes} />
        <Box sx={{ mt: 2 }}>
          <FilterTags />
        </Box>
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 1 }}>
        <ResultsLabel />
      </Box>

      {filteredRecipes.length === 0 ? (
        <NoRecipes />
      ) : (
        <Grid container spacing={3}>
          {filteredRecipes.map((recipe) => (
            <Grid item xs={12} sm={6} md={3} key={recipe.slug}>
              <Card
                component={Link}
                to={`/recipe/${recipe.slug}`}
                sx={{
                  height: "100%",
                  textDecoration: "none",
                  transition: "all 0.2s ease-in-out",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: (theme) => theme.shadows[8],
                  },
                  display: 'flex',
                  flexDirection: 'column',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <Box sx={{ position: 'relative', paddingTop: '80%', width: '100%' }}>
                  <RecipeImage
                    slug={recipe.slug}
                    title={recipe.title}
                    size="medium"
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 12,
                      right: 12,
                      display: 'flex',
                      gap: 1,
                      alignItems: 'center',
                    }}
                  >
                    {recipe.metadata?.totalTime && (
                      <Box
                        sx={{
                          bgcolor: 'background.paper',
                          color: 'text.primary',
                          px: 1,
                          py: 0.5,
                          borderRadius: 1,
                          fontSize: '0.75rem',
                          fontWeight: 'medium',
                          boxShadow: 1,
                        }}
                      >
                        {recipe.metadata.totalTime}
                      </Box>
                    )}
                    {recipe.metadata?.quick && (
                      <Box
                        sx={{
                          bgcolor: 'primary.main',
                          color: 'primary.contrastText',
                          p: 0.5,
                          borderRadius: 1,
                          display: 'flex',
                          alignItems: 'center',
                          boxShadow: 1,
                        }}
                      >
                        <BoltIcon sx={{ fontSize: '1rem' }} />
                      </Box>
                    )}
                  </Box>
                </Box>
                <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Typography variant="h6" component="h2">
                    {recipe.title}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Container>
  );
};

export default HomePage;
