import React, { useState } from "react";
import { useRecipe } from "../../../contexts/RecipeContext";
import RecipeHeader from "./RecipeHeader";
import IngredientsList from "./IngredientsList/index";
import PreparationSteps from "./PreparationSteps";
import { Box, Container, Paper, Divider } from "@mui/material";

const SimpleView = () => {
  const { recipe } = useRecipe();
  const [shoppingMode, setShoppingMode] = useState(false);

  return (
    <Box
      sx={{
        height: "calc(100vh - 64px)", // Hauteur totale moins la navbar
        overflow: "auto",
        p: { xs: 0, sm: 3, md: 4 },
        pt: { xs: 2, sm: 3, md: 4 },
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
              shoppingMode={shoppingMode}
              setShoppingMode={setShoppingMode}
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
