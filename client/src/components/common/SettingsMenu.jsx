import React, { useState } from 'react';
import { IconButton, Menu, MenuItem, ListItemIcon, ListItemText, Divider, Typography, Select, Box } from '@mui/material';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import ViewStreamOutlinedIcon from '@mui/icons-material/ViewStreamOutlined';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import { usePreferences } from '../../contexts/PreferencesContext';
import { VIEWS } from '../../constants/views';

const SETTINGS_TEXTS = {
  VIEW: {
    TITLE: 'View',
    SIMPLE: 'Simple view',
    GRAPH: 'Graph view'
  },
  PREFERENCES: {
    TITLE: 'Preferences',
    LIGHT_MODE: 'Light mode',
    DARK_MODE: 'Dark mode',
    METRIC_UNITS: 'Metric units',
    IMPERIAL_UNITS: 'Imperial units'
  }
};

const SettingsMenu = ({ currentView, onViewChange, isRecipePage, darkMode, toggleDarkMode }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const { unitSystem, toggleUnitSystem } = usePreferences();

  const open = Boolean(anchorEl);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleViewChange = (view) => {
    onViewChange?.(view);
    handleClose();
  };

  const handleUnitChange = (event) => {
    toggleUnitSystem();
  };

  return (
    <>
      <IconButton
        onClick={handleClick}
        sx={{
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
        <SettingsOutlinedIcon />
      </IconButton>
      
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        PaperProps={{
          elevation: 3,
          sx: {
            minWidth: 250,
            overflow: 'visible',
            mt: 1.5,
            '&:before': {
              content: '""',
              display: 'block',
              position: 'absolute',
              top: 0,
              right: 14,
              width: 10,
              height: 10,
              bgcolor: 'background.paper',
              transform: 'translateY(-50%) rotate(45deg)',
              zIndex: 0,
            },
            '& .MuiMenuItem-root': {
              py: 1.5,
              px: 2.5
            },
            '& .MuiDivider-root': {
              my: 1
            },
            '& .MuiTypography-root.menu-section': {
              px: 2.5,
              py: 1.5,
              fontSize: '0.75rem',
              fontWeight: 700,
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              color: 'text.secondary'
            }
          }
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {isRecipePage && (
          <>
            <Typography variant="body2" color="text.secondary" className="menu-section">
              {SETTINGS_TEXTS.VIEW.TITLE}
            </Typography>
            <MenuItem 
              onClick={() => handleViewChange(VIEWS.SIMPLE)}
              selected={currentView === VIEWS.SIMPLE}
            >
              <ListItemIcon>
                <ViewStreamOutlinedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{SETTINGS_TEXTS.VIEW.SIMPLE}</ListItemText>
            </MenuItem>
            <MenuItem 
              onClick={() => handleViewChange(VIEWS.GRAPH)}
              selected={currentView === VIEWS.GRAPH}
            >
              <ListItemIcon>
                <AccountTreeOutlinedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{SETTINGS_TEXTS.VIEW.GRAPH}</ListItemText>
            </MenuItem>
            <Divider />
          </>
        )}

        <Typography variant="body2" color="text.secondary" className="menu-section">
          {SETTINGS_TEXTS.PREFERENCES.TITLE}
        </Typography>

        <MenuItem onClick={toggleDarkMode}>
          <ListItemIcon>
            {darkMode ? 
              <DarkModeOutlinedIcon fontSize="small" /> : 
              <LightModeOutlinedIcon fontSize="small" />
            }
          </ListItemIcon>
          <ListItemText>
            {darkMode ? SETTINGS_TEXTS.PREFERENCES.LIGHT_MODE : SETTINGS_TEXTS.PREFERENCES.DARK_MODE}
          </ListItemText>
        </MenuItem>

        <MenuItem onClick={handleUnitChange}>
          <ListItemIcon>
            <Box component="span" sx={{ 
              width: 20, 
              height: 20, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: 600
            }}>
              {unitSystem === 'metric' ? 'g' : 'oz'}
            </Box>
          </ListItemIcon>
          <ListItemText>
            {unitSystem === 'metric' ? 
              SETTINGS_TEXTS.PREFERENCES.IMPERIAL_UNITS : 
              SETTINGS_TEXTS.PREFERENCES.METRIC_UNITS}
          </ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
};

export default SettingsMenu;
