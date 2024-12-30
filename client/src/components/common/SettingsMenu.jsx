import React, { useState } from 'react';
import { IconButton, Menu, MenuItem, ListItemIcon, ListItemText, Divider, Typography, Select, Box } from '@mui/material';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import ViewStreamOutlinedIcon from '@mui/icons-material/ViewStreamOutlined';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import ViewColumnOutlinedIcon from '@mui/icons-material/ViewColumnOutlined';
import ViewAgendaOutlinedIcon from '@mui/icons-material/ViewAgendaOutlined';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import { usePreferences } from '../../contexts/PreferencesContext';
import { useLayout, LAYOUT_MODES } from '../../contexts/LayoutContext';
import { useTranslation } from 'react-i18next';
import { VIEWS } from '../../constants/views';

const SettingsMenu = ({ currentView, onViewChange, isRecipePage, darkMode, toggleDarkMode }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const { unitSystem, toggleUnitSystem } = usePreferences();
  const { layoutMode, toggleLayout } = useLayout();
  const { t, i18n } = useTranslation();
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

  const handleLanguageChange = (event) => {
    i18n.changeLanguage(event.target.value);
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
              {t('navigation.settings.view')}
            </Typography>
            <MenuItem 
              onClick={() => handleViewChange(VIEWS.SIMPLE)}
              selected={currentView === VIEWS.SIMPLE}
            >
              <ListItemIcon>
                <ViewStreamOutlinedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{t('navigation.views.simple')}</ListItemText>
            </MenuItem>
            <MenuItem 
              onClick={() => handleViewChange(VIEWS.GRAPH)}
              selected={currentView === VIEWS.GRAPH}
            >
              <ListItemIcon>
                <AccountTreeOutlinedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{t('navigation.views.graph')}</ListItemText>
            </MenuItem>
            <Divider />
          </>
        )}

        {isRecipePage && currentView === VIEWS.SIMPLE && (
          <>
            <Typography variant="body2" color="text.secondary" className="menu-section">
              {t('navigation.settings.layout')}
            </Typography>
            <MenuItem onClick={toggleLayout}>
              <ListItemIcon>
                {layoutMode === LAYOUT_MODES.SINGLE_COLUMN ? 
                  <ViewColumnOutlinedIcon fontSize="small" /> : 
                  <ViewAgendaOutlinedIcon fontSize="small" />
                }
              </ListItemIcon>
              <ListItemText>
                {layoutMode === LAYOUT_MODES.SINGLE_COLUMN ? 
                  t('navigation.settings.twoColumns') : 
                  t('navigation.settings.oneColumn')
                }
              </ListItemText>
            </MenuItem>
            <Divider />
          </>
        )}

        <Typography variant="body2" color="text.secondary" className="menu-section">
          {t('navigation.settings.preferences')}
        </Typography>

        <MenuItem onClick={toggleDarkMode}>
          <ListItemIcon>
            {darkMode ? 
              <DarkModeOutlinedIcon fontSize="small" /> : 
              <LightModeOutlinedIcon fontSize="small" />
            }
          </ListItemIcon>
          <ListItemText>
            {darkMode ? t('navigation.settings.lightMode') : t('navigation.settings.darkMode')}
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
              t('navigation.settings.imperialUnits') : 
              t('navigation.settings.metricUnits')
            }
          </ListItemText>
        </MenuItem>

        <Divider />

        <Typography variant="body2" color="text.secondary" className="menu-section">
          {t('navigation.settings.language')}
        </Typography>
        <MenuItem onClick={() => i18n.changeLanguage('fr')} selected={i18n.language === 'fr'}>
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
              FR
            </Box>
          </ListItemIcon>
          <ListItemText>Français</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => i18n.changeLanguage('en')} selected={i18n.language === 'en'}>
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
              EN
            </Box>
          </ListItemIcon>
          <ListItemText>English</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
};

export default SettingsMenu;
