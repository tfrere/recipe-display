import React from "react";
import { Box, Typography, Tooltip, alpha, useTheme } from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import FitnessCenterIcon from "@mui/icons-material/FitnessCenter";
import GrainIcon from "@mui/icons-material/Grain";
import WaterDropOutlinedIcon from "@mui/icons-material/WaterDropOutlined";
import GrassOutlinedIcon from "@mui/icons-material/GrassOutlined";

export const MACRO_REFERENCES = {
  protein: {
    min: 0.10,
    ideal: 0.15,
    max: 0.20,
    label: "Protein",
    color: "#66bb6a",
    icon: <FitnessCenterIcon />,
    source: "ANSES 10-20%",
    scale: 40,
  },
  carbs: {
    min: 0.40,
    ideal: 0.50,
    max: 0.55,
    label: "Carbs",
    color: "#ffa726",
    icon: <GrainIcon />,
    source: "ANSES 40-55%",
    scale: 80,
  },
  fat: {
    min: 0.35,
    ideal: 0.37,
    max: 0.40,
    label: "Fat",
    color: "#ef5350",
    icon: <WaterDropOutlinedIcon />,
    source: "ANSES 35-40%",
    scale: 60,
  },
  fiber: {
    label: "Fiber",
    color: "#8d6e63",
    icon: <GrassOutlinedIcon />,
    dailyMin: 25,
    source: "ANSES/WHO >= 25g/day",
  },
};

const getStatus = (pct, ref) => {
  const value = pct / 100;
  if (value >= ref.min && value <= ref.max) return { label: "In range", color: "#4caf50" };
  const dist = value < ref.min ? ref.min - value : value - ref.max;
  if (dist <= 0.05) return { label: value < ref.min ? "Slightly low" : "Slightly high", color: "#ff9800" };
  return { label: value < ref.min ? "Low" : "High", color: "#ef5350" };
};

const ReferenceTooltip = () => (
  <Box sx={{ p: 0.5, fontSize: "0.75rem", lineHeight: 1.6 }}>
    <Typography
      variant="caption"
      sx={{ fontWeight: 700, display: "block", mb: 0.5, fontSize: "0.75rem" }}
    >
      ANSES nutritional references (France)
    </Typography>
    {["protein", "carbs", "fat"].map((key) => {
      const ref = MACRO_REFERENCES[key];
      return (
        <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <Box
            sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: ref.color, flexShrink: 0 }}
          />
          <Typography variant="caption">
            {ref.label}: {ref.min * 100}–{ref.max * 100}% of energy
          </Typography>
        </Box>
      );
    })}
    <Typography
      variant="caption"
      sx={{ display: "block", mt: 0.75, color: "rgba(255,255,255,0.5)", fontSize: "0.65rem" }}
    >
      Sources: ANSES 2016, IOM/USDA AMDR, EFSA DRV, WHO
    </Typography>
  </Box>
);

const MacroRow = ({ macroKey, value, pct }) => {
  const theme = useTheme();
  const ref = MACRO_REFERENCES[macroKey];
  const status = getStatus(pct, ref);
  const scale = ref.scale;

  const rangeStartPct = (ref.min * 100 / scale) * 100;
  const rangeWidthPct = ((ref.max - ref.min) * 100 / scale) * 100;
  const valuePct = Math.min(pct / scale * 100, 100);
  const idealPct = (ref.ideal * 100 / scale) * 100;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, py: 0.75 }}>
      {/* Icon */}
      <Box sx={{ flexShrink: 0, display: "flex", alignItems: "center" }}>
        {React.cloneElement(ref.icon, {
          sx: { fontSize: "1rem", color: ref.color },
        })}
      </Box>

      {/* Label + value */}
      <Box sx={{ width: 80, flexShrink: 0 }}>
        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", lineHeight: 1.2 }}>
          {ref.label}
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.7rem" }}>
          {pct}% · {value}g
        </Typography>
      </Box>

      {/* Bar */}
      <Box sx={{ flex: 1, position: "relative", height: 28, display: "flex", alignItems: "center" }}>
        {/* Track */}
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            top: "50%",
            transform: "translateY(-50%)",
            height: 8,
            borderRadius: 4,
            bgcolor: alpha(theme.palette.text.primary, 0.06),
          }}
        />

        {/* Ideal range zone */}
        <Tooltip
          title={`Recommended: ${ref.min * 100}–${ref.max * 100}%`}
          arrow
          placement="top"
        >
          <Box
            sx={{
              position: "absolute",
              left: `${rangeStartPct}%`,
              width: `${rangeWidthPct}%`,
              top: "50%",
              transform: "translateY(-50%)",
              height: 18,
              borderRadius: 2,
              bgcolor: alpha(ref.color, 0.1),
              border: "1px dashed",
              borderColor: alpha(ref.color, 0.25),
            }}
          />
        </Tooltip>

        {/* Ideal marker (thin line) */}
        <Box
          sx={{
            position: "absolute",
            left: `${idealPct}%`,
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: 1,
            height: 14,
            bgcolor: alpha(ref.color, 0.3),
          }}
        />

        {/* Filled bar */}
        <Box
          sx={{
            position: "absolute",
            left: 0,
            width: `${valuePct}%`,
            top: "50%",
            transform: "translateY(-50%)",
            height: 8,
            borderRadius: 4,
            bgcolor: status.color,
            opacity: 0.7,
            transition: "width 0.5s ease",
          }}
        />

        {/* Value dot */}
        <Box
          sx={{
            position: "absolute",
            left: `${valuePct}%`,
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: 14,
            height: 14,
            borderRadius: "50%",
            bgcolor: status.color,
            border: "2px solid",
            borderColor: "background.paper",
            boxShadow: `0 0 0 1px ${alpha(status.color, 0.3)}`,
            transition: "left 0.5s ease",
            zIndex: 1,
          }}
        />
      </Box>

      {/* Status badge */}
      <Box
        sx={{
          flexShrink: 0,
          px: 1,
          py: 0.25,
          borderRadius: 1.5,
          bgcolor: alpha(status.color, 0.1),
          minWidth: 64,
          textAlign: "center",
        }}
      >
        <Typography
          variant="caption"
          sx={{ fontWeight: 600, fontSize: "0.65rem", color: status.color, whiteSpace: "nowrap" }}
        >
          {status.label}
        </Typography>
      </Box>
    </Box>
  );
};

const FiberRow = ({ avgFiber }) => {
  const theme = useTheme();
  const ref = MACRO_REFERENCES.fiber;
  const targetPerMeal = 8;
  const scale = 20;
  const valuePct = Math.min(avgFiber / scale * 100, 100);
  const targetPct = (targetPerMeal / scale) * 100;
  const isGood = avgFiber >= targetPerMeal;
  const statusColor = isGood ? "#4caf50" : "#ff9800";

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, py: 0.75 }}>
      <Box sx={{ flexShrink: 0, display: "flex", alignItems: "center" }}>
        {React.cloneElement(ref.icon, {
          sx: { fontSize: "1rem", color: ref.color },
        })}
      </Box>

      <Box sx={{ width: 80, flexShrink: 0 }}>
        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", lineHeight: 1.2 }}>
          {ref.label}
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.7rem" }}>
          {avgFiber}g / meal
        </Typography>
      </Box>

      <Box sx={{ flex: 1, position: "relative", height: 28, display: "flex", alignItems: "center" }}>
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            top: "50%",
            transform: "translateY(-50%)",
            height: 8,
            borderRadius: 4,
            bgcolor: alpha(theme.palette.text.primary, 0.06),
          }}
        />

        {/* Target line */}
        <Tooltip title={`Target: ≥${targetPerMeal}g per meal (≥25g/day)`} arrow placement="top">
          <Box
            sx={{
              position: "absolute",
              left: `${targetPct}%`,
              top: "50%",
              transform: "translate(-50%, -50%)",
              width: 2,
              height: 18,
              borderRadius: 1,
              bgcolor: alpha(ref.color, 0.4),
            }}
          />
        </Tooltip>

        <Box
          sx={{
            position: "absolute",
            left: 0,
            width: `${valuePct}%`,
            top: "50%",
            transform: "translateY(-50%)",
            height: 8,
            borderRadius: 4,
            bgcolor: statusColor,
            opacity: 0.7,
            transition: "width 0.5s ease",
          }}
        />

        <Box
          sx={{
            position: "absolute",
            left: `${valuePct}%`,
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: 14,
            height: 14,
            borderRadius: "50%",
            bgcolor: statusColor,
            border: "2px solid",
            borderColor: "background.paper",
            boxShadow: `0 0 0 1px ${alpha(statusColor, 0.3)}`,
            transition: "left 0.5s ease",
            zIndex: 1,
          }}
        />
      </Box>

      <Box
        sx={{
          flexShrink: 0,
          px: 1,
          py: 0.25,
          borderRadius: 1.5,
          bgcolor: alpha(statusColor, 0.1),
          minWidth: 64,
          textAlign: "center",
        }}
      >
        <Typography
          variant="caption"
          sx={{ fontWeight: 600, fontSize: "0.65rem", color: statusColor, whiteSpace: "nowrap" }}
        >
          {isGood ? "Good" : "Low"}
        </Typography>
      </Box>
    </Box>
  );
};

const MacroBalanceBar = ({ nutrition }) => {
  if (!nutrition || nutrition.recipesWithData === 0) return null;

  const macros = [
    { key: "protein", value: nutrition.avgProtein, pct: nutrition.proteinPct },
    { key: "carbs", value: nutrition.avgCarbs, pct: nutrition.carbsPct },
    { key: "fat", value: nutrition.avgFat, pct: nutrition.fatPct },
  ];

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
          {nutrition.avgCalories} kcal
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          avg. per meal
        </Typography>
        <Tooltip
          title={<ReferenceTooltip />}
          arrow
          placement="top"
          slotProps={{
            tooltip: {
              sx: { maxWidth: 320, bgcolor: "rgba(33,33,33,0.95)", p: 1.5 },
            },
          }}
        >
          <InfoOutlinedIcon
            sx={{
              fontSize: "0.85rem",
              color: "text.disabled",
              cursor: "help",
              "&:hover": { color: "text.secondary" },
            }}
          />
        </Tooltip>
        <Typography
          variant="caption"
          color="text.disabled"
          sx={{ ml: "auto", fontSize: "0.65rem" }}
        >
          {nutrition.recipesWithData}/{nutrition.total} with data
        </Typography>
      </Box>

      {/* Macro rows */}
      <Box sx={{ px: 2, pb: 1.5 }}>
        {macros.map(({ key, value, pct }) => (
          <MacroRow key={key} macroKey={key} value={value} pct={pct} />
        ))}
        {nutrition.avgFiber > 0 && <FiberRow avgFiber={nutrition.avgFiber} />}
      </Box>
    </Box>
  );
};

export default MacroBalanceBar;
