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
} from "@mui/material";
import { useTheme } from "../../contexts/ThemeContext";
import { useRecipeList } from "../../contexts/RecipeListContext";
import { usePantry } from "../../contexts/PantryContext";
import AutoStoriesOutlinedIcon from "@mui/icons-material/AutoStoriesOutlined";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import NoAccountsOutlinedIcon from "@mui/icons-material/NoAccountsOutlined";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import { alpha } from "@mui/material/styles";
import AddRecipeModal from "./AddRecipe/AddRecipeModal";
import PantryDrawer from "./PantryDrawer";
import useLongPress from "../../hooks/useLongPress";

const NAVIGATION_TEXTS = {
  COOKBOOK: "Cookbook",
  ACTIONS: {
    ADD_RECIPE: "Add recipe",
    TOGGLE_GRAPH: "Toggle graph view",
    LOGOUT: "Logout",
  },
};

const Navigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { darkMode } = useTheme();
  const { pantrySize } = usePantry();
  const [isAddRecipeModalOpen, setIsAddRecipeModalOpen] = useState(false);
  const [isPantryOpen, setIsPantryOpen] = useState(false);
  const { disablePrivateAccess, hasPrivateAccess, pressing, longPressProps } =
    useLongPress();
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

  const handleDisablePrivateAccess = () => {
    disablePrivateAccess();
  };

  return (
    <>
      <AppBar
        position="relative"
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
                position: "relative",
              }}
              onClick={() => {
                navigate("/");
                resetFilters();
              }}
              {...longPressProps}
            >
              <AutoStoriesOutlinedIcon
                sx={{
                  mr: 1,
                  color: pressing ? "primary.main" : "text.secondary",
                  transition: "color 0.2s ease-in-out",
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
                {NAVIGATION_TEXTS.COOKBOOK}
              </Typography>
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", ml: 3 }}>
              {[
                { path: "/", label: "Recipes" },
                { path: "/meal-planner", label: "Meal Planner" },
              ].map((route, index) => (
                <React.Fragment key={route.path}>
                  {index > 0 && (
                    <Typography
                      variant="body2"
                      component="div"
                      color="text.secondary"
                      sx={{ mx: 1.5, display: { xs: "none", sm: "block" } }}
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
            <Tooltip title="My Pantry">
              <Box
                sx={{
                  p: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  cursor: "pointer",
                  borderRadius: 1,
                  border: "1px solid",
                  borderColor: pantrySize > 0 ? "text.primary" : "divider",
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
                      bgcolor: "text.primary",
                      color: "background.paper",
                    },
                  }}
                >
                  <KitchenOutlinedIcon
                    sx={{
                      color: pantrySize > 0 ? "text.primary" : "text.secondary",
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
                  Pantry
                </Typography>
              </Box>
            </Tooltip>
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
                    onClick={handleDisablePrivateAccess}
                  >
                    <NoAccountsOutlinedIcon sx={{ color: "text.secondary" }} />
                  </Box>
                </Tooltip>
              </>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <AddRecipeModal
        open={isAddRecipeModalOpen}
        onClose={() => setIsAddRecipeModalOpen(false)}
      />

      <PantryDrawer
        open={isPantryOpen}
        onClose={() => setIsPantryOpen(false)}
      />
    </>
  );
};

export default Navigation;
