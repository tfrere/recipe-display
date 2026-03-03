import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Typography,
  Dialog,
  DialogContent,
  IconButton,
  Divider,
  Tooltip,
  Button,
  Collapse,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import MacroRing from "./MacroRing";
import DetailTable from "./DetailTable";
import MineralsSection from "./MineralsSection";
import {
  MACRO_COLORS,
  NUTRITION_TAG_KEYS,
  NUTRITION_TAG_CRITERIA_KEYS,
  formatMacro,
  roundCalories,
  pctDV,
} from "./constants";

const NutritionDialog = ({ open, onClose, recipeTitle, nutritionPerServing, nutritionTags }) => {
  const { t } = useTranslation();
  const [view, setView] = useState("overview");
  const [showMethodology, setShowMethodology] = useState(false);

  const handleClose = () => {
    onClose();
    setTimeout(() => setView("overview"), 200);
  };

  if (!nutritionPerServing) return null;

  const {
    calories = 0,
    protein = 0,
    fat = 0,
    carbs = 0,
    fiber = 0,
    sugar = 0,
    saturatedFat = 0,
    minerals = null,
    confidence = "none",
    resolvedIngredients = 0,
    totalIngredients = 0,
    negligibleIngredients = 0,
    source = "OpenNutrition",
    liquidRetentionApplied = false,
    ingredientDetails = [],
    servings = 1,
  } = nutritionPerServing;

  const tags = nutritionTags || [];

  const resolvedDetails = ingredientDetails
    .filter((d) => d.status === "resolved")
    .sort((a, b) => b.calories - a.calories);
  const unresolvedDetails = ingredientDetails.filter((d) => d.status !== "resolved");
  const hasIngredients = ingredientDetails.length > 0;

  const sodium = minerals?.sodium || 0;
  const secondaryMacros = [
    { key: "fiber", labelKey: "nutrition.macroFiber", value: fiber, color: MACRO_COLORS.fiber, unit: "g" },
    { key: "sugar", labelKey: "nutrition.macroSugar", value: sugar, color: MACRO_COLORS.sugar, unit: "g" },
    { key: "saturatedFat", labelKey: "nutrition.macroSaturatedFat", value: saturatedFat, color: MACRO_COLORS.saturatedFat, unit: "g" },
    { key: "sodium", labelKey: "nutrition.mineralSodium", value: sodium, color: "#90a4ae", unit: "mg" },
  ].filter((m) => m.value > 0);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth={view === "detail" ? "sm" : "xs"}
      fullWidth
      PaperProps={{ sx: { bgcolor: "background.paper", borderRadius: 3, backgroundImage: "none", transition: "max-width 0.2s ease" } }}
    >
      {/* Header */}
      <Box sx={{
        display: "flex", alignItems: "flex-start", justifyContent: "space-between",
        px: 3, pt: 2.5, pb: 0,
      }}>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography sx={{ fontWeight: 700, fontSize: "1.1rem" }}>
            {t("nutrition.estimatedTitle")}
          </Typography>
          {recipeTitle && (
            <Typography sx={{
              fontSize: "0.72rem", fontWeight: 500, color: "text.disabled",
              mt: 0.25, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>
              {recipeTitle}
            </Typography>
          )}
          {resolvedIngredients < totalIngredients && (
            <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.7rem" }}>
              {t("nutrition.basedOn", { resolved: resolvedIngredients, total: totalIngredients })}
            </Typography>
          )}
        </Box>
        <IconButton onClick={handleClose} size="small" sx={{ mt: -0.5, ml: 1, flexShrink: 0 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <DialogContent sx={{ pt: 2, pb: 2.5, px: 3 }}>
        {confidence === "low" && (
          <Box sx={{ p: 1.25, mb: 2, borderRadius: 2, bgcolor: "rgba(239, 83, 80, 0.06)", border: "1px solid rgba(239, 83, 80, 0.15)" }}>
            <Typography variant="caption" sx={{ color: "error.main", fontWeight: 600, fontSize: "0.72rem" }}>
              {t("nutrition.lowConfidenceWarning")}
            </Typography>
          </Box>
        )}

        {/* ── OVERVIEW VIEW ── */}
        {view === "overview" && (() => {
          const NutrientRow = ({ label, value, unit = "g", dvKey, bold, indent, color }) => {
            const dv = pctDV(value, dvKey);
            return (
              <Box sx={{ borderTop: "1px solid", borderColor: "divider", display: "flex", alignItems: "baseline", py: 0.5, px: 0.5 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1, pl: indent ? 2 : 0 }}>
                  {color && <Box sx={{ width: 7, height: 7, borderRadius: "50%", bgcolor: color, flexShrink: 0, position: "relative", top: -0.5 }} />}
                  <Typography sx={{ fontSize: "0.8rem", fontWeight: bold ? 700 : 400, color: "text.primary" }}>
                    {label}
                  </Typography>
                  <Typography sx={{ fontSize: "0.8rem", fontWeight: bold ? 700 : 400, color: "text.primary", fontVariantNumeric: "tabular-nums" }}>
                    {formatMacro(value, confidence)}{unit}
                  </Typography>
                </Box>
                {dv != null && (
                  <Typography sx={{ fontSize: "0.75rem", fontWeight: bold ? 600 : 400, color: "text.secondary", fontVariantNumeric: "tabular-nums", flexShrink: 0 }}>
                    {dv}%
                  </Typography>
                )}
              </Box>
            );
          };

          const primaryMacros = [
            { label: t("nutrition.macroProtein"), value: protein, dvKey: "protein", color: MACRO_COLORS.protein, bold: true },
            { label: t("nutrition.macroCarbs"), value: carbs, dvKey: "carbs", color: MACRO_COLORS.carbs, bold: true },
            { label: t("nutrition.macroFat"), value: fat, dvKey: "fat", color: MACRO_COLORS.fat, bold: true },
          ];

          return (
            <Box>
              {/* Hero: ring + calories */}
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 3, py: 2 }}>
                <MacroRing protein={protein} carbs={carbs} fat={fat} confidence={confidence} />
                <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                  <Typography sx={{ fontWeight: 800, fontSize: "2.8rem", lineHeight: 1, color: "text.primary", letterSpacing: "-0.03em" }}>
                    ~{roundCalories(calories)}
                  </Typography>
                  <Typography sx={{ color: "text.disabled", fontSize: "0.72rem", fontWeight: 500, mt: 0.5 }}>
                    {t("nutrition.kcalPerServing")}
                  </Typography>
                </Box>
              </Box>

              {/* Nutrition tags centered under hero */}
              {tags.length > 0 && (
                <Box sx={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 0.75, mb: 2 }}>
                  {tags.map((tag) => (
                    <Tooltip
                      key={tag}
                      title={NUTRITION_TAG_CRITERIA_KEYS[tag] ? t(NUTRITION_TAG_CRITERIA_KEYS[tag]) : ""}
                      arrow placement="top" enterDelay={300}
                      slotProps={{ tooltip: { sx: { fontSize: "0.72rem", maxWidth: 240 } } }}
                    >
                      <Typography
                        component="span"
                        sx={{
                          fontSize: "0.68rem",
                          color: "text.secondary",
                          px: 1,
                          py: 0.25,
                          borderRadius: 1,
                          border: "1px solid",
                          borderColor: "divider",
                          cursor: "default",
                          "&:hover": { borderColor: "text.disabled" },
                          transition: "border-color 0.15s ease",
                        }}
                      >
                        {NUTRITION_TAG_KEYS[tag] ? t(NUTRITION_TAG_KEYS[tag]) : tag}
                      </Typography>
                    </Tooltip>
                  ))}
                </Box>
              )}

              {/* %DV header */}
              <Box sx={{ display: "flex", justifyContent: "flex-end", py: 0.25, px: 0.5, borderBottom: "1px solid", borderColor: "divider" }}>
                <Typography sx={{ fontSize: "0.62rem", fontWeight: 600, color: "text.disabled" }}>
                  % {t("nutrition.dailyValue", { defaultValue: "Daily Value" })}
                </Typography>
              </Box>

              {/* Primary macros */}
              {primaryMacros.map((m) => (
                <NutrientRow key={m.label} {...m} />
              ))}

              {/* Secondary macros */}
              {secondaryMacros.map((m) => (
                <NutrientRow
                  key={m.key}
                  label={t(m.labelKey)}
                  value={m.value}
                  unit={m.unit}
                  dvKey={m.key}
                  indent
                />
              ))}

              {/* Bottom border */}
              <Box sx={{ borderTop: "1px solid", borderColor: "divider" }} />

              {/* Detail button */}
              {hasIngredients && (
                <Box sx={{ mt: 2.5, display: "flex", justifyContent: "center" }}>
                  <Button
                    onClick={() => setView("detail")}
                    variant="outlined"
                    size="small"
                    sx={{
                      textTransform: "none",
                      color: "text.secondary",
                      borderColor: "divider",
                      fontSize: "0.75rem",
                      fontWeight: 500,
                      px: 2.5,
                      py: 0.5,
                      borderRadius: 2,
                      "&:hover": { borderColor: "text.disabled", bgcolor: "action.hover" },
                    }}
                  >
                    {t("nutrition.advancedView")}
                  </Button>
                </Box>
              )}
            </Box>
          );
        })()}

        {/* ── DETAIL VIEW ── */}
        {view === "detail" && (
          <Box>
            <Button
              onClick={() => setView("overview")}
              startIcon={<ArrowBackIcon sx={{ fontSize: "0.85rem !important" }} />}
              sx={{
                textTransform: "none",
                color: "text.secondary",
                fontSize: "0.75rem",
                fontWeight: 500,
                mb: 2,
                px: 1,
                "&:hover": { bgcolor: "action.hover" },
              }}
            >
              {t("nutrition.backToOverview")}
            </Button>
            <DetailTable
              resolvedDetails={resolvedDetails}
              unresolvedDetails={unresolvedDetails}
              servings={servings}
              totalIngredients={totalIngredients}
              resolvedIngredients={resolvedIngredients}
              negligibleIngredients={negligibleIngredients}
              confidence={confidence}
              t={t}
            />
            {minerals && (
              <Box sx={{ mt: 2.5 }}>
                <MineralsSection minerals={minerals} t={t} />
              </Box>
            )}
          </Box>
        )}

        {/* Footer */}
        <Box sx={{ mt: 2, px: 1 }}>
          <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5, flexWrap: "wrap" }}>
            <Typography variant="caption" component="span" sx={{
              color: "text.disabled", fontSize: "0.56rem", opacity: 0.55,
              lineHeight: 1.35,
            }}>
              {t("nutrition.errorMarginDisclaimer")}
              {liquidRetentionApplied && ` · ${t("nutrition.liquidRetention")}`}
            </Typography>
            <Typography
              variant="caption"
              component="span"
              onClick={() => setShowMethodology((v) => !v)}
              sx={{
                color: "text.disabled", fontSize: "0.56rem", opacity: 0.55,
                lineHeight: 1.35,
                cursor: "pointer", textDecoration: "underline",
                textUnderlineOffset: "2px",
                "&:hover": { opacity: 0.8 },
                transition: "opacity 0.15s ease",
              }}
            >
              {t("nutrition.howCalculated")}
            </Typography>
          </Box>
          <Collapse in={showMethodology}>
            <Box sx={{ mt: 0.75, display: "flex", flexDirection: "column", gap: 0.5 }}>
              {(t("nutrition.methodologySteps", { returnObjects: true }) || []).map((step, i) => (
                <Box key={i} sx={{ display: "flex", gap: 0.5 }}>
                  <Typography component="span" sx={{
                    color: "text.disabled", fontSize: "0.56rem", opacity: 0.55,
                    lineHeight: 1.4, flexShrink: 0,
                  }}>
                    •
                  </Typography>
                  <Typography variant="caption" component="p" sx={{
                    color: "text.disabled", fontSize: "0.56rem", opacity: 0.55,
                    lineHeight: 1.4,
                  }}>
                    {step}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Collapse>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default NutritionDialog;
