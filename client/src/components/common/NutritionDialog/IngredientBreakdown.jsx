import React from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import { MACRO_COLORS, UNRESOLVED_KEYS, formatQty } from "./constants";

const IngredientRow = ({ d, servings, maxCal, totalCal, t, isLast }) => {
  const s = servings > 0 ? servings : 1;
  const cal = Math.round(d.calories / s);
  const barWidth = maxCal > 0 ? (d.calories / s / maxCal) * 100 : 0;

  const macroTip = [
    { labelKey: "nutrition.macroProtein", value: d.protein / s, color: MACRO_COLORS.protein, unit: "g" },
    { labelKey: "nutrition.macroCarbs", value: d.carbs / s, color: MACRO_COLORS.carbs, unit: "g" },
    { labelKey: "nutrition.macroFat", value: d.fat / s, color: MACRO_COLORS.fat, unit: "g" },
    { labelKey: "nutrition.macroFiber", value: d.fiber / s, color: MACRO_COLORS.fiber, unit: "g" },
    { labelKey: "nutrition.macroSugar", value: (d.sugar || 0) / s, color: MACRO_COLORS.sugar, unit: "g" },
    { labelKey: "nutrition.macroSaturatedFat", value: (d.saturatedFat || 0) / s, color: MACRO_COLORS.saturatedFat, unit: "g" },
  ];

  return (
    <Tooltip
      placement="left"
      enterDelay={200}
      arrow
      slotProps={{
        tooltip: { sx: { bgcolor: "grey.900", p: 1.25, maxWidth: 180, borderRadius: 1.5 } },
        arrow: { sx: { color: "grey.900" } },
      }}
      title={
        <Box>
          <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: "grey.100", mb: 0.75 }}>
            {d.name}
          </Typography>
          {macroTip.map((m) => (
            <Box key={m.labelKey} sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.25 }}>
              <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: m.color, flexShrink: 0 }} />
              <Typography sx={{ fontSize: "0.62rem", color: "grey.400", flex: 1 }}>
                {t(m.labelKey)}
              </Typography>
              <Typography sx={{ fontSize: "0.62rem", color: "grey.100", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                {Math.round(m.value * 10) / 10}{m.unit}
              </Typography>
            </Box>
          ))}
          {d.grams != null && (
            <Typography sx={{ fontSize: "0.58rem", color: "grey.500", mt: 0.5 }}>
              {Math.round(d.grams / s)}g {t("nutrition.perServing")}
            </Typography>
          )}
        </Box>
      }
    >
      <Box sx={{
        display: "flex", alignItems: "center", gap: 1,
        py: 0.6, px: 1,
        borderBottom: isLast ? "none" : "1px solid",
        borderColor: "divider",
        "&:hover": { bgcolor: "action.hover" },
        cursor: "default",
        transition: "background-color 0.15s ease",
      }}>
        <Box sx={{ flex: "0 0 35%", minWidth: 0 }}>
          <Typography sx={{
            fontSize: "0.75rem", fontWeight: 500, color: "text.primary",
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          }}>
            {d.name}
          </Typography>
          <Typography sx={{
            fontSize: "0.62rem", color: "text.disabled",
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          }}>
            {formatQty(d.quantity, d.unit, d.grams)}
          </Typography>
        </Box>
        <Box sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: "action.hover", overflow: "hidden", ml: 1 }}>
          <Box sx={{
            width: `${barWidth}%`, height: "100%", borderRadius: 3,
            bgcolor: "text.disabled",
            opacity: barWidth > 50 ? 0.45 : barWidth > 20 ? 0.3 : 0.18,
            transition: "width 0.3s ease",
          }} />
        </Box>
        <Typography sx={{
          fontSize: "0.72rem", fontWeight: 600, color: "text.primary",
          minWidth: 32, textAlign: "right", fontVariantNumeric: "tabular-nums", flexShrink: 0,
        }}>
          {cal}
        </Typography>
      </Box>
    </Tooltip>
  );
};

const UnresolvedRow = ({ d, t, isLast }) => (
  <Box sx={{
    display: "flex", alignItems: "center", gap: 1,
    py: 0.6, px: 1,
    borderBottom: isLast ? "none" : "1px solid",
    borderColor: "divider",
  }}>
    <Box sx={{ flex: 1, minWidth: 0 }}>
      <Typography sx={{
        fontSize: "0.75rem", fontWeight: 400, color: "text.disabled", fontStyle: "italic",
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
      }}>
        {d.name}
      </Typography>
    </Box>
    <Typography sx={{ fontSize: "0.62rem", color: "text.disabled", fontStyle: "italic", flexShrink: 0 }}>
      {UNRESOLVED_KEYS[d.status] ? t(UNRESOLVED_KEYS[d.status]) : "—"}
    </Typography>
  </Box>
);

const IngredientBreakdown = ({ resolvedDetails, unresolvedDetails, servings, totalIngredients, resolvedIngredients, negligibleIngredients, t }) => {
  const s = servings && servings > 0 ? servings : 1;
  const maxCal = Math.max(...resolvedDetails.map((d) => d.calories / s), 1);
  const totalCal = resolvedDetails.reduce((sum, d) => sum + d.calories, 0) / s;
  const allItems = [...resolvedDetails, ...unresolvedDetails];

  return (
    <Box>
      <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: "text.secondary", textTransform: "uppercase", letterSpacing: "0.03em", mb: 1, px: 1 }}>
        {t("nutrition.calorieBreakdown")}
      </Typography>
      <Box sx={{
        maxHeight: 340,
        overflowY: "auto",
        overflowX: "hidden",
        "&::-webkit-scrollbar": { width: 3 },
        "&::-webkit-scrollbar-thumb": { bgcolor: "divider", borderRadius: 2 },
      }}>
        {resolvedDetails.map((d, i) => (
          <IngredientRow
            key={`r${i}`} d={d}
            servings={s} maxCal={maxCal} totalCal={totalCal} t={t}
            isLast={i === resolvedDetails.length - 1 && unresolvedDetails.length === 0}
          />
        ))}
        {unresolvedDetails.map((d, i) => (
          <UnresolvedRow
            key={`u${i}`} d={d} t={t}
            isLast={i === unresolvedDetails.length - 1}
          />
        ))}
      </Box>

      <Box sx={{
        display: "flex", justifyContent: "space-between", alignItems: "baseline",
        px: 1, pt: 1, mt: 0.5,
        borderTop: "2px solid", borderColor: "divider",
      }}>
        <Typography sx={{ fontSize: "0.72rem", fontWeight: 700, color: "text.primary" }}>
          {t("nutrition.total")}
        </Typography>
        <Typography sx={{ fontSize: "0.78rem", fontWeight: 700, color: "text.primary", fontVariantNumeric: "tabular-nums" }}>
          ~{Math.round(totalCal)} kcal
        </Typography>
      </Box>

      <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.6rem", mt: 0.75, display: "block", px: 1 }}>
        {t("nutrition.basedOn", { resolved: resolvedIngredients, total: totalIngredients })}
        {negligibleIngredients > 0 && ` · ${t("nutrition.seasoningsExcluded", { count: negligibleIngredients })}`}
      </Typography>
    </Box>
  );
};

export default IngredientBreakdown;
