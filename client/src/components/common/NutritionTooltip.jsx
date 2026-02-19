import React, { useState } from "react";
import {
  Box,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  LinearProgress,
  Divider,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import FitnessCenterIcon from "@mui/icons-material/FitnessCenter";
import GrainIcon from "@mui/icons-material/Grain";
import WaterDropOutlinedIcon from "@mui/icons-material/WaterDropOutlined";
import GrassOutlinedIcon from "@mui/icons-material/GrassOutlined";
import RecipeChip, { CHIP_TYPES } from "./RecipeChip";

/**
 * Labels for nutrition tags
 */
const NUTRITION_TAG_LABELS = {
  "high-protein": "High protein",
  "low-calorie": "Light",
  "high-fiber": "High fiber",
  "indulgent": "Indulgent",
  "balanced": "Balanced",
};

/**
 * Confidence level config
 */
const CONFIDENCE_CONFIG = {
  high: { label: "High", color: "success.main", chipColor: "#66bb6a", pct: 90 },
  medium: { label: "Medium", color: "warning.main", chipColor: "#ffa726", pct: 60 },
  low: { label: "Low", color: "error.main", chipColor: "#ef5350", pct: 30 },
  none: { label: "Unavailable", color: "text.disabled", chipColor: "#bdbdbd", pct: 0 },
};

/**
 * Macro colors
 */
const MACRO_COLORS = {
  protein: "#66bb6a",
  carbs: "#ffa726",
  fat: "#ef5350",
  fiber: "#8d6e63",
};

/**
 * Round calories to nearest 10 for display (avoids false precision)
 */
const roundCalories = (cal) => Math.round(cal / 10) * 10;

/**
 * Format a macro value for display.
 * For low confidence, show "~" prefix; for high, show exact.
 */
const formatMacro = (value, confidence) => {
  if (confidence === "low") return `~${Math.round(value)}`;
  if (confidence === "medium") return `~${Math.round(value * 10) / 10}`;
  return Math.round(value * 10) / 10;
};

/**
 * Donut-style macro ring using SVG
 */
const MacroRing = ({ protein, carbs, fat, calories, confidence }) => {
  const total = (protein || 0) * 4 + (carbs || 0) * 4 + (fat || 0) * 9;
  if (total === 0) return null;

  const pctProtein = ((protein || 0) * 4 / total) * 100;
  const pctCarbs = ((carbs || 0) * 4 / total) * 100;
  const pctFat = ((fat || 0) * 9 / total) * 100;

  const radius = 54;
  const circumference = 2 * Math.PI * radius;

  // Build SVG arcs
  const segments = [
    { pct: pctProtein, color: MACRO_COLORS.protein },
    { pct: pctCarbs, color: MACRO_COLORS.carbs },
    { pct: pctFat, color: MACRO_COLORS.fat },
  ];

  let offset = 0;
  const displayCal = roundCalories(calories);
  const isLowConfidence = confidence === "low";

  return (
    <Box sx={{ position: "relative", width: 140, height: 140, mx: "auto" }}>
      <svg viewBox="0 0 128 128" width="140" height="140">
        {/* Background ring */}
        <circle
          cx="64" cy="64" r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="12"
        />
        {/* Macro segments */}
        {segments.map((seg, i) => {
          const dashLength = (seg.pct / 100) * circumference;
          const dashOffset = -(offset / 100) * circumference;
          offset += seg.pct;
          return (
            <circle
              key={i}
              cx="64" cy="64" r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth="12"
              strokeDasharray={`${dashLength} ${circumference - dashLength}`}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              transform="rotate(-90 64 64)"
              style={{
                transition: "stroke-dasharray 0.5s ease",
                opacity: isLowConfidence ? 0.4 : 1,
              }}
            />
          );
        })}
      </svg>
      {/* Center text */}
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center",
        }}
      >
        <Typography
          variant="h5"
          sx={{ fontWeight: 700, lineHeight: 1, color: "text.primary" }}
        >
          {isLowConfidence ? "~" : ""}{displayCal}
        </Typography>
        <Typography
          variant="caption"
          sx={{ color: "text.secondary", fontSize: "0.7rem" }}
        >
          kcal / serving
        </Typography>
      </Box>
    </Box>
  );
};

/**
 * Macro detail row
 */
const MacroRow = ({ icon, label, value, unit, color, pctOfCalories }) => (
  <Box
    sx={{
      display: "flex",
      alignItems: "center",
      gap: 1.5,
      py: 1,
    }}
  >
    <Box
      sx={{
        width: 36,
        height: 36,
        borderRadius: "10px",
        backgroundColor: `${color}15`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      {React.cloneElement(icon, { sx: { fontSize: "1.1rem", color } })}
    </Box>
    <Box sx={{ flex: 1 }}>
      <Typography
        variant="body2"
        sx={{ fontWeight: 500, color: "text.primary", fontSize: "0.85rem" }}
      >
        {label}
      </Typography>
      {pctOfCalories !== undefined && (
        <LinearProgress
          variant="determinate"
          value={Math.min(pctOfCalories, 100)}
          sx={{
            mt: 0.5,
            height: 3,
            borderRadius: 2,
            backgroundColor: "rgba(255,255,255,0.06)",
            "& .MuiLinearProgress-bar": {
              backgroundColor: color,
              borderRadius: 2,
            },
          }}
        />
      )}
    </Box>
    <Typography
      variant="body2"
      sx={{ fontWeight: 600, color: "text.primary", minWidth: 50, textAlign: "right" }}
    >
      {value}{unit}
    </Typography>
  </Box>
);

/**
 * Nutrition Dialog — detailed popup showing nutritional breakdown
 */
const NutritionDialog = ({ open, onClose, nutritionPerServing, nutritionTags }) => {
  if (!nutritionPerServing) return null;

  const {
    calories = 0,
    protein = 0,
    fat = 0,
    carbs = 0,
    fiber = 0,
    confidence = "none",
    resolvedIngredients = 0,
    matchedIngredients,
    totalIngredients = 0,
    negligibleIngredients = 0,
    source = "OpenNutrition",
    liquidRetentionApplied = false,
  } = nutritionPerServing;

  const conf = CONFIDENCE_CONFIG[confidence] || CONFIDENCE_CONFIG.none;
  const tags = nutritionTags || [];

  // Calorie percentages
  const totalCal = calories || 1;
  const pctProtein = Math.round((protein * 4 / totalCal) * 100);
  const pctCarbs = Math.round((carbs * 4 / totalCal) * 100);
  const pctFat = Math.round((fat * 9 / totalCal) * 100);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: "background.paper",
          borderRadius: 3,
          backgroundImage: "none",
        },
      }}
    >
      <DialogTitle
        sx={{
          pb: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <ScienceOutlinedIcon sx={{ color: "text.secondary", fontSize: "1.2rem" }} />
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "1.05rem" }}>
            Estimated nutrition
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 2 }}>
        {/* Low confidence banner */}
        {confidence === "low" && (
          <Box
            sx={{
              p: 1.5,
              mb: 1,
              borderRadius: 2,
              backgroundColor: "rgba(239, 83, 80, 0.08)",
              border: "1px solid rgba(239, 83, 80, 0.2)",
            }}
          >
            <Typography
              variant="caption"
              sx={{ color: "error.main", fontWeight: 600, fontSize: "0.8rem" }}
            >
              Insufficient data — values shown are rough estimates only
            </Typography>
          </Box>
        )}

        {/* Donut ring */}
        <Box sx={{ my: 2 }}>
          <MacroRing
            protein={protein}
            carbs={carbs}
            fat={fat}
            calories={calories}
            confidence={confidence}
          />
        </Box>

        {/* Legend under ring */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            gap: 2,
            mb: 2.5,
          }}
        >
          {[
            { label: "Protein", pct: pctProtein, color: MACRO_COLORS.protein },
            { label: "Carbs", pct: pctCarbs, color: MACRO_COLORS.carbs },
            { label: "Fat", pct: pctFat, color: MACRO_COLORS.fat },
          ].map((item) => (
            <Box key={item.label} sx={{ textAlign: "center" }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: item.color,
                  mx: "auto",
                  mb: 0.25,
                }}
              />
              <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.65rem" }}>
                {item.label} {item.pct}%
              </Typography>
            </Box>
          ))}
        </Box>

        <Divider sx={{ mb: 1.5 }} />

        {/* Macro rows */}
        <MacroRow
          icon={<FitnessCenterIcon />}
          label="Protein"
          value={formatMacro(protein, confidence)}
          unit="g"
          color={MACRO_COLORS.protein}
          pctOfCalories={pctProtein}
        />
        <MacroRow
          icon={<GrainIcon />}
          label="Carbs"
          value={formatMacro(carbs, confidence)}
          unit="g"
          color={MACRO_COLORS.carbs}
          pctOfCalories={pctCarbs}
        />
        <MacroRow
          icon={<WaterDropOutlinedIcon />}
          label="Fat"
          value={formatMacro(fat, confidence)}
          unit="g"
          color={MACRO_COLORS.fat}
          pctOfCalories={pctFat}
        />
        <MacroRow
          icon={<GrassOutlinedIcon />}
          label="Fiber"
          value={formatMacro(fiber, confidence)}
          unit="g"
          color={MACRO_COLORS.fiber}
        />

        {/* Tags */}
        {tags.length > 0 && (
          <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            {tags.map((tag) => (
              <RecipeChip
                key={tag}
                label={NUTRITION_TAG_LABELS[tag] || tag}
                type={CHIP_TYPES.NUTRITION}
                size="small"
              />
            ))}
          </Box>
        )}

        {/* Confidence & disclaimer */}
        <Box
          sx={{
            mt: 2.5,
            p: 1.5,
            borderRadius: 2,
            backgroundColor: "action.hover",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.75,
              mb: 0.75,
            }}
          >
            <InfoOutlinedIcon sx={{ fontSize: "0.9rem", color: "text.secondary" }} />
            <Typography variant="caption" sx={{ fontWeight: 600, color: "text.secondary" }}>
              About this data
            </Typography>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: conf.chipColor,
                flexShrink: 0,
              }}
            />
            <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.75rem" }}>
              {conf.label} confidence — {resolvedIngredients} of {totalIngredients} ingredient{totalIngredients > 1 ? "s" : ""} resolved
              {negligibleIngredients > 0 && (
                <> ({negligibleIngredients} spice{negligibleIngredients > 1 ? "s" : ""}/condiment{negligibleIngredients > 1 ? "s" : ""} excluded)</>
              )}
            </Typography>
          </Box>
          {matchedIngredients !== undefined && matchedIngredients > resolvedIngredients && (
            <Typography
              variant="caption"
              sx={{
                color: "text.secondary",
                fontSize: "0.7rem",
                display: "block",
                lineHeight: 1.6,
                mb: 0.5,
                ml: 2.5,
              }}
            >
              {matchedIngredients - resolvedIngredients} ingredient{matchedIngredients - resolvedIngredients > 1 ? "s" : ""}{" "}
              identified but without precise quantities (not included in calculation).
            </Typography>
          )}

          {liquidRetentionApplied && (
            <Typography
              variant="caption"
              sx={{
                color: "text.secondary",
                fontSize: "0.7rem",
                display: "block",
                lineHeight: 1.6,
                mb: 0.5,
              }}
            >
              Cooking liquids (broth, wine, etc.) have been adjusted to
              account for absorption and evaporation during cooking.
            </Typography>
          )}

          <Typography
            variant="caption"
            sx={{
              color: "text.disabled",
              fontSize: "0.7rem",
              display: "block",
              lineHeight: 1.6,
            }}
          >
            These values are estimates based on the {source} database.
            They may vary depending on brands, preparation methods,
            and actual quantities used.
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

/**
 * NutritionTooltip — displays a clickable nutrition chip that opens a detailed dialog.
 *
 * Props:
 * - nutritionTags: string[] — e.g. ["high-protein", "low-calorie"]
 * - nutritionPerServing: object — full nutrition profile
 */
const NutritionTooltip = ({ nutritionTags, nutritionPerServing }) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  // Don't render if no data
  if (
    (!nutritionTags || nutritionTags.length === 0) &&
    !nutritionPerServing
  ) {
    return null;
  }

  const tags = nutritionTags || [];
  const hasDetailedData =
    nutritionPerServing && nutritionPerServing.confidence !== "none";

  const confidence = nutritionPerServing?.confidence || "none";
  const conf = CONFIDENCE_CONFIG[confidence] || CONFIDENCE_CONFIG.none;
  const isHighConfidence = confidence === "high";

  return (
    <>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        {/* Nutrition tags — only show when confidence is high */}
        {isHighConfidence && tags.map((tag) => (
          <RecipeChip
            key={tag}
            label={NUTRITION_TAG_LABELS[tag] || tag}
            type={CHIP_TYPES.NUTRITION}
            size="small"
            onClick={hasDetailedData ? () => setDialogOpen(true) : undefined}
            sx={hasDetailedData ? { cursor: "pointer" } : {}}
          />
        ))}

        {/* Calorie chip + confidence indicator */}
        {hasDetailedData && confidence !== "low" && (
          <Chip
            label={`${isHighConfidence ? "" : "~"}${roundCalories(nutritionPerServing.calories)} kcal`}
            size="small"
            variant="outlined"
            icon={<LocalFireDepartmentIcon sx={{ fontSize: "0.85rem" }} />}
            onClick={() => setDialogOpen(true)}
            sx={{
              cursor: "pointer",
              borderRadius: "6px",
              borderColor: isHighConfidence
                ? "rgba(255, 152, 0, 0.3)"
                : "rgba(150, 150, 150, 0.3)",
              backgroundColor: isHighConfidence
                ? "rgba(255, 152, 0, 0.06)"
                : "rgba(150, 150, 150, 0.06)",
              fontSize: "0.75rem",
              fontWeight: 600,
              "& .MuiChip-icon": {
                color: isHighConfidence ? "#ff9800" : "#9e9e9e",
              },
              "&:hover": {
                backgroundColor: isHighConfidence
                  ? "rgba(255, 152, 0, 0.12)"
                  : "rgba(150, 150, 150, 0.12)",
              },
            }}
          />
        )}

        {/* Low confidence: show "insufficient data" chip instead of precise numbers */}
        {hasDetailedData && confidence === "low" && (
          <Chip
            label="Nutrition data insufficient"
            size="small"
            variant="outlined"
            icon={<ScienceOutlinedIcon sx={{ fontSize: "0.85rem" }} />}
            onClick={() => setDialogOpen(true)}
            sx={{
              cursor: "pointer",
              borderRadius: "6px",
              borderColor: "rgba(150, 150, 150, 0.3)",
              backgroundColor: "rgba(150, 150, 150, 0.06)",
              fontSize: "0.7rem",
              fontWeight: 500,
              color: "text.secondary",
              "& .MuiChip-icon": { color: "#9e9e9e" },
              "&:hover": {
                backgroundColor: "rgba(150, 150, 150, 0.12)",
              },
            }}
          />
        )}

        {/* Confidence badge — show "estimation" for medium */}
        {hasDetailedData && confidence === "medium" && (
          <Typography
            variant="caption"
            sx={{
              color: conf.chipColor,
              fontSize: "0.65rem",
              fontWeight: 500,
              opacity: 0.8,
            }}
          >
            estimation
          </Typography>
        )}
      </Box>

      {/* Detailed dialog */}
      {hasDetailedData && (
        <NutritionDialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          nutritionPerServing={nutritionPerServing}
          nutritionTags={tags}
        />
      )}
    </>
  );
};

export default NutritionTooltip;
