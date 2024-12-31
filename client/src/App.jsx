import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, CssBaseline } from '@mui/material';
import HomePage from "./pages/HomePage";
import RecipePage from "./pages/RecipePage";
import { RecipeProvider } from "./contexts/RecipeContext";
import { RecipeListProvider } from "./contexts/RecipeListContext"; 
import { ThemeProvider } from './contexts/ThemeContext';
import { PreferencesProvider } from './contexts/PreferencesContext';
import { LayoutProvider } from './contexts/LayoutContext';
import Navigation from './components/common/Navigation';
import { VIEWS } from './constants/views';

function App() {
  const [currentView, setCurrentView] = React.useState(VIEWS.SIMPLE);

  // Ensure view state is properly managed
  const handleViewChange = (view) => {
    if (Object.values(VIEWS).includes(view)) {
      setCurrentView(view);
    }
  };

  return (
    <ThemeProvider>
      <PreferencesProvider>
        <LayoutProvider>
          <RecipeProvider>
            <RecipeListProvider>
              <CssBaseline />
              <Router>
                <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
                  <Navigation currentView={currentView} onViewChange={handleViewChange} />
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/recipe/:slug" element={<RecipePage currentView={currentView} />} />
                  </Routes>
                </Box>
              </Router>
            </RecipeListProvider>
          </RecipeProvider>
        </LayoutProvider>
      </PreferencesProvider>
    </ThemeProvider>
  );
}

export default App;
