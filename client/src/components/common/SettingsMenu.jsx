import React, { useState } from "react";
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Select,
  Box,
} from "@mui/material";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import ViewStreamOutlinedIcon from "@mui/icons-material/ViewStreamOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import { VIEWS } from "../../constants/views";

const SETTINGS_TEXTS = {
  VIEW: {
    TITLE: "View",
    SIMPLE: "Simple view",
    GRAPH: "Graph view",
  },
};

const SettingsMenu = ({
  currentView,
  onViewChange,
  isRecipePage,
  darkMode,
  toggleDarkMode,
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const unitSystem = "metric";

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

  return (
    <>
      <IconButton
        onClick={handleClick}
        edge="end"
        aria-label="settings"
        aria-controls={open ? "settings-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={open ? "true" : undefined}
        sx={{
          color: open ? "primary.main" : "text.secondary",
          transition: "all 0.2s ease-in-out",
          "&:hover": {
            color: "primary.main",
            backgroundColor: "transparent",
          },
        }}
      >
        <SettingsOutlinedIcon />
      </IconButton>

      <Menu
        id="settings-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        PaperProps={{
          elevation: 3,
          sx: {
            minWidth: 250,
            overflow: "visible",
            mt: 1.5,
            "&:before": {
              content: '""',
              display: "block",
              position: "absolute",
              top: 0,
              right: 14,
              width: 10,
              height: 10,
              bgcolor: "background.paper",
              transform: "translateY(-50%) rotate(45deg)",
              zIndex: 0,
            },
            "& .MuiMenuItem-root": {
              py: 1.5,
              px: 2.5,
            },
            "& .MuiDivider-root": {
              my: 1,
            },
            "& .MuiTypography-root.menu-section": {
              px: 2.5,
              py: 1.5,
              fontSize: "0.75rem",
              fontWeight: 700,
              letterSpacing: "0.5px",
              textTransform: "uppercase",
              color: "text.secondary",
            },
          },
        }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
      >
        {isRecipePage && (
          <>
            <Typography
              variant="body2"
              color="text.secondary"
              className="menu-section"
            >
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
          </>
        )}
      </Menu>
    </>
  );
};

export default SettingsMenu;
