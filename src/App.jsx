import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Box } from "@mui/material";
import HomePage from "./pages/HomePage";
import RecipePage from "./pages/RecipePage";
import { RecipeProvider } from "./contexts/RecipeContext";

function App() {
  return (
    <BrowserRouter>
      <RecipeProvider>
        <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/recipe/:recipeId" element={<RecipePage />} />
          </Routes>
        </Box>
      </RecipeProvider>
    </BrowserRouter>
  );
}

export default App;
