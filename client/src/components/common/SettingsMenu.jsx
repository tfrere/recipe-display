import React, { useState } from 'react';
import { IconButton, Menu, MenuItem, ListItemIcon, ListItemText, Divider, Typography, Select } from '@mui/material';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import ViewStreamOutlinedIcon from '@mui/icons-material/ViewStreamOutlined';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import { usePreferences } from '../../contexts/PreferencesContext';
import { useTranslation } from 'react-i18next';

const VIEWS = {
  GRAPH: 'graph',
  SIMPLE: 'simple'
};

const SettingsMenu = ({ currentView, onViewChange, isRecipePage }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const { unitSystem, toggleUnitSystem } = usePreferences();
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
          sx: {
            minWidth: 200,
            '& .MuiMenuItem-root': {
              py: 1,
              px: 2
            }
          }
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {isRecipePage && (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ px: 2, py: 1 }}>
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
            <Divider sx={{ my: 1 }} />
          </>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ px: 2, py: 1 }}>
          {t('navigation.settings.units')}
        </Typography>
        <MenuItem>
          <Select
            value={unitSystem}
            onChange={handleUnitChange}
            size="small"
            fullWidth
            variant="standard"
          >
            <MenuItem value="metric">{t('navigation.settings.unitsSystem.metric')}</MenuItem>
            <MenuItem value="imperial">{t('navigation.settings.unitsSystem.imperial')}</MenuItem>
          </Select>
        </MenuItem>

        <Typography variant="body2" color="text.secondary" sx={{ px: 2, py: 1 }}>
          {t('navigation.settings.language')}
        </Typography>
        <MenuItem>
          <Select
            value={i18n.language}
            onChange={handleLanguageChange}
            size="small"
            fullWidth
            variant="standard"
          >
            <MenuItem value="fr">Français</MenuItem>
            <MenuItem value="en">English</MenuItem>
          </Select>
        </MenuItem>
      </Menu>
    </>
  );
};

export default SettingsMenu;
