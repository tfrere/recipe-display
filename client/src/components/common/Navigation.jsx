import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Box,
  Typography,
  Tooltip,
  Button,
} from "@mui/material";
import { useTheme } from "../../contexts/ThemeContext";
import {
  usePreferences,
  UNIT_SYSTEMS,
} from "../../contexts/PreferencesContext";
import { useRecipeList } from "../../contexts/RecipeListContext";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import AutoStoriesOutlinedIcon from "@mui/icons-material/AutoStoriesOutlined";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import NoAccountsOutlinedIcon from "@mui/icons-material/NoAccountsOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import { VIEWS } from "../../constants/views";
import { alpha } from "@mui/material/styles";
import AddRecipeModal from "./AddRecipe/AddRecipeModal";
import useCheatCode from "../../hooks/useCheatCode";

const NAVIGATION_TEXTS = {
  COOKBOOK: "Cookbook",
  ACTIONS: {
    TOGGLE_UNITS: {
      METRIC: "Switch to imperial units",
      IMPERIAL: "Switch to metric units",
    },
    ADD_RECIPE: "Add recipe",
    TOGGLE_GRAPH: "Toggle graph view",
    LOGOUT: "Logout",
  },
};

const Navigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode, toggleDarkMode } = useTheme();
  const { unitSystem, toggleUnitSystem } = usePreferences();
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);
  const { disablePrivateAccess, hasPrivateAccess } = useCheatCode();
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
    setSelectedSeason(null);
    setSelectedType(null);
    setSelectedDishType(null);
    setIsQuickOnly(false);
    setSearchQuery("");
  };

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          backgroundColor: "background.default",
          borderBottom: "none",
          color: "text.primary",
          "@media print": {
            display: "none",
          },
        }}
      >
        <Toolbar>
          <Box sx={{ display: "flex", alignItems: "center", flex: 1 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
              }}
              onClick={() => {
                navigate("/");
                resetFilters();
              }}
            >
              <AutoStoriesOutlinedIcon
                sx={{ mr: 1, color: "text.secondary" }}
              />
              <Typography
                variant="body1"
                sx={{
                  color: "text.primary",
                  fontWeight: 500,
                  display: { xs: "none", sm: "block" },
                }}
              >
                {NAVIGATION_TEXTS.COOKBOOK}
              </Typography>
            </Box>

            <Box sx={{ display: "flex", alignItems: "center", ml: 4 }}>
              {[
                { path: "/", label: "Recipes" },
                { path: "/ingredients", label: "Ingredients" },
              ].map((route, index) => (
                <React.Fragment key={route.path}>
                  {index > 0 && (
                    <Typography
                      variant="body2"
                      component="div"
                      color="text.secondary"
                      sx={{ mx: 1.5 }}
                    >
                      •
                    </Typography>
                  )}
                  <Button
                    variant="text"
                    sx={{
                      minWidth: "auto",
                      color:
                        location.pathname === route.path ||
                        (route.path === "/" && location.pathname === "/recipes")
                          ? "text.primary"
                          : "text.secondary",
                      p: "2px 0",
                      textTransform: "none",
                      borderBottom: (theme) =>
                        `1px solid ${alpha(theme.palette.text.secondary, 0)}`,
                      "&:hover": {
                        background: "none",
                        color: "text.primary",
                      },
                      ...(location.pathname === route.path ||
                      (route.path === "/" && location.pathname === "/recipes")
                        ? {
                            borderBottom: (theme) =>
                              `1px solid ${alpha(
                                theme.palette.text.secondary,
                                0.25
                              )}`,
                            borderRadius: 0,
                          }
                        : {}),
                    }}
                    disableRipple
                    onClick={() => navigate(route.path)}
                  >
                    {route.label}
                  </Button>
                </React.Fragment>
              ))}
            </Box>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {hasPrivateAccess && (
              <>
                <Tooltip title={NAVIGATION_TEXTS.ACTIONS.ADD_RECIPE}>
                  <Box
                    sx={{
                      p: 1,
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
                    onClick={() => setIsAddRecipeModalOpen(true)}
                  >
                    <AddOutlinedIcon sx={{ color: "text.secondary" }} />
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        fontWeight: 500,
                        display: { xs: "none", sm: "block" },
                      }}
                    >
                      {NAVIGATION_TEXTS.ACTIONS.ADD_RECIPE}
                    </Typography>
                  </Box>
                </Tooltip>
                <Tooltip title={NAVIGATION_TEXTS.ACTIONS.LOGOUT}>
                  <Box
                    sx={{
                      p: 1,
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
                    onClick={() => {
                      disablePrivateAccess();
                      window.location.reload();
                    }}
                  >
                    <NoAccountsOutlinedIcon sx={{ color: "text.secondary" }} />
                  </Box>
                </Tooltip>
              </>
            )}
            <Box
              sx={{
                p: 1,
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
                borderRadius: 1,
                "&:hover": {
                  bgcolor: "action.hover",
                },
              }}
              onClick={toggleDarkMode}
            >
              {darkMode ? (
                <LightModeOutlinedIcon sx={{ color: "text.secondary" }} />
              ) : (
                <DarkModeOutlinedIcon sx={{ color: "text.secondary" }} />
              )}
            </Box>
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
