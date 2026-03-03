import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Box,
  Typography,
  Tooltip,
  Button,
  Badge,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useTheme } from "../../contexts/ThemeContext";
import { useRecipeList } from "../../contexts/RecipeListContext";
import useLocalStorage from "../../hooks/useLocalStorage";
import { usePantry } from "../../contexts/PantryContext";
import AutoStoriesOutlinedIcon from "@mui/icons-material/AutoStoriesOutlined";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import SettingsBrightnessOutlinedIcon from "@mui/icons-material/SettingsBrightnessOutlined";
import CloseIcon from "@mui/icons-material/Close";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import { alpha } from "@mui/material/styles";
import PantryDrawer from "./PantryDrawer";
import LoginDialog from "./LoginDialog";
import useLongPress from "../../hooks/useLongPress";

const Navigation = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode } = useTheme();
  const { pantrySize } = usePantry();
  const [isPantryOpen, setIsPantryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const { hasPrivateAccess, login, disablePrivateAccess } = useLongPress();
  const {
    setSelectedDiet,
    setSelectedDifficulty,
    setSelectedSeason,
    setSelectedType,
    setSelectedDishType,
    setIsQuickOnly,
    setSearchQuery,
  } = useRecipeList();

  const resetFilters = () => {
    setSelectedDiet(null);
    setSelectedDifficulty(null);
    setSelectedSeason([]);
    setSelectedType(null);
    setSelectedDishType(null);
    setIsQuickOnly(false);
    setSearchQuery("");
  };

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === "fr" ? "en" : "fr");
  };

  const routes = [
    { path: "/", label: t("nav.recipes") },
    { path: "/meal-planner", label: t("nav.mealPlanner") },
  ];

  return (
    <>
      <AppBar
        position="relative"
        elevation={0}
        className="no-print"
        sx={{
          backgroundColor: "background.default",
          borderBottom: "none",
          color: "text.primary",
          "@media print": { display: "none !important" },
        }}
      >
        <Toolbar>
          <Box sx={{ display: "flex", alignItems: "center", flex: 1 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
                position: "relative",
              }}
              onClick={() => {
                navigate("/");
                resetFilters();
              }}
            >
              <AutoStoriesOutlinedIcon
                sx={{
                  mr: 1,
                  color: "text.secondary",
                }}
              />
              <Typography
                variant="body1"
                sx={{
                  color: "text.primary",
                  fontWeight: 500,
                  display: { xs: "none", sm: "block" },
                }}
              >
                {t("nav.cookbook")}
              </Typography>
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", ml: 3 }}>
              {routes.map((route, index) => (
                <React.Fragment key={route.path}>
                  {index > 0 && (
                    <Typography
                      variant="body2"
                      component="div"
                      color="text.secondary"
                      sx={{ mx: 1.5 }}
                    >
                      ·
                    </Typography>
                  )}
                  <Button
                    variant="text"
                    size="small"
                    sx={{
                      minWidth: "auto",
                      color:
                        location.pathname === route.path
                          ? "text.primary"
                          : "text.secondary",
                      p: "4px 0",
                      textTransform: "none",
                      fontWeight: location.pathname === route.path ? 600 : 400,
                      fontSize: "0.85rem",
                      borderBottom: "1.5px solid",
                      borderColor:
                        location.pathname === route.path
                          ? alpha(
                              darkMode
                                ? "rgba(255,255,255,0.5)"
                                : "rgba(0,0,0,0.4)",
                              1
                            )
                          : "transparent",
                      borderRadius: 0,
                      "&:hover": {
                        background: "none",
                        color: "text.primary",
                      },
                    }}
                    disableRipple
                    onClick={() => {
                      if (route.path === "/") resetFilters();
                      navigate(route.path);
                    }}
                  >
                    {route.label}
                  </Button>
                </React.Fragment>
              ))}
            </Box>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Tooltip title={t("nav.myPantry")}>
              <Box
                sx={{
                  p: 0.75,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  cursor: "pointer",
                  borderRadius: 1,
                  border: "1px solid",
                  borderColor: "divider",
                  "&:hover": {
                    bgcolor: "action.hover",
                  },
                }}
                onClick={() => setIsPantryOpen(true)}
              >
                <Badge
                  badgeContent={pantrySize > 0 ? pantrySize : null}
                  max={99}
                  sx={{
                    "& .MuiBadge-badge": {
                      fontSize: "0.65rem",
                      height: 18,
                      minWidth: 18,
                      bgcolor: "background.paper",
                      color: "text.primary",
                      border: "1px solid",
                      borderColor: "text.primary",
                    },
                  }}
                >
                  <KitchenOutlinedIcon
                    sx={{
                      color: pantrySize > 0 ? "text.primary" : "text.secondary",
                      fontSize: "1.2rem",
                    }}
                  />
                </Badge>
                <Typography
                  variant="body2"
                  sx={{
                    color: pantrySize > 0 ? "text.primary" : "text.secondary",
                    fontWeight: pantrySize > 0 ? 600 : 500,
                    display: { xs: "none", sm: "block" },
                  }}
                >
                  {t("nav.pantry")}
                </Typography>
              </Box>
            </Tooltip>
            <Tooltip title={t("nav.settings", { defaultValue: "Settings" })}>
              <Box
                sx={{
                  p: 0.75,
                  display: "flex",
                  alignItems: "center",
                  cursor: "pointer",
                  borderRadius: 1,
                  border: "1px solid",
                  borderColor: "divider",
                  "&:hover": {
                    bgcolor: "action.hover",
                  },
                }}
                onClick={() => setIsSettingsOpen(true)}
              >
                <SettingsOutlinedIcon sx={{ color: "text.secondary", fontSize: "1.2rem" }} />
              </Box>
            </Tooltip>
            {hasPrivateAccess ? (
              <Tooltip title={t("nav.logout", { defaultValue: "Logout" })}>
                <Box
                  sx={{
                    p: 0.75,
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "divider",
                    "&:hover": {
                      bgcolor: "action.hover",
                    },
                  }}
                  onClick={disablePrivateAccess}
                >
                  <LogoutOutlinedIcon sx={{ color: "text.secondary", fontSize: "1.2rem" }} />
                </Box>
              </Tooltip>
            ) : (
              <Tooltip title={t("auth.login", { defaultValue: "Login" })}>
                <Box
                  sx={{
                    p: 0.75,
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "divider",
                    "&:hover": {
                      bgcolor: "action.hover",
                    },
                  }}
                  onClick={() => setIsLoginOpen(true)}
                >
                  <PersonOutlineOutlinedIcon sx={{ color: "text.secondary", fontSize: "1.2rem" }} />
                </Box>
              </Tooltip>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <PantryDrawer
        open={isPantryOpen}
        onClose={() => setIsPantryOpen(false)}
      />

      <SettingsDialog
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      <LoginDialog
        open={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        onLogin={login}
      />
    </>
  );
};

// ---------------------------------------------------------------------------
// Settings Dialog
// ---------------------------------------------------------------------------

const SettingsDialog = ({ open, onClose }) => {
  const { t, i18n } = useTranslation();
  const { themeMode, setThemeMode } = useTheme();
  const [unitSystem, setUnitSystem] = useLocalStorage("unit_system", "metric");

  const settingRow = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    py: 1.5,
    borderBottom: "1px solid",
    borderColor: "divider",
    "&:last-child": { borderBottom: "none" },
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{ sx: { borderRadius: 3 } }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pb: 0.5,
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "1rem" }}>
          {t("nav.settings", { defaultValue: "Settings" })}
        </Typography>
        <IconButton onClick={onClose} size="small" sx={{ color: "text.secondary" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ pt: 1 }}>
        {/* Language */}
        <Box sx={settingRow}>
          <Typography variant="body2" color="text.secondary">
            {t("nav.language", { defaultValue: "Language" })}
          </Typography>
          <ToggleButtonGroup
            value={i18n.language}
            exclusive
            onChange={(_, val) => val && i18n.changeLanguage(val)}
            size="small"
            sx={{
              "& .MuiToggleButton-root": {
                textTransform: "none",
                fontSize: "0.75rem",
                fontWeight: 500,
                px: 1.5,
                py: 0.3,
              },
            }}
          >
            <ToggleButton value="fr">FR</ToggleButton>
            <ToggleButton value="en">EN</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Theme */}
        <Box sx={settingRow}>
          <Typography variant="body2" color="text.secondary">
            {t("settings.theme", { defaultValue: "Theme" })}
          </Typography>
          <ToggleButtonGroup
            value={themeMode}
            exclusive
            onChange={(_, val) => val && setThemeMode(val)}
            size="small"
            sx={{
              "& .MuiToggleButton-root": {
                textTransform: "none",
                fontSize: "0.75rem",
                fontWeight: 500,
                px: 1.5,
                py: 0.3,
              },
            }}
          >
            <ToggleButton value="light">
              <LightModeOutlinedIcon sx={{ fontSize: "0.9rem", mr: 0.5 }} />
              {t("settings.light", { defaultValue: "Light" })}
            </ToggleButton>
            <ToggleButton value="dark">
              <DarkModeOutlinedIcon sx={{ fontSize: "0.9rem", mr: 0.5 }} />
              {t("settings.dark", { defaultValue: "Dark" })}
            </ToggleButton>
            <ToggleButton value="system">
              <SettingsBrightnessOutlinedIcon sx={{ fontSize: "0.9rem", mr: 0.5 }} />
              {t("settings.system", { defaultValue: "System" })}
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Unit system */}
        <Box sx={settingRow}>
          <Typography variant="body2" color="text.secondary">
            {t("settings.units", { defaultValue: "Units" })}
          </Typography>
          <ToggleButtonGroup
            value={unitSystem}
            exclusive
            onChange={(_, val) => val && setUnitSystem(val)}
            size="small"
            sx={{
              "& .MuiToggleButton-root": {
                textTransform: "none",
                fontSize: "0.75rem",
                fontWeight: 500,
                px: 1.5,
                py: 0.3,
              },
            }}
          >
            <ToggleButton value="metric">
              {t("settings.metric", { defaultValue: "Metric" })}
            </ToggleButton>
            <ToggleButton value="imperial">
              {t("settings.imperial", { defaultValue: "Imperial" })}
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default Navigation;
