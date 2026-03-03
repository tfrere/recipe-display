import React from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Tooltip, alpha, useTheme } from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";

export const MACRO_REFERENCES = {
  protein: { min: 0.10, ideal: 0.15, max: 0.20, labelKey: "mealPlanner.macroProtein", color: "#66bb6a" },
  carbs: { min: 0.40, ideal: 0.50, max: 0.55, labelKey: "mealPlanner.macroCarbs", color: "#ffa726" },
  fat: { min: 0.35, ideal: 0.37, max: 0.40, labelKey: "mealPlanner.macroFat", color: "#ef5350" },
};

const getStatus = (pct, ref, t) => {
  const v = pct / 100;
  if (v >= ref.min && v <= ref.max) return { label: t("mealPlanner.statusOk"), ok: true };
  const dist = v < ref.min ? ref.min - v : v - ref.max;
  if (dist <= 0.05) return { label: v < ref.min ? t("mealPlanner.statusLow") : t("mealPlanner.statusHigh"), ok: false };
  return { label: v < ref.min ? t("mealPlanner.statusLow") : t("mealPlanner.statusHigh"), ok: false };
};

const MacroBalanceBar = ({ nutrition }) => {
  const { t } = useTranslation();
  if (!nutrition || nutrition.recipesWithData === 0) return null;

  const theme = useTheme();

  const macros = [
    { key: "protein", pct: nutrition.proteinPct, grams: nutrition.avgProtein },
    { key: "carbs", pct: nutrition.carbsPct, grams: nutrition.avgCarbs },
    { key: "fat", pct: nutrition.fatPct, grams: nutrition.avgFat },
  ];

  const fiberOk = nutrition.avgFiber >= 8;

  return (
    <Box
      sx={{
        mb: 3,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 2,
          pt: 1.5,
          pb: 1,
        }}
      >
        <LocalFireDepartmentIcon sx={{ fontSize: "1rem", color: "#ff9800" }} />
        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.85rem" }}>
          ~{nutrition.avgCalories} kcal
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {t("mealPlanner.avgPerMeal")}
        </Typography>
        <Tooltip
          title={
            <Box sx={{ p: 0.5, fontSize: "0.75rem", lineHeight: 1.6 }}>
              <Typography variant="caption" sx={{ fontWeight: 700, display: "block", mb: 0.5 }}>
                {t("mealPlanner.ansesRefs")}
              </Typography>
              {macros.map(({ key }) => {
                const ref = MACRO_REFERENCES[key];
                return (
                  <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: ref.color, flexShrink: 0 }} />
                    <Typography variant="caption">
                      {t(ref.labelKey)}: {ref.min * 100}–{ref.max * 100}%
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          }
          arrow
          placement="top"
          slotProps={{ tooltip: { sx: { maxWidth: 280, bgcolor: "rgba(33,33,33,0.95)", p: 1.5 } } }}
        >
          <InfoOutlinedIcon
            sx={{ fontSize: "0.85rem", color: "text.disabled", cursor: "help", "&:hover": { color: "text.secondary" } }}
          />
        </Tooltip>
        <Typography variant="caption" color="text.disabled" sx={{ ml: "auto", fontSize: "0.65rem" }}>
          {t("mealPlanner.withData", { withData: nutrition.recipesWithData, total: nutrition.total })}
        </Typography>
      </Box>

      {/* Stacked bars comparison */}
      <Box sx={{ px: 2, pb: 1.25 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
          <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.6rem", fontWeight: 600, width: 56, flexShrink: 0 }}>
            {t("mealPlanner.yourPlan")}
          </Typography>
          <Box sx={{ flex: 1, display: "flex", height: 10, borderRadius: 5, overflow: "hidden" }}>
            {macros.map(({ key, pct }) => (
              <Box
                key={key}
                sx={{
                  width: `${pct}%`,
                  bgcolor: MACRO_REFERENCES[key].color,
                  transition: "width 0.4s ease",
                }}
              />
            ))}
          </Box>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.6rem", fontWeight: 500, width: 56, flexShrink: 0 }}>
            {t("mealPlanner.reference")}
          </Typography>
          <Box sx={{ flex: 1, display: "flex", height: 10, borderRadius: 5, overflow: "hidden", opacity: 0.35 }}>
            {macros.map(({ key }) => (
              <Box
                key={key}
                sx={{
                  width: `${MACRO_REFERENCES[key].ideal * 100}%`,
                  bgcolor: MACRO_REFERENCES[key].color,
                }}
              />
            ))}
          </Box>
        </Box>
      </Box>

      {/* Macro stats */}
      <Box
        sx={{
          display: "flex",
          borderTop: "1px solid",
          borderColor: "divider",
        }}
      >
        {macros.map(({ key, pct, grams }, i) => {
          const ref = MACRO_REFERENCES[key];
          const status = getStatus(pct, ref, t);
          return (
            <React.Fragment key={key}>
              {i > 0 && <Box sx={{ width: "1px", bgcolor: "divider", my: 1.5 }} />}
              <Box
                sx={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 0.25,
                  py: 1.5,
                }}
              >
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: ref.color,
                    mb: 0.25,
                  }}
                />
                <Typography variant="body2" sx={{ fontWeight: 700, fontSize: "1rem", lineHeight: 1 }}>
                  {pct}%
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.7rem", lineHeight: 1 }}>
                  {t(ref.labelKey)}
                </Typography>
                <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.65rem" }}>
                  {grams}g
                </Typography>
                <Box
                  sx={{
                    mt: 0.25,
                    px: 0.75,
                    py: 0.15,
                    borderRadius: 1,
                    bgcolor: alpha(status.ok ? "#4caf50" : "#ff9800", 0.1),
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 600,
                      fontSize: "0.6rem",
                      color: status.ok ? "#4caf50" : "#ff9800",
                      lineHeight: 1.2,
                    }}
                  >
                    {status.label}
                  </Typography>
                </Box>
              </Box>
            </React.Fragment>
          );
        })}

        {/* Fiber */}
        {nutrition.avgFiber > 0 && (
          <>
            <Box sx={{ width: "1px", bgcolor: "divider", my: 1.5 }} />
            <Box
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 0.25,
                py: 1.5,
              }}
            >
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: "#8d6e63",
                  mb: 0.25,
                }}
              />
              <Typography variant="body2" sx={{ fontWeight: 700, fontSize: "1rem", lineHeight: 1 }}>
                {nutrition.avgFiber}g
              </Typography>
              <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.7rem", lineHeight: 1 }}>
                {t("mealPlanner.macroFiber")}
              </Typography>
              <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.65rem" }}>
                {t("mealPlanner.perMeal")}
              </Typography>
              <Box
                sx={{
                  mt: 0.25,
                  px: 0.75,
                  py: 0.15,
                  borderRadius: 1,
                  bgcolor: alpha(fiberOk ? "#4caf50" : "#ff9800", 0.1),
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontWeight: 600,
                    fontSize: "0.6rem",
                    color: fiberOk ? "#4caf50" : "#ff9800",
                    lineHeight: 1.2,
                  }}
                >
                  {fiberOk ? t("mealPlanner.statusOk") : t("mealPlanner.statusLow")}
                </Typography>
              </Box>
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
};

export default MacroBalanceBar;
