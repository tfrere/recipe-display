import React from "react";
import { useRecipe } from "../../../contexts/RecipeContext";
import { usePreferences } from "../../../contexts/PreferencesContext";
import RecipeHeader from "./RecipeHeader";
import IngredientsList from "./IngredientsList/index";
import PreparationSteps from "./PreparationSteps";
import { Box, Container, Paper, Divider } from "@mui/material";

const SimpleView = () => {
  const { recipe } = useRecipe();
  const { sortByCategory, setSortByCategory } = usePreferences();

  return (
    <Box
      sx={{
        height: "calc(100vh - 64px)", // Hauteur totale moins la navbar
        overflow: "auto",
        p: { xs: 2, sm: 3, md: 4 },
        "@keyframes fadeIn": {
          "0%": {
            opacity: 0,
          },
          "100%": {
            opacity: 1,
          },
        },
        animation: "fadeIn 0.3s ease-in-out",
      }}
    >
      <Container
        sx={{
          maxWidth: "1000px !important",
          display: "flex",
          flexDirection: "column",
          gap: 3,
          mb: 9,
        }}
      >
        <Paper
          elevation={2}
          sx={{
            p: { xs: 3, sm: 4 },
            borderRadius: 2,
          }}
        >
          <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <RecipeHeader recipe={recipe} />
            <Divider sx={{ borderStyle: "dashed" }} />
            <IngredientsList
              recipe={recipe}
              sortByCategory={sortByCategory}
              setSortByCategory={setSortByCategory}
            />
            <Divider sx={{ borderStyle: "dashed" }} />
            <PreparationSteps recipe={recipe} />
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default SimpleView;
