import React, { useState } from "react";
import {
  Box,
  TextField,
  Typography,
  Card,
  CardContent,
  Grid,
} from "@mui/material";
import { Link } from "react-router-dom";

const RECIPES = [
  {
    id: "buche-noel",
    title: "Bûche de Noël",
    file: "/data/buche-noel.recipe.json",
  },
  {
    id: "laap-thailandais",
    title: "Laap Thailandais",
    file: "/data/laap-thailandais.recipe.json",
  },
];

const HomePage = () => {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredRecipes = RECIPES.filter((recipe) =>
    recipe.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Typography variant="h3" component="h1" gutterBottom>
        Mes Recettes
      </Typography>

      <TextField
        fullWidth
        variant="outlined"
        placeholder="Rechercher une recette..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 4 }}
      />

      <Grid container spacing={3}>
        {filteredRecipes.map((recipe) => (
          <Grid item xs={12} sm={6} md={4} key={recipe.id}>
            <Card
              component={Link}
              to={`/recipe/${recipe.id}`}
              sx={{
                textDecoration: "none",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                transition: "transform 0.2s",
                "&:hover": {
                  transform: "scale(1.02)",
                },
              }}
            >
              <CardContent>
                <Typography variant="h5" component="h2">
                  {recipe.title}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default HomePage;
