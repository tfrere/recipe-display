import React, { useState, useEffect } from "react";
import {
  Box,
  TextField,
  Typography,
  Card,
  CardContent,
  Grid,
  Container
} from "@mui/material";
import { Link } from "react-router-dom";
import RecipeImage from "../components/common/RecipeImage";
import { useTranslation } from 'react-i18next';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const HomePage = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [recipes, setRecipes] = useState([]);
  const { t } = useTranslation();

  useEffect(() => {
    const fetchRecipes = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/recipes`);
        const data = await response.json();
        setRecipes(data);
      } catch (error) {
        console.error('Error fetching recipes:', error);
      }
    };
    fetchRecipes();
  }, []);

  const filteredRecipes = recipes.filter((recipe) =>
    recipe.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" component="h1" gutterBottom>
        {t('home.title')}
      </Typography>

      <TextField
        fullWidth
        variant="outlined"
        placeholder={t('home.search')}
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 4 }}
      />

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
                  imageName={recipe.image}
                  size="medium"
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    borderRadius: '4px 4px 0 0',
                  }}
                />
              </Box>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  {recipe.title}
                </Typography>
                {recipe.description && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {recipe.description}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default HomePage;
