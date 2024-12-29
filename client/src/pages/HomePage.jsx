import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Container,
  CircularProgress,
  Alert
} from "@mui/material";
import { Link } from "react-router-dom";
import RecipeImage from "../components/common/RecipeImage";
import { useTranslation } from 'react-i18next';
import SearchBar from '../components/SearchBar';
import FilterTags from '../components/FilterTags';
import ResultsLabel from '../components/ResultsLabel';
import { useRecipeList } from '../contexts/RecipeListContext';

const HomePage = () => {
  const { t } = useTranslation();
  const { filteredRecipes, loading, error } = useRecipeList();

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>{t('common.loading')}</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ py: 8 }}>
        <Alert severity="error">{t('common.error')}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ pt: 8, pb: 4 }}>
        <SearchBar />
        <Box sx={{ mt: 2 }}>
          <FilterTags />
        </Box>
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 1 }}>
        <ResultsLabel />
      </Box>

      <Grid container spacing={3}>
        {filteredRecipes.map((recipe) => (
          <Grid item xs={12} sm={6} md={4} key={recipe.slug}>
            <Card
              component={Link}
              to={`/recipe/${recipe.slug}`}
              sx={{
                height: "100%",
                textDecoration: "none",
                transition: "transform 0.2s",
                "&:hover": {
                  transform: "scale(1.02)",
                },
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <Box sx={{ position: 'relative', paddingTop: '56.25%' }}>
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
                  }}
                />
              </Box>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  {t(`recipes.${recipe.slug}.title`, recipe.title)}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                >
                  {t(`recipes.${recipe.slug}.description`, recipe.metadata.description)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default HomePage;
