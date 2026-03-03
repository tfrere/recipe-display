import React from "react";
import { Box, Typography } from "@mui/material";
import { MINERAL_COLORS, MINERAL_UNITS, pctDV } from "./constants";

const MineralsSection = ({ minerals, t }) => {
  if (!minerals) return null;

  const items = [
    { key: "calcium", labelKey: "nutrition.mineralCalcium", value: minerals.calcium, color: MINERAL_COLORS.calcium },
    { key: "iron", labelKey: "nutrition.mineralIron", value: minerals.iron, color: MINERAL_COLORS.iron },
    { key: "magnesium", labelKey: "nutrition.mineralMagnesium", value: minerals.magnesium, color: MINERAL_COLORS.magnesium },
    { key: "potassium", labelKey: "nutrition.mineralPotassium", value: minerals.potassium, color: MINERAL_COLORS.potassium },
    { key: "zinc", labelKey: "nutrition.mineralZinc", value: minerals.zinc, color: MINERAL_COLORS.zinc },
  ].filter((m) => m.value != null && m.value > 0);

  if (items.length === 0) return null;

  const formatValue = (key, value) => {
    if (key === "iron" || key === "zinc") return Math.round(value * 100) / 100;
    return Math.round(value);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography sx={{
        fontSize: "0.7rem", fontWeight: 600, color: "text.secondary",
        textTransform: "uppercase", letterSpacing: "0.03em",
      }}>
        {t("nutrition.mineralsSection")}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
      {items.map((m) => {
        const dv = pctDV(m.value, m.key);
        return (
          <Box
            key={m.key}
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              flex: 1,
              px: 1.25,
              py: 0.75,
              borderRadius: 1.5,
              border: "1px solid",
              borderColor: "divider",
              minWidth: 56,
            }}
          >
            <Typography sx={{ fontSize: "0.65rem", color: "text.secondary", lineHeight: 1.2 }}>
              {t(m.labelKey)}
            </Typography>
            <Typography sx={{ fontSize: "0.78rem", fontWeight: 600, color: "text.primary", lineHeight: 1.3, fontVariantNumeric: "tabular-nums" }}>
              {formatValue(m.key, m.value)}{MINERAL_UNITS[m.key]}
            </Typography>
            {dv != null && (
              <Typography sx={{ fontSize: "0.58rem", color: "text.disabled", lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>
                {dv}% DV
              </Typography>
            )}
          </Box>
        );
      })}
      </Box>
    </Box>
  );
};

export default MineralsSection;
