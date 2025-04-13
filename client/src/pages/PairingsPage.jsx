import React, { useState, useEffect } from "react";
import { Box, Typography, CircularProgress } from "@mui/material";
import { IngredientGraph } from "../components/IngredientGraph";

// Hauteur estimée de la barre de navigation
const NAV_HEIGHT = 64;

const PairingsPage = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState([]);

  // Chargement des données
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/tsne_ingredients_data.json");
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`);
        }
        const jsonData = await response.json();

        // Filtrer uniquement les ingrédients
        const ingredients = jsonData.filter(
          (item) => item.node_type === "ingredient"
        );
        setData(ingredients);
        setIsLoading(false);
      } catch (err) {
        console.error("Erreur lors du chargement des données:", err);
        setError(err.message);
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Gestion des erreurs et de l'état de chargement
  if (error) {
    return (
      <Box
        sx={{
          height: `calc(100vh - ${NAV_HEIGHT}px)`,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 2,
        }}
      >
        <Typography variant="h5" color="error">
          Erreur de chargement des données
        </Typography>
        <Typography color="text.secondary">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: `calc(100vh - ${NAV_HEIGHT}px)`,
        width: "100vw",
        overflow: "hidden",
        position: "relative",
        bgcolor: "background.default",
      }}
    >
      {isLoading ? (
        <Box
          sx={{
            height: "100%",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            flexDirection: "column",
            gap: 2,
          }}
        >
          <CircularProgress />
          <Typography>Chargement des données en cours...</Typography>
        </Box>
      ) : (
        <IngredientGraph data={data} navHeight={NAV_HEIGHT} />
      )}
    </Box>
  );
};

export default PairingsPage;
