import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";
import { Box, CssBaseline } from "@mui/material";
import { AnimatePresence } from "framer-motion";
import HomePage from "./pages/HomePage";
import RecipePage from "./pages/RecipePage";
import PairingsPage from "./pages/PairingsPage";
import WinePage from "./pages/WinePage";
import MealPlannerPage from "./pages/MealPlannerPage";
import { RecipeProvider } from "./contexts/RecipeContext";
import { RecipeListProvider } from "./contexts/RecipeListContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ConstantsProvider } from "./contexts/ConstantsContext";
import { AuthorsProvider } from "./contexts/AuthorsContext";
import { PantryProvider } from "./contexts/PantryContext";
import Navigation from "./components/common/Navigation";
import AppTransition from "./components/common/AppTransition";

// Composant pour gérer les animations de route
const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <AppTransition type="page" key={location.pathname}>
        <Routes location={location}>
          <Route path="/" element={<HomePage />} />
          <Route path="/recipe/:slug" element={<RecipePage />} />
          <Route path="/ingredients" element={<PairingsPage />} />
          <Route path="/wines" element={<WinePage />} />
          <Route path="/meal-planner" element={<MealPlannerPage />} />
        </Routes>
      </AppTransition>
    </AnimatePresence>
  );
};

const AppContent = () => {
  return (
    <RecipeProvider>
      <CssBaseline />
      <Router>
        <RecipeListProvider>
          <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
            <Navigation />
            <AnimatedRoutes />
          </Box>
        </RecipeListProvider>
      </Router>
    </RecipeProvider>
  );
};

function App() {
  return (
    <ThemeProvider>
      <ConstantsProvider>
        <AuthorsProvider>
          <PantryProvider>
            <AppContent />
          </PantryProvider>
        </AuthorsProvider>
      </ConstantsProvider>
    </ThemeProvider>
  );
}

export default App;
