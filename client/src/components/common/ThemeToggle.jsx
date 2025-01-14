const THEME_TEXTS = {
  LIGHT_MODE: "Light mode",
  DARK_MODE: "Dark mode"
};

import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import { useTheme } from '../../contexts/ThemeContext';

const ThemeToggle = () => {
  const { darkMode, toggleDarkMode } = useTheme();

  return (
    <Tooltip title={darkMode ? THEME_TEXTS.LIGHT_MODE : THEME_TEXTS.DARK_MODE}>
      <IconButton 
        onClick={toggleDarkMode}
        size="large"
        disableRipple
        sx={{
          position: 'fixed',
          top: 16,
          right: 16,
          zIndex: 1200,
          color: 'text.primary',
          p: 1,
          '@media print': { display: 'none' },
          '& .MuiSvgIcon-root': {
            transition: 'transform 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
            fontSize: '1.5rem',
          },
          '&:hover .MuiSvgIcon-root': {
            transform: 'rotate(15deg)',
          },
          '&:active .MuiSvgIcon-root': {
            transform: 'rotate(360deg)',
            transition: 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
          },
        }}
      >
        {darkMode ? (
          <LightModeOutlinedIcon sx={{ animation: 'fadeIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
        ) : (
          <DarkModeOutlinedIcon sx={{ animation: 'fadeIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
        )}
      </IconButton>
    </Tooltip>
  );
};

export default ThemeToggle;
