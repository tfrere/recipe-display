import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, CssBaseline } from '@mui/material';
import HomePage from "./pages/HomePage";
import RecipePage from "./pages/RecipePage";
import { RecipeProvider } from "./contexts/RecipeContext";
import { RecipeListProvider } from "./contexts/RecipeListContext"; // Added import statement
import { ThemeProvider } from './contexts/ThemeContext';
import { PreferencesProvider } from './contexts/PreferencesContext';
import { LayoutProvider } from './contexts/LayoutContext';
import Navigation from './components/common/Navigation';
import { I18nextProvider } from 'react-i18next';
import i18n from './i18n';

const VIEWS = {
  GRAPH: 'graph',
  SIMPLE: 'simple'
};

function App() {
  const [currentView, setCurrentView] = React.useState(VIEWS.SIMPLE);

  return (
    <I18nextProvider i18n={i18n}>
      <ThemeProvider>
        <PreferencesProvider>
          <LayoutProvider>
            <RecipeProvider>
              <RecipeListProvider>
                <CssBaseline />
                <Router>
                  <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
                    <Navigation currentView={currentView} onViewChange={setCurrentView} />
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
    </I18nextProvider>
  );
}

export default App;
