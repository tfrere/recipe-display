import React, { useState, useMemo, useCallback } from "react";
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  TextField,
  InputAdornment,
  Chip,
  Button,
  Divider,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import DeleteSweepOutlinedIcon from "@mui/icons-material/DeleteSweepOutlined";
import { usePantry } from "../../contexts/PantryContext";

const PANTRY_CATEGORIES = [
  {
    id: "spices",
    label: "Spices",
    items: [
      "salt",
      "pepper",
      "cumin",
      "paprika",
      "smoked paprika",
      "curry",
      "cinnamon",
      "nutmeg",
      "turmeric",
      "piment d'Espelette",
      "cayenne",
      "ginger",
      "ras el hanout",
      "allspice",
      "sumac",
      "coriander seeds",
      "cardamom",
      "za'atar",
      "chili",
      "saffron",
      "fenugreek",
      "caraway",
      "star anise",
      "five spice",
      "garam masala",
      "tandoori",
      "chipotle",
    ],
  },
  {
    id: "herbs",
    label: "Dried herbs",
    items: [
      "thyme",
      "rosemary",
      "oregano",
      "herbes de Provence",
      "bay leaf",
      "sage",
    ],
  },
  {
    id: "oils",
    label: "Oils & fats",
    items: [
      "olive oil",
      "sunflower oil",
      "sesame oil",
      "toasted sesame oil",
      "butter",
      "ghee",
      "coconut oil",
      "rapeseed oil",
      "peanut oil",
      "walnut oil",
      "grapeseed oil",
      "lard",
    ],
  },
  {
    id: "condiments",
    label: "Condiments & sauces",
    items: [
      "mustard",
      "Dijon mustard",
      "soy sauce",
      "balsamic vinegar",
      "cider vinegar",
      "wine vinegar",
      "rice vinegar",
      "honey",
      "Tabasco",
      "Worcestershire",
      "tomato paste",
      "fish sauce",
      "tahini",
      "harissa",
      "sriracha",
      "miso",
      "oyster sauce",
      "curry paste",
      "sambal oelek",
      "maple syrup",
      "teriyaki",
    ],
  },
  {
    id: "dry-goods",
    label: "Dry goods & baking",
    items: [
      "all-purpose flour",
      "whole wheat flour",
      "almond flour",
      "chickpea flour",
      "rice flour",
      "cornmeal",
      "sugar",
      "brown sugar",
      "cornstarch",
      "breadcrumbs",
      "yeast",
      "baking soda",
      "lentils",
      "red lentils",
      "chickpeas",
      "oats",
      "flax seeds",
      "chia seeds",
      "sesame seeds",
      "peanuts",
      "cashews",
      "almonds",
      "pine nuts",
      "raisins",
      "coconut",
      "cocoa",
      "dark chocolate",
    ],
  },
  {
    id: "pasta-rice",
    label: "Pasta, rice & grains",
    items: [
      "spaghetti",
      "penne",
      "fusilli",
      "tagliatelle",
      "linguine",
      "farfalle",
      "rigatoni",
      "lasagna",
      "rice noodles",
      "udon",
      "soba",
      "vermicelli",
      "basmati rice",
      "jasmine rice",
      "arborio rice",
      "brown rice",
      "semolina",
      "bulgur",
      "quinoa",
      "polenta",
      "couscous",
    ],
  },
  {
    id: "canned",
    label: "Canned & jarred",
    items: [
      "coconut milk",
      "peeled tomatoes",
      "crushed tomatoes",
      "stock cubes",
      "coconut cream",
      "canned chickpeas",
      "canned kidney beans",
      "canned tuna",
      "sardines",
      "anchovies",
      "capers",
      "olives",
      "pickles",
    ],
  },
];

const DRAWER_WIDTH = 420;

const CategorySection = ({ category, hasExactItem, toggleItem }) => {
  return (
    <Box sx={{ mb: 2.5 }}>
      <Typography
        variant="overline"
        sx={{
          color: "text.secondary",
          fontWeight: 600,
          letterSpacing: 1.2,
          fontSize: "0.65rem",
          lineHeight: 1,
          mb: 1,
        }}
      >
        {category.label}
      </Typography>
      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
        {category.items.map((item) => {
          const isActive = hasExactItem(item);
          return (
            <Chip
              key={item}
              label={item}
              size="small"
              onClick={() => toggleItem(item)}
              variant={isActive ? "filled" : "outlined"}
              sx={{
                fontWeight: isActive ? 600 : 400,
                fontSize: "0.78rem",
                borderRadius: "8px",
                height: 30,
                cursor: "pointer",
                transition: "all 0.15s ease",
                ...(isActive
                  ? {
                      bgcolor: "text.primary",
                      color: "background.paper",
                      "&:hover": {
                        bgcolor: "text.primary",
                        opacity: 0.85,
                        transform: "scale(1.03)",
                      },
                    }
                  : {
                      borderColor: "divider",
                      color: "text.secondary",
                      "&:hover": {
                        bgcolor: (theme) =>
                          theme.palette.mode === "dark"
                            ? "rgba(255,255,255,0.08)"
                            : "rgba(0,0,0,0.04)",
                        transform: "scale(1.03)",
                      },
                    }),
              }}
            />
          );
        })}
      </Box>
    </Box>
  );
};

const PantryDrawer = ({ open, onClose }) => {
  const { pantryItems, pantrySize, hasExactItem, toggleItem, addItem, removeItem } =
    usePantry();
  const [customInput, setCustomInput] = useState("");

  const allSuggested = useMemo(() => {
    const set = new Set();
    PANTRY_CATEGORIES.forEach((cat) =>
      cat.items.forEach((item) => set.add(item.toLowerCase()))
    );
    return set;
  }, []);

  const customItems = useMemo(() => {
    return pantryItems.filter(
      (item) => !allSuggested.has(item.toLowerCase())
    );
  }, [pantryItems, allSuggested]);

  const handleAddCustom = useCallback(() => {
    const trimmed = customInput.trim();
    if (!trimmed) return;
    addItem(trimmed);
    setCustomInput("");
  }, [customInput, addItem]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAddCustom();
      }
    },
    [handleAddCustom]
  );

  const handleClearAll = useCallback(() => {
    pantryItems.forEach((item) => removeItem(item));
  }, [pantryItems, removeItem]);

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: "100%", sm: DRAWER_WIDTH },
          maxWidth: "100vw",
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2.5,
            py: 2,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <KitchenOutlinedIcon sx={{ color: "text.primary" }} />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                My Pantry
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {pantrySize === 0
                  ? "Add items you always have at home"
                  : `${pantrySize} item${pantrySize !== 1 ? "s" : ""} in your pantry`}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Custom item input */}
        <Box sx={{ px: 2.5, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Add a custom item..."
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            onKeyDown={handleKeyDown}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <AddIcon sx={{ fontSize: "1.1rem", color: "text.disabled" }} />
                </InputAdornment>
              ),
              endAdornment: customInput.trim() && (
                <InputAdornment position="end">
                  <Button
                    size="small"
                    onClick={handleAddCustom}
                    sx={{
                      minWidth: 0,
                      textTransform: "none",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      borderRadius: "6px",
                      px: 1.5,
                    }}
                  >
                    Add
                  </Button>
                </InputAdornment>
              ),
              sx: {
                borderRadius: "8px",
                fontSize: "0.85rem",
              },
            }}
          />
        </Box>

        {/* Scrollable body */}
        <Box
          sx={{
            flex: 1,
            overflow: "auto",
            px: 2.5,
            py: 2,
          }}
        >
          {PANTRY_CATEGORIES.map((category) => (
            <CategorySection
              key={category.id}
              category={category}
              hasExactItem={hasExactItem}
              toggleItem={toggleItem}
            />
          ))}

          {/* Custom items section */}
          {customItems.length > 0 && (
            <Box sx={{ mb: 2.5 }}>
              <Typography
                variant="overline"
                sx={{
                  color: "text.secondary",
                  fontWeight: 600,
                  letterSpacing: 1.2,
                  fontSize: "0.65rem",
                  lineHeight: 1,
                  mb: 1,
                }}
              >
                Custom items
              </Typography>
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {customItems.map((item) => (
                  <Chip
                    key={item}
                    label={item}
                    size="small"
                    onDelete={() => removeItem(item)}
                    deleteIcon={
                      <CloseIcon sx={{ fontSize: "0.8rem !important" }} />
                    }
                    sx={{
                      fontWeight: 600,
                      fontSize: "0.78rem",
                      borderRadius: "8px",
                      height: 30,
                      bgcolor: "text.primary",
                      color: "background.paper",
                      "& .MuiChip-deleteIcon": {
                        color: "background.paper",
                        opacity: 0.7,
                        "&:hover": { opacity: 1 },
                      },
                    }}
                  />
                ))}
              </Box>
            </Box>
          )}
        </Box>

        {/* Footer */}
        {pantrySize > 0 && (
          <Box
            sx={{
              px: 2.5,
              py: 1.5,
              borderTop: "1px solid",
              borderColor: "divider",
              display: "flex",
              justifyContent: "flex-end",
            }}
          >
            <Button
              size="small"
              color="error"
              startIcon={<DeleteSweepOutlinedIcon />}
              onClick={handleClearAll}
              sx={{
                textTransform: "none",
                fontSize: "0.8rem",
                fontWeight: 500,
              }}
            >
              Clear all
            </Button>
          </Box>
        )}
      </Box>
    </Drawer>
  );
};

export default PantryDrawer;
