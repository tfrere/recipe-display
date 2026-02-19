import React, { useState, useMemo, useCallback } from "react";
import {
  Box,
  Typography,
  Drawer,
  IconButton,
  Checkbox,
  Chip,
  Snackbar,
  Switch,
  FormControlLabel,
  LinearProgress,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import KitchenOutlinedIcon from "@mui/icons-material/KitchenOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import {
  buildShoppingList,
  formatQuantity,
  shoppingListToText,
} from "./utils/mealPlannerUtils";
import { usePantry } from "../../../contexts/PantryContext";

const ShoppingListDrawer = ({ open, onClose, planItems, servingsPerMeal }) => {
  const [checkedItems, setCheckedItems] = useState(new Set());
  const [copySnackbar, setCopySnackbar] = useState(false);
  const [hidePantryItems, setHidePantryItems] = useState(false);
  const { hasItem, pantrySize } = usePantry();

  const shoppingGroups = useMemo(
    () => buildShoppingList(planItems, servingsPerMeal),
    [planItems, servingsPerMeal]
  );

  const totalItems = useMemo(
    () => shoppingGroups.reduce((acc, g) => acc + g.items.length, 0),
    [shoppingGroups]
  );

  const pantryItemCount = useMemo(() => {
    if (pantrySize === 0) return 0;
    let count = 0;
    for (const group of shoppingGroups) {
      for (const item of group.items) {
        if (hasItem(item.name_en)) count++;
      }
    }
    return count;
  }, [shoppingGroups, hasItem, pantrySize]);

  const checkedCount = checkedItems.size + (hidePantryItems ? 0 : pantryItemCount);
  const progressPct = totalItems > 0 ? (checkedCount / totalItems) * 100 : 0;

  const toggleItem = useCallback((itemName) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemName)) {
        next.delete(itemName);
      } else {
        next.add(itemName);
      }
      return next;
    });
  }, []);

  const toggleGroup = useCallback((group) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      const allChecked = group.items.every((item) => next.has(item.name));
      for (const item of group.items) {
        if (allChecked) {
          next.delete(item.name);
        } else {
          next.add(item.name);
        }
      }
      return next;
    });
  }, []);

  const handleCopy = useCallback(async () => {
    const text = shoppingListToText(shoppingGroups);
    try {
      await navigator.clipboard.writeText(text);
      setCopySnackbar(true);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopySnackbar(true);
    }
  }, [shoppingGroups]);

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        PaperProps={{
          sx: {
            width: { xs: "100%", sm: 420 },
            maxWidth: "100vw",
            display: "flex",
            flexDirection: "column",
          },
        }}
      >
        {/* ── Sticky header ── */}
        <Box
          sx={{
            p: 2,
            pb: 1.5,
            borderBottom: "1px solid",
            borderColor: "divider",
            position: "sticky",
            top: 0,
            bgcolor: "background.paper",
            zIndex: 1,
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1.5,
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              Shopping List
            </Typography>
            <IconButton size="small" onClick={onClose}>
              <CloseIcon sx={{ fontSize: "1.2rem" }} />
            </IconButton>
          </Box>

          {/* Progress bar */}
          <Box sx={{ mb: 1 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
                {checkedCount} of {totalItems} items
              </Typography>
              {checkedCount === totalItems && totalItems > 0 && (
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <CheckCircleOutlineIcon sx={{ fontSize: "0.85rem", color: "success.main" }} />
                  <Typography variant="caption" sx={{ color: "success.main", fontWeight: 600, fontSize: "0.75rem" }}>
                    All done
                  </Typography>
                </Box>
              )}
            </Box>
            <LinearProgress
              variant="determinate"
              value={progressPct}
              sx={{
                height: 4,
                borderRadius: 2,
                bgcolor: (theme) =>
                  theme.palette.mode === "dark" ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
                "& .MuiLinearProgress-bar": {
                  borderRadius: 2,
                  bgcolor: progressPct === 100 ? "success.main" : "text.primary",
                  transition: "width 0.3s ease, background-color 0.3s ease",
                },
              }}
            />
          </Box>

          {/* Pantry filter */}
          {pantrySize > 0 && pantryItemCount > 0 && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                pt: 0.5,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <KitchenOutlinedIcon sx={{ fontSize: "0.9rem", color: "text.secondary" }} />
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
                  {pantryItemCount} in your pantry
                </Typography>
              </Box>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={hidePantryItems}
                    onChange={(e) => setHidePantryItems(e.target.checked)}
                  />
                }
                label={
                  <Typography variant="caption" sx={{ fontSize: "0.7rem" }}>
                    Hide
                  </Typography>
                }
                labelPlacement="start"
                sx={{ m: 0, gap: 0.5 }}
              />
            </Box>
          )}
        </Box>

        {/* ── Shopping list content ── */}
        <Box sx={{ px: 2, py: 1, overflowY: "auto", flex: 1 }}>
          {shoppingGroups.length === 0 ? (
            <Box sx={{ py: 4, textAlign: "center" }}>
              <Typography color="text.secondary">
                No ingredients to display. Recipe details may not be loaded.
              </Typography>
            </Box>
          ) : (
            shoppingGroups.map((group) => {
              const visibleItems = hidePantryItems
                ? group.items.filter((item) => !hasItem(item.name_en))
                : group.items;

              if (visibleItems.length === 0) return null;

              const allGroupChecked = group.items.every(
                (item) => checkedItems.has(item.name) || (pantrySize > 0 && hasItem(item.name_en))
              );

              return (
                <Box key={group.category} sx={{ mb: 2 }}>
                  {/* Category header — clickable to toggle group */}
                  <Box
                    onClick={() => toggleGroup(group)}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      mb: 0.5,
                      mt: 1,
                      py: 0.5,
                      px: 0.5,
                      cursor: "pointer",
                      borderRadius: 1,
                      userSelect: "none",
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                  >
                    <Typography sx={{ fontSize: 16 }}>{group.emoji}</Typography>
                    <Typography
                      variant="overline"
                      sx={{
                        fontWeight: 700,
                        letterSpacing: 1.2,
                        color: allGroupChecked ? "text.disabled" : "text.secondary",
                        textDecoration: allGroupChecked ? "line-through" : "none",
                        fontSize: "0.65rem",
                        lineHeight: 1,
                      }}
                    >
                      {group.category}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.disabled", fontSize: "0.65rem", ml: -0.5 }}
                    >
                      ({visibleItems.length})
                    </Typography>
                  </Box>

                  {/* Items */}
                  {visibleItems.map((item) => {
                    const isChecked = checkedItems.has(item.name);
                    const isInPantry = pantrySize > 0 && hasItem(item.name_en);
                    const qty = formatQuantity(item.quantity, item.unit);
                    const isDone = isChecked || isInPantry;

                    return (
                      <Box
                        key={item.name}
                        onClick={() => toggleItem(item.name)}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          py: 0.6,
                          px: 0.5,
                          cursor: "pointer",
                          borderRadius: 1,
                          transition: "all 0.15s",
                          opacity: isDone ? 0.5 : 1,
                          "&:hover": {
                            bgcolor: "action.hover",
                          },
                        }}
                      >
                        <Checkbox
                          size="small"
                          checked={isDone}
                          sx={{ p: 0.5, mr: 1 }}
                          tabIndex={-1}
                        />
                        <Typography
                          variant="body2"
                          sx={{
                            flex: 1,
                            textDecoration: isDone ? "line-through" : "none",
                            color: isDone ? "text.disabled" : "text.primary",
                            transition: "all 0.15s",
                            fontSize: "0.9rem",
                          }}
                        >
                          {item.name}
                        </Typography>
                        {isInPantry && (
                          <Chip
                            label="pantry"
                            size="small"
                            variant="outlined"
                            sx={{
                              height: 20,
                              fontSize: "0.6rem",
                              fontWeight: 600,
                              ml: 0.5,
                              borderColor: "success.main",
                              color: "success.main",
                              "& .MuiChip-label": { px: 0.75 },
                            }}
                          />
                        )}
                        {qty && (
                          <Typography
                            variant="body2"
                            sx={{
                              color: isDone ? "text.disabled" : "text.secondary",
                              fontWeight: 500,
                              ml: 1,
                              whiteSpace: "nowrap",
                              fontSize: "0.85rem",
                            }}
                          >
                            {qty}
                          </Typography>
                        )}
                      </Box>
                    );
                  })}
                </Box>
              );
            })
          )}
        </Box>

        {/* ── Sticky footer ── */}
        <Box
          sx={{
            p: 2,
            borderTop: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: "0.85rem" }}>
            {totalItems} item{totalItems !== 1 ? "s" : ""}
            {pantryItemCount > 0 && ` · ${pantryItemCount} in pantry`}
          </Typography>
          <IconButton
            size="small"
            onClick={handleCopy}
            title="Copy to clipboard"
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
              px: 1.5,
              gap: 0.5,
            }}
          >
            <ContentCopyIcon sx={{ fontSize: "0.9rem" }} />
            <Typography variant="caption" sx={{ fontWeight: 600, fontSize: "0.75rem" }}>
              Copy
            </Typography>
          </IconButton>
        </Box>
      </Drawer>

      <Snackbar
        open={copySnackbar}
        autoHideDuration={2000}
        onClose={() => setCopySnackbar(false)}
        message="Shopping list copied to clipboard"
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      />
    </>
  );
};

export default ShoppingListDrawer;
