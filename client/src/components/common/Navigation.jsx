import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Box, Button } from '@mui/material';
import { useTheme } from '../../contexts/ThemeContext';
import { useLayout, LAYOUT_MODES } from '../../contexts/LayoutContext';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import KeyboardBackspaceOutlinedIcon from '@mui/icons-material/KeyboardBackspaceOutlined';
import AddOutlinedIcon from '@mui/icons-material/AddOutlined';
import SettingsMenu from './SettingsMenu';
import AddRecipeModal from './AddRecipeModal';
import { useTranslation } from 'react-i18next';

const Navigation = ({ currentView, onViewChange }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode, toggleDarkMode } = useTheme();
  const { layoutMode } = useLayout();
  const isRecipePage = location.pathname.startsWith('/recipe/');
  const { t } = useTranslation();
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);

  return (
    <>
      <AppBar 
        position="sticky" 
        elevation={0}
        sx={{ 
          bgcolor: 'background.paper',
          color: 'text.primary',
          borderBottom: (theme) => layoutMode === LAYOUT_MODES.TWO_COLUMN ? 
            `1px solid ${theme.palette.divider}` : 'none',
          '@media print': {
            display: 'none'
          }
        }}
      >
        <Toolbar>
          {isRecipePage && (
            <Button
              onClick={() => navigate('/')}
              startIcon={<KeyboardBackspaceOutlinedIcon />}
              sx={{ 
                textTransform: 'none',
                color: 'text.secondary',
                ml: 2,
                '&:hover': {
                  color: 'text.primary'
                }
              }}
            >
              {t('navigation.backToRecipes')}
            </Button>
          )}
          
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
              {t('navigation.addRecipe')}
            </Button>

            <SettingsMenu 
              currentView={currentView} 
              onViewChange={onViewChange} 
              isRecipePage={isRecipePage}
              darkMode={darkMode}
              onToggleDarkMode={toggleDarkMode}
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
