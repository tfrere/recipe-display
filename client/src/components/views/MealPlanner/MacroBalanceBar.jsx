import React from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import FitnessCenterIcon from "@mui/icons-material/FitnessCenter";
import GrainIcon from "@mui/icons-material/Grain";
import WaterDropOutlinedIcon from "@mui/icons-material/WaterDropOutlined";
import GrassOutlinedIcon from "@mui/icons-material/GrassOutlined";

/**
 * Macronutrient reference ranges.
 *
 * Sources:
 *   - ANSES (France, 2016): Protéines 10-20%, Glucides 40-55%, Lipides 35-40%
 *   - IOM/USDA AMDR:        Protéines 10-35%, Glucides 45-65%, Lipides 20-35%
 *   - EFSA (Europe):         Protéines ~10-15%, Glucides ~52%, Lipides ~31.5%
 *   - WHO/OMS:               Lipides <= 30% (focus qualité, pas de range strict)
 *
 * We use ANSES as the primary reference (French audience) with cross-validation
 * against USDA/EFSA. The "ideal" is the midpoint of the ANSES range.
 */
export const MACRO_REFERENCES = {
  protein: {
    min: 0.10,
    ideal: 0.15,
    max: 0.20,
    label: "Protein",
    color: "#66bb6a",
    icon: <FitnessCenterIcon />,
    source: "ANSES 10-20%",
  },
  carbs: {
    min: 0.40,
    ideal: 0.50,
    max: 0.55,
    label: "Carbs",
    color: "#ffa726",
    icon: <GrainIcon />,
    source: "ANSES 40-55%",
  },
  fat: {
    min: 0.35,
    ideal: 0.37,
    max: 0.40,
    label: "Fat",
    color: "#ef5350",
    icon: <WaterDropOutlinedIcon />,
    source: "ANSES 35-40%",
  },
  fiber: {
    label: "Fiber",
    color: "#8d6e63",
    icon: <GrassOutlinedIcon />,
    dailyMin: 25,
    source: "ANSES/WHO >= 25g/day",
  },
};

const getStatusColor = (pct, ref) => {
  const value = pct / 100;
  if (value >= ref.min && value <= ref.max) return "#4caf50";
  const dist = value < ref.min ? ref.min - value : value - ref.max;
  if (dist <= 0.05) return "#ff9800";
  return "#ef5350";
};

const getStatusLabel = (pct, ref) => {
  const value = pct / 100;
  if (value >= ref.min && value <= ref.max) return "In range";
  if (value < ref.min) return "Low";
  return "High";
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
            sx={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              bgcolor: ref.color,
              flexShrink: 0,
            }}
          />
          <Typography variant="caption">
            {ref.label}: {ref.min * 100}-{ref.max * 100}% of energy (ideal{" "}
            {ref.ideal * 100}%)
          </Typography>
        </Box>
      );
    })}
    <Typography
      variant="caption"
      sx={{
        display: "block",
        mt: 0.75,
        color: "rgba(255,255,255,0.7)",
        fontStyle: "italic",
      }}
    >
      Green = in range · Orange = close · Red = out of range
    </Typography>
    <Typography
      variant="caption"
      sx={{
        display: "block",
        mt: 0.25,
        color: "rgba(255,255,255,0.5)",
        fontSize: "0.65rem",
      }}
    >
      Sources: ANSES 2016, IOM/USDA AMDR, EFSA DRV, WHO
    </Typography>
  </Box>
);

const MacroColumn = ({ macroKey, value, pct }) => {
  const ref = MACRO_REFERENCES[macroKey];
  const statusColor = getStatusColor(pct, ref);
  const statusLabel = getStatusLabel(pct, ref);

  return (
    <Box
      sx={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 0.5,
        py: 1.5,
      }}
    >
      {React.cloneElement(ref.icon, {
        sx: { fontSize: "1.1rem", color: ref.color, opacity: 0.8 },
      })}
      <Typography variant="h6" sx={{ fontWeight: 800, fontSize: "1.1rem", lineHeight: 1 }}>
        {pct}%
      </Typography>
      <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.7rem", lineHeight: 1 }}>
        {ref.label}
      </Typography>
      <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.65rem" }}>
        {value}g
      </Typography>
      <Box
        sx={{
          px: 0.75,
          py: 0.15,
          borderRadius: 1,
          bgcolor: `${statusColor}18`,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            fontWeight: 600,
            fontSize: "0.6rem",
            color: statusColor,
            lineHeight: 1.2,
          }}
        >
          {statusLabel}
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
              sx: {
                maxWidth: 320,
                bgcolor: "rgba(33,33,33,0.95)",
                p: 1.5,
              },
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

      {/* Macro columns */}
      <Box
        sx={{
          display: "flex",
          borderTop: "1px solid",
          borderColor: "divider",
        }}
      >
        {macros.map(({ key, value, pct }, i) => (
          <React.Fragment key={key}>
            {i > 0 && (
              <Box
                sx={{
                  width: "1px",
                  bgcolor: "divider",
                  my: 1.5,
                }}
              />
            )}
            <MacroColumn macroKey={key} value={value} pct={pct} />
          </React.Fragment>
        ))}
        {/* Fiber column (absolute value, not percentage) */}
        {nutrition.avgFiber > 0 && (
          <>
            <Box sx={{ width: "1px", bgcolor: "divider", my: 1.5 }} />
            <Box
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 0.5,
                py: 1.5,
              }}
            >
              {React.cloneElement(MACRO_REFERENCES.fiber.icon, {
                sx: { fontSize: "1.1rem", color: MACRO_REFERENCES.fiber.color, opacity: 0.8 },
              })}
              <Typography variant="h6" sx={{ fontWeight: 800, fontSize: "1.1rem", lineHeight: 1 }}>
                {nutrition.avgFiber}g
              </Typography>
              <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.7rem", lineHeight: 1 }}>
                Fiber
              </Typography>
              <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.65rem" }}>
                per meal
              </Typography>
              <Box
                sx={{
                  px: 0.75,
                  py: 0.15,
                  borderRadius: 1,
                  bgcolor: nutrition.avgFiber >= 8 ? "#4caf5018" : "#ff980018",
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontWeight: 600,
                    fontSize: "0.6rem",
                    color: nutrition.avgFiber >= 8 ? "#4caf50" : "#ff9800",
                    lineHeight: 1.2,
                  }}
                >
                  {nutrition.avgFiber >= 8 ? "Good" : "Low"}
                </Typography>
              </Box>
            </Box>
          </>
        )}
      </Box>

      {/* Stacked bar comparison */}
      <Box sx={{ px: 2, pb: 1.5 }}>
        <Box
          sx={{
            display: "flex",
            height: 6,
            borderRadius: 3,
            overflow: "hidden",
          }}
        >
          {macros.map(({ key, pct }) => (
            <Box
              key={key}
              sx={{
                width: `${pct}%`,
                bgcolor: MACRO_REFERENCES[key].color,
                transition: "width 0.3s",
              }}
            />
          ))}
        </Box>
        <Box
          sx={{
            display: "flex",
            height: 3,
            borderRadius: 3,
            overflow: "hidden",
            mt: 0.5,
            opacity: 0.3,
          }}
        >
          {["protein", "carbs", "fat"].map((key) => (
            <Box
              key={key}
              sx={{
                width: `${MACRO_REFERENCES[key].ideal * 100}%`,
                bgcolor: MACRO_REFERENCES[key].color,
              }}
            />
          ))}
        </Box>
        <Typography
          variant="caption"
          sx={{
            color: "text.disabled",
            fontSize: "0.55rem",
            display: "block",
            textAlign: "right",
            mt: 0.25,
          }}
        >
          vs. ANSES reference
        </Typography>
      </Box>
    </Box>
  );
};

export default MacroBalanceBar;
