import React, { useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
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
import useLocalStorage from "../../../hooks/useLocalStorage";

const ShoppingListDrawer = ({ open, onClose, planItems, servingsPerMeal }) => {
  const { t } = useTranslation();
  const [checkedItems, setCheckedItems] = useState(new Set());
  const [copySnackbar, setCopySnackbar] = useState(false);
  const [hidePantryItems, setHidePantryItems] = useState(false);
  const { hasItem, pantrySize } = usePantry();
  const [unitSystem] = useLocalStorage("unit_system", "metric");

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

  const visibleTotal = hidePantryItems ? totalItems - pantryItemCount : totalItems;
  const checkedCount = hidePantryItems
    ? checkedItems.size
    : checkedItems.size + pantryItemCount;
  const progressPct = visibleTotal > 0 ? Math.min((checkedCount / visibleTotal) * 100, 100) : 0;

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
    const text = shoppingListToText(shoppingGroups, unitSystem);
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
              {t("mealPlanner.shoppingList")}
            </Typography>
            <IconButton size="small" onClick={onClose}>
              <CloseIcon sx={{ fontSize: "1.2rem" }} />
            </IconButton>
          </Box>

          {/* Progress bar */}
          <Box sx={{ mb: 1 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
                {t("mealPlanner.itemsProgress", { checked: checkedCount, total: visibleTotal })}
                {hidePantryItems && pantryItemCount > 0 && (
                  <Typography component="span" variant="caption" sx={{ color: "text.disabled", fontSize: "0.7rem" }}>
                    {" "}{t("mealPlanner.pantryHidden", { count: pantryItemCount })}
                  </Typography>
                )}
              </Typography>
              {checkedCount === visibleTotal && visibleTotal > 0 && (
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <CheckCircleOutlineIcon sx={{ fontSize: "0.85rem", color: "success.main" }} />
                  <Typography variant="caption" sx={{ color: "success.main", fontWeight: 600, fontSize: "0.75rem" }}>
                    {t("mealPlanner.allDone")}
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
                  {t("mealPlanner.inPantry", { count: pantryItemCount })}
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
                    {t("mealPlanner.hide")}
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
                {t("mealPlanner.noIngredients")}
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
                    const qty = formatQuantity(item.quantity, item.unit, unitSystem);
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
                            label={t("nav.pantry")}
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
            {t("mealPlanner.itemsToBuy", { count: visibleTotal })}
            {pantryItemCount > 0 && !hidePantryItems && ` ${t("mealPlanner.inPantryShort", { count: pantryItemCount })}`}
            {pantryItemCount > 0 && hidePantryItems && (
              <Typography component="span" variant="caption" sx={{ color: "text.disabled", fontSize: "0.75rem" }}>
                {" "}+ {t("mealPlanner.inPantry", { count: pantryItemCount })}
              </Typography>
            )}
          </Typography>
          <IconButton
            size="small"
            onClick={handleCopy}
            title={t("mealPlanner.copyToClipboard")}
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
              {t("mealPlanner.copy")}
            </Typography>
          </IconButton>
        </Box>
      </Drawer>

      <Snackbar
        open={copySnackbar}
        autoHideDuration={2000}
        onClose={() => setCopySnackbar(false)}
        message={t("mealPlanner.copySuccess")}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      />
    </>
  );
};

export default ShoppingListDrawer;
