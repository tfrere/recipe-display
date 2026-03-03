import React from "react";
import { Box, Typography } from "@mui/material";
import { MACRO_COLORS, formatMacro } from "./constants";

const MacroBar = ({ label, value, pct, color, confidence, unit = "g" }) => (
  <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
    <Box sx={{ width: 7, height: 7, borderRadius: "50%", bgcolor: color, flexShrink: 0 }} />
    <Typography sx={{ fontSize: "0.78rem", color: "text.secondary", minWidth: 52, fontWeight: 500 }}>
      {label}
    </Typography>
    <Box sx={{ flex: 1, height: 8, borderRadius: 4, bgcolor: "action.hover", overflow: "hidden" }}>
      <Box sx={{
        width: `${Math.min(pct, 100)}%`,
        height: "100%",
        borderRadius: 4,
        bgcolor: color,
        opacity: confidence === "low" ? 0.4 : 0.85,
        transition: "width 0.4s ease",
      }} />
    </Box>
    <Typography sx={{
      fontSize: "0.78rem", fontWeight: 600, color: "text.primary",
      minWidth: 36, textAlign: "right", fontVariantNumeric: "tabular-nums",
    }}>
      {formatMacro(value, confidence)}{unit}
    </Typography>
    <Typography sx={{
      fontSize: "0.68rem", color: "text.disabled",
      minWidth: 28, textAlign: "right", fontVariantNumeric: "tabular-nums",
    }}>
      {pct}%
    </Typography>
  </Box>
);

const MacroBars = ({ protein, carbs, fat, calories, confidence, t }) => {
  const totalCal = calories || 1;
  const pctProtein = Math.round((protein * 4 / totalCal) * 100);
  const pctCarbs = Math.round((carbs * 4 / totalCal) * 100);
  const pctFat = Math.round((fat * 9 / totalCal) * 100);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, width: "100%" }}>
      <MacroBar
        label={t("nutrition.macroProtein")}
        value={protein} pct={pctProtein}
        color={MACRO_COLORS.protein} confidence={confidence}
      />
      <MacroBar
        label={t("nutrition.macroCarbs")}
        value={carbs} pct={pctCarbs}
        color={MACRO_COLORS.carbs} confidence={confidence}
      />
      <MacroBar
        label={t("nutrition.macroFat")}
        value={fat} pct={pctFat}
        color={MACRO_COLORS.fat} confidence={confidence}
      />
    </Box>
  );
};

export default MacroBars;
