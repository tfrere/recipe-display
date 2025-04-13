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
import { RecipeProvider } from "./contexts/RecipeContext";
import { RecipeListProvider } from "./contexts/RecipeListContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { PreferencesProvider } from "./contexts/PreferencesContext";
import { ConstantsProvider } from "./contexts/ConstantsContext";
import { AuthorsProvider } from "./contexts/AuthorsContext";
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
        </Routes>
      </AppTransition>
    </AnimatePresence>
  );
};

const AppContent = () => {
  return (
    <RecipeProvider>
      <RecipeListProvider>
        <CssBaseline />
        <Router>
          <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
            <Navigation />
            <AnimatedRoutes />
          </Box>
        </Router>
      </RecipeListProvider>
    </RecipeProvider>
  );
};

function App() {
  return (
    <ThemeProvider>
      <PreferencesProvider>
        <ConstantsProvider>
          <AuthorsProvider>
            <RecipeListProvider>
              <AppContent />
            </RecipeListProvider>
          </AuthorsProvider>
        </ConstantsProvider>
      </PreferencesProvider>
    </ThemeProvider>
  );
}

export default App;
