import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Box, Button, Typography } from '@mui/material';
import { useTheme } from '../../contexts/ThemeContext';
import { useLayout, LAYOUT_MODES } from '../../contexts/LayoutContext';
import { useRecipeList } from '../../contexts/RecipeListContext';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import KeyboardBackspaceOutlinedIcon from '@mui/icons-material/KeyboardBackspaceOutlined';
import AddOutlinedIcon from '@mui/icons-material/AddOutlined';
import AutoStoriesOutlinedIcon from '@mui/icons-material/AutoStoriesOutlined';
import SettingsMenu from './SettingsMenu';
import AddRecipeModal from './AddRecipeModal';

const NAVIGATION_TEXTS = {
  BACK: 'Back',
  ADD_RECIPE: 'Add recipe',
  COOKBOOK: 'Cookbook'
};

const Navigation = ({ currentView, onViewChange }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode, toggleDarkMode } = useTheme();
  const { layoutMode } = useLayout();
  const isRecipePage = location.pathname.startsWith('/recipe/');
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);
  const { 
    setSelectedDiet,
    setSelectedDifficulty,
    setSelectedSeason,
    setSelectedType,
    setSelectedDishType,
    setIsQuickOnly,
    setSearchQuery
  } = useRecipeList();

  const resetFilters = () => {
    setSelectedDiet(null);
    setSelectedDifficulty(null);
    setSelectedSeason(null);
    setSelectedType(null);
    setSelectedDishType(null);
    setIsQuickOnly(false);
    setSearchQuery('');
  };

  // Ensure currentView and onViewChange are defined
  const handleViewChange = (view) => {
    if (onViewChange && typeof onViewChange === 'function') {
      onViewChange(view);
    }
  };

  return (
    <>
      <AppBar 
        position="sticky" 
        elevation={0}
        sx={{ 
          bgcolor: 'background.paper',
          color: 'text.primary',
          borderBottom: (theme) => layoutMode === LAYOUT_MODES.TWO_COLUMN && isRecipePage ? 
            `1px solid ${theme.palette.divider}` : 'none',
          '@media print': {
            display: 'none'
          }
        }}
      >
        <Toolbar>
          <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
            {isRecipePage ? (
              <Button
                onClick={() => navigate('/')}
                startIcon={<KeyboardBackspaceOutlinedIcon />}
                sx={{ 
                  textTransform: 'none',
                  color: 'text.secondary',
                  '&:hover': {
                    color: 'text.primary'
                  }
                }}
              >
                {NAVIGATION_TEXTS.BACK}
              </Button>
            ) : (
              <Box 
                sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  cursor: 'pointer' 
                }}
                onClick={() => {
                  navigate('/');
                  resetFilters();
                }}
              >
                <AutoStoriesOutlinedIcon sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography variant="h6" component="div" color="text.secondary" sx={{ fontWeight: 500 }}>
                  {NAVIGATION_TEXTS.COOKBOOK}
                </Typography>
              </Box>
            )}
          </Box>

          <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button
              onClick={() => setIsAddRecipeModalOpen(true)}
              startIcon={<AddOutlinedIcon />}
              sx={{
                textTransform: 'none',
                color: 'text.secondary',
                '& .MuiSvgIcon-root': {
                  fontSize: '1.25rem',
                  strokeWidth: 1,
                  stroke: 'currentColor'
                },
                '&:hover': {
                  color: 'text.primary'
                }
              }}
            >
              {NAVIGATION_TEXTS.ADD_RECIPE}
            </Button>

            <SettingsMenu 
              currentView={currentView}
              onViewChange={handleViewChange}
              isRecipePage={isRecipePage}
              darkMode={darkMode}
              toggleDarkMode={toggleDarkMode}
            />
          </Box>
        </Toolbar>
      </AppBar>

      <AddRecipeModal 
        open={isAddRecipeModalOpen} 
        onClose={() => setIsAddRecipeModalOpen(false)} 
      />
    </>
  );
};

export default Navigation;
