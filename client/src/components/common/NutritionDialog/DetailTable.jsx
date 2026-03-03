import React, { useState } from "react";
import { Box, Typography, ToggleButtonGroup, ToggleButton } from "@mui/material";
import { MACRO_COLORS, UNRESOLVED_KEYS, formatQty, roundCalories, pctDV } from "./constants";

const COL_SX = {
  fontSize: "0.7rem",
  fontVariantNumeric: "tabular-nums",
  textAlign: "right",
  whiteSpace: "nowrap",
};

const HeaderCell = ({ children, color, align = "right", flex }) => (
  <Typography sx={{
    fontSize: "0.62rem",
    fontWeight: 600,
    color: color || "text.disabled",
    textTransform: "uppercase",
    letterSpacing: "0.03em",
    textAlign: align,
    flex,
    minWidth: 0,
  }}>
    {children}
  </Typography>
);

const MacroStat = ({ label, value, unit = "g", color, showDV = true }) => {
  const dv = showDV ? pctDV(value, label.toLowerCase()) : null;
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
      <Typography sx={{ fontSize: "1.15rem", fontWeight: 700, color: "text.primary", lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>
        {Math.round(value)}<Typography component="span" sx={{ fontSize: "0.7rem", fontWeight: 400, color: "text.secondary" }}>{unit}</Typography>
      </Typography>
      <Typography sx={{ fontSize: "0.65rem", fontWeight: 500, color, lineHeight: 1.4 }}>
        {label}
      </Typography>
      {dv != null && (
        <Typography sx={{ fontSize: "0.55rem", color: "text.disabled", lineHeight: 1.2 }}>
          {dv}% DV
        </Typography>
      )}
    </Box>
  );
};

const DetailTable = ({
  resolvedDetails,
  unresolvedDetails,
  servings,
  totalIngredients,
  resolvedIngredients,
  negligibleIngredients,
  confidence,
  t,
}) => {
  const [mode, setMode] = useState("serving");
  const s = servings && servings > 0 ? servings : 1;
  const divisor = mode === "serving" ? s : 1;

  const totals = resolvedDetails.reduce(
    (acc, d) => ({
      calories: acc.calories + d.calories / divisor,
      protein: acc.protein + (d.protein || 0) / divisor,
      carbs: acc.carbs + (d.carbs || 0) / divisor,
      fat: acc.fat + (d.fat || 0) / divisor,
      fiber: acc.fiber + (d.fiber || 0) / divisor,
    }),
    { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 }
  );

  const calFromProtein = totals.protein * 4;
  const calFromCarbs = totals.carbs * 4;
  const calFromFat = totals.fat * 9;
  const calTotal = calFromProtein + calFromCarbs + calFromFat || 1;
  const pctProtein = Math.round((calFromProtein / calTotal) * 100);
  const pctCarbs = Math.round((calFromCarbs / calTotal) * 100);
  const pctFat = 100 - pctProtein - pctCarbs;

  const columns = [
    { key: "name", label: t("recipe.ingredients"), align: "left", flex: "1 1 0" },
    { key: "qty", label: "Qty", align: "right", flex: "0 0 72px" },
    { key: "kcal", label: "kcal", align: "right", flex: "0 0 44px" },
    { key: "protein", label: t("nutrition.macroProtein"), color: MACRO_COLORS.protein, align: "right", flex: "0 0 56px" },
    { key: "carbs", label: t("nutrition.macroCarbs"), color: MACRO_COLORS.carbs, align: "right", flex: "0 0 56px" },
    { key: "fat", label: t("nutrition.macroFat"), color: MACRO_COLORS.fat, align: "right", flex: "0 0 56px" },
    { key: "fiber", label: t("nutrition.macroFiber"), color: MACRO_COLORS.fiber, align: "right", flex: "0 0 56px" },
  ];

  const fmtVal = (v) => {
    if (v == null || v === 0) return "—";
    const rounded = Math.round(v * 10) / 10;
    return rounded < 0.1 ? "<0.1" : rounded;
  };

  return (
    <Box>
      {/* ── Summary dashboard ── */}
      <Box sx={{
        display: "flex",
        alignItems: "center",
        gap: 3,
        mb: 3,
        py: 2,
        px: 2.5,
        borderRadius: 2,
        bgcolor: "action.hover",
      }}>
        {/* Calories */}
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", pr: 3, borderRight: "1px solid", borderColor: "divider" }}>
          <Typography sx={{ fontWeight: 800, fontSize: "2rem", lineHeight: 1, color: "text.primary", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>
            ~{roundCalories(totals.calories)}
          </Typography>
          <Typography sx={{ fontSize: "0.65rem", color: "text.disabled", mt: 0.25 }}>
            {mode === "serving" ? t("nutrition.kcalPerServing") : "kcal"}
          </Typography>
          {s > 1 && (
            <Typography sx={{ fontSize: "0.52rem", color: "text.disabled", mt: 0.25, opacity: 0.7 }}>
              {t("nutrition.servingsCount", { count: s })}
            </Typography>
          )}
        </Box>

        {/* Macros */}
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 1.5 }}>
          {/* Macro stats row */}
          <Box sx={{ display: "flex" }}>
            <MacroStat label={t("nutrition.macroProtein")} value={totals.protein} color={MACRO_COLORS.protein} showDV={mode === "serving"} />
            <MacroStat label={t("nutrition.macroCarbs")} value={totals.carbs} color={MACRO_COLORS.carbs} showDV={mode === "serving"} />
            <MacroStat label={t("nutrition.macroFat")} value={totals.fat} color={MACRO_COLORS.fat} showDV={mode === "serving"} />
            <MacroStat label={t("nutrition.macroFiber")} value={totals.fiber} color={MACRO_COLORS.fiber} showDV={mode === "serving"} />
          </Box>

          {/* Caloric distribution bar */}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            <Box sx={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden" }}>
              <Box sx={{ width: `${pctProtein}%`, bgcolor: MACRO_COLORS.protein, transition: "width 0.3s ease" }} />
              <Box sx={{ width: `${pctCarbs}%`, bgcolor: MACRO_COLORS.carbs, transition: "width 0.3s ease" }} />
              <Box sx={{ width: `${pctFat}%`, bgcolor: MACRO_COLORS.fat, transition: "width 0.3s ease" }} />
            </Box>
            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
              <Typography sx={{ fontSize: "0.55rem", color: "text.disabled" }}>{pctProtein}%</Typography>
              <Typography sx={{ fontSize: "0.55rem", color: "text.disabled" }}>{pctCarbs}%</Typography>
              <Typography sx={{ fontSize: "0.55rem", color: "text.disabled" }}>{pctFat}%</Typography>
            </Box>
          </Box>
        </Box>
      </Box>

      {/* ── Toggle + section title ── */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Typography sx={{
          fontSize: "0.7rem", fontWeight: 600, color: "text.secondary",
          textTransform: "uppercase", letterSpacing: "0.03em",
        }}>
          {t("nutrition.calorieBreakdown")}
        </Typography>
        {s > 1 && (
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_, v) => { if (v) setMode(v); }}
            size="small"
            sx={{ height: 24 }}
          >
            <ToggleButton value="serving" sx={{
              textTransform: "none", fontSize: "0.62rem", fontWeight: 500,
              px: 1.25, py: 0, lineHeight: 1.4, borderRadius: "6px 0 0 6px !important",
              borderColor: "divider",
              "&.Mui-selected": { bgcolor: "action.selected", color: "text.primary", fontWeight: 600 },
            }}>
              {t("nutrition.viewPerServing")}
            </ToggleButton>
            <ToggleButton value="total" sx={{
              textTransform: "none", fontSize: "0.62rem", fontWeight: 500,
              px: 1.25, py: 0, lineHeight: 1.4, borderRadius: "0 6px 6px 0 !important",
              borderColor: "divider",
              "&.Mui-selected": { bgcolor: "action.selected", color: "text.primary", fontWeight: 600 },
            }}>
              {t("nutrition.viewTotalRecipe")}
            </ToggleButton>
          </ToggleButtonGroup>
        )}
      </Box>

      {/* Header row */}
      <Box sx={{
        display: "flex", gap: 1, px: 1, pb: 0.75,
        borderBottom: "1px solid", borderColor: "divider",
      }}>
        {columns.map((col) => (
          <HeaderCell key={col.key} color={col.color} align={col.align} flex={col.flex}>
            {col.label}
          </HeaderCell>
        ))}
      </Box>

      {/* Scrollable body */}
      <Box sx={{
        maxHeight: 320,
        overflowY: "auto",
        overflowX: "hidden",
        "&::-webkit-scrollbar": { width: 3 },
        "&::-webkit-scrollbar-thumb": { bgcolor: "divider", borderRadius: 2 },
      }}>
        {resolvedDetails.map((d, i) => {
          const cal = Math.round(d.calories / divisor);
          const prot = (d.protein || 0) / divisor;
          const carb = (d.carbs || 0) / divisor;
          const f = (d.fat || 0) / divisor;
          const fib = (d.fiber || 0) / divisor;
          const pctOfTotal = totals.calories > 0 ? Math.round((d.calories / divisor / totals.calories) * 100) : 0;

          return (
            <Box
              key={`r${i}`}
              sx={{
                display: "flex", gap: 1, px: 1, py: 0.6,
                borderBottom: "1px solid", borderColor: "divider",
                "&:hover": { bgcolor: "action.hover" },
                transition: "background-color 0.1s ease",
                position: "relative",
              }}
            >
              {/* Subtle calorie proportion bar behind the row */}
              <Box sx={{
                position: "absolute", left: 0, top: 0, bottom: 0,
                width: `${pctOfTotal}%`,
                bgcolor: "action.hover",
                opacity: 0.5,
                borderRadius: 0.5,
                pointerEvents: "none",
              }} />
              {/* Name */}
              <Box sx={{ flex: "1 1 0", minWidth: 0, position: "relative" }}>
                <Typography sx={{
                  fontSize: "0.73rem", fontWeight: 500, color: "text.primary",
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                }}>
                  {d.name}
                </Typography>
              </Box>
              {/* Qty */}
              <Typography sx={{ ...COL_SX, flex: "0 0 72px", color: "text.disabled", fontSize: "0.65rem", position: "relative" }}>
                {formatQty(d.quantity != null ? d.quantity / divisor : null, d.unit, d.grams != null ? d.grams / divisor : null)}
              </Typography>
              {/* kcal */}
              <Typography sx={{ ...COL_SX, flex: "0 0 44px", fontWeight: 600, color: "text.primary", position: "relative" }}>
                {cal}
              </Typography>
              {/* Macros */}
              <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.secondary", position: "relative" }}>{fmtVal(prot)}</Typography>
              <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.secondary", position: "relative" }}>{fmtVal(carb)}</Typography>
              <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.secondary", position: "relative" }}>{fmtVal(f)}</Typography>
              <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.secondary", position: "relative" }}>{fmtVal(fib)}</Typography>
            </Box>
          );
        })}

        {/* Unresolved ingredients */}
        {unresolvedDetails.map((d, i) => (
          <Box
            key={`u${i}`}
            sx={{
              display: "flex", gap: 1, px: 1, py: 0.6,
              borderBottom: "1px solid", borderColor: "divider",
            }}
          >
            <Box sx={{ flex: "1 1 0", minWidth: 0 }}>
              <Typography sx={{
                fontSize: "0.73rem", fontWeight: 400, color: "text.disabled", fontStyle: "italic",
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}>
                {d.name}
              </Typography>
            </Box>
            <Typography sx={{ ...COL_SX, flex: "0 0 72px", color: "text.disabled", fontStyle: "italic", fontSize: "0.62rem" }}>
              {UNRESOLVED_KEYS[d.status] ? t(UNRESOLVED_KEYS[d.status]) : "—"}
            </Typography>
            <Typography sx={{ ...COL_SX, flex: "0 0 44px", color: "text.disabled" }}>—</Typography>
            <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.disabled" }}>—</Typography>
            <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.disabled" }}>—</Typography>
            <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.disabled" }}>—</Typography>
            <Typography sx={{ ...COL_SX, flex: "0 0 56px", color: "text.disabled" }}>—</Typography>
          </Box>
        ))}
      </Box>

      {/* Totals row */}
      <Box sx={{
        display: "flex", gap: 1, px: 1, pt: 1, mt: 0.5,
        borderTop: "2px solid", borderColor: "divider",
      }}>
        <Typography sx={{ flex: "1 1 0", fontSize: "0.73rem", fontWeight: 700, color: "text.primary" }}>
          {t("nutrition.total")}
        </Typography>
        <Typography sx={{ ...COL_SX, flex: "0 0 72px" }}>{""}</Typography>
        <Typography sx={{ ...COL_SX, flex: "0 0 44px", fontWeight: 700, color: "text.primary" }}>
          ~{Math.round(totals.calories)}
        </Typography>
        <Typography sx={{ ...COL_SX, flex: "0 0 56px", fontWeight: 600, color: MACRO_COLORS.protein }}>
          {Math.round(totals.protein)}g
        </Typography>
        <Typography sx={{ ...COL_SX, flex: "0 0 56px", fontWeight: 600, color: MACRO_COLORS.carbs }}>
          {Math.round(totals.carbs)}g
        </Typography>
        <Typography sx={{ ...COL_SX, flex: "0 0 56px", fontWeight: 600, color: MACRO_COLORS.fat }}>
          {Math.round(totals.fat)}g
        </Typography>
        <Typography sx={{ ...COL_SX, flex: "0 0 56px", fontWeight: 600, color: MACRO_COLORS.fiber }}>
          {Math.round(totals.fiber)}g
        </Typography>
      </Box>

      <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.6rem", mt: 1, display: "block", px: 1 }}>
        {t("nutrition.basedOn", { resolved: resolvedIngredients, total: totalIngredients })}
        {negligibleIngredients > 0 && ` · ${t("nutrition.seasoningsExcluded", { count: negligibleIngredients })}`}
      </Typography>
    </Box>
  );
};

export default DetailTable;
