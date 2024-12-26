import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Box, IconButton, Button } from '@mui/material';
import { useTheme } from '../../contexts/ThemeContext';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import KeyboardBackspaceOutlinedIcon from '@mui/icons-material/KeyboardBackspaceOutlined';
import SettingsMenu from './SettingsMenu';
import { useTranslation } from 'react-i18next';

const Navigation = ({ currentView, onViewChange }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode, toggleDarkMode } = useTheme();
  const isRecipePage = location.pathname.startsWith('/recipe/');
  const { t } = useTranslation();

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{ 
        bgcolor: 'background.paper',
        color: 'text.primary',
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
          <SettingsMenu currentView={currentView} onViewChange={onViewChange} isRecipePage={isRecipePage} />
          
          <IconButton 
            onClick={toggleDarkMode} 
            color="inherit"
            disableRipple
            sx={{
              color: 'text.secondary',
              '& .MuiSvgIcon-root': {
                transition: 'transform 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
                fontSize: '1.25rem',
              },
              '&:hover': {
                color: 'text.primary',
                '& .MuiSvgIcon-root': {
                  transform: 'rotate(12deg)'
                }
              }
            }}
          >
            {darkMode ? <DarkModeOutlinedIcon /> : <LightModeOutlinedIcon />}
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navigation;
