import React, { useMemo } from "react";
import { Box, Typography, useTheme, Tooltip } from "@mui/material";
import { useRecipe } from "../../../contexts/RecipeContext";
import { parseTimeToMinutes } from "../../../utils/timeUtils";

/**
 * Compute a scheduled timeline from recipe steps.
 * Each step is assigned a start/end time and a "machine" (lane).
 * Passive steps free the "cook" lane for other tasks.
 */
const computeSchedule = (recipe) => {
  if (!recipe?.subRecipes) return { lanes: {}, makespan: 0, steps: [] };

  const subRecipes = recipe.subRecipes || [];

  // Flatten all steps with their sub-recipe info
  const allSteps = [];
  subRecipes.forEach((sr) => {
    (sr.steps || []).forEach((step) => {
      if (!step) return;
      allSteps.push({
        ...step,
        subRecipeTitle: sr.title || sr.id || "main",
        durationMin: step.time ? parseTimeToMinutes(step.time) : (step.duration ? parseTimeToMinutes(step.duration) : 3),
      });
    });
  });

  // Build state → step producer map for dependency resolution
  const stateProducer = {}; // stateId → step index in allSteps
  allSteps.forEach((step, i) => {
    if (step.produces) stateProducer[step.produces] = i;
  });

  // Schedule each step via topological order
  const scheduled = allSteps.map(() => null);
  const laneEndTimes = {}; // laneName → earliest available time

  const getStepLane = (step) => {
    if (step.isPassive) {
      // Passive steps go to their equipment/sub-recipe lane
      return step.subRecipeTitle;
    }
    return "Vous";
  };

  // Compute start times respecting dependencies
  const computeStart = (idx) => {
    if (scheduled[idx] !== null) return scheduled[idx].start;

    const step = allSteps[idx];
    let earliest = 0;

    // Check dependencies: all states in `uses` that come from other steps
    (step.uses || []).forEach((ref) => {
      if (stateProducer[ref] !== undefined) {
        const depIdx = stateProducer[ref];
        const depEnd = computeStart(depIdx) + allSteps[depIdx].durationMin;
        earliest = Math.max(earliest, depEnd);
      }
    });
    (step.requires || []).forEach((ref) => {
      if (stateProducer[ref] !== undefined) {
        const depIdx = stateProducer[ref];
        const depEnd = computeStart(depIdx) + allSteps[depIdx].durationMin;
        earliest = Math.max(earliest, depEnd);
      }
    });

    // Also respect lane availability (can't overlap on same lane)
    const lane = getStepLane(step);
    const laneAvailable = laneEndTimes[lane] || 0;
    earliest = Math.max(earliest, laneAvailable);

    const start = earliest;
    const end = start + step.durationMin;

    scheduled[idx] = { start, end, lane };
    laneEndTimes[lane] = end;

    return start;
  };

  // Process all steps
  allSteps.forEach((_, i) => computeStart(i));

  // Build lane data
  const lanes = {};
  let makespan = 0;
  const stepsWithSchedule = allSteps.map((step, i) => {
    const sched = scheduled[i];
    if (!lanes[sched.lane]) lanes[sched.lane] = [];
    const entry = {
      ...step,
      start: sched.start,
      end: sched.end,
      lane: sched.lane,
    };
    lanes[sched.lane].push(entry);
    makespan = Math.max(makespan, sched.end);
    return entry;
  });

  return { lanes, makespan, steps: stepsWithSchedule };
};

// Color palette for sub-recipes
const SUB_RECIPE_COLORS = [
  { bg: "#e3f2fd", border: "#1976d2", text: "#0d47a1" },
  { bg: "#fce4ec", border: "#c62828", text: "#b71c1c" },
  { bg: "#e8f5e9", border: "#2e7d32", text: "#1b5e20" },
  { bg: "#fff3e0", border: "#e65100", text: "#bf360c" },
  { bg: "#f3e5f5", border: "#7b1fa2", text: "#4a148c" },
  { bg: "#e0f7fa", border: "#00838f", text: "#006064" },
  { bg: "#fff8e1", border: "#f9a825", text: "#f57f17" },
];

const SUB_RECIPE_COLORS_DARK = [
  { bg: "#1a3a5c", border: "#42a5f5", text: "#90caf9" },
  { bg: "#4a1a1a", border: "#ef5350", text: "#ef9a9a" },
  { bg: "#1a3a1a", border: "#66bb6a", text: "#a5d6a7" },
  { bg: "#3e2723", border: "#ff9800", text: "#ffcc80" },
  { bg: "#2a1a3a", border: "#ab47bc", text: "#ce93d8" },
  { bg: "#1a3a3a", border: "#26c6da", text: "#80deea" },
  { bg: "#3a3a1a", border: "#fdd835", text: "#fff59d" },
];

const formatTime = (minutes) => {
  if (minutes < 60) return `${minutes}min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h${m}` : `${h}h`;
};

const GanttContent = () => {
  const { recipe } = useRecipe();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  const { lanes, makespan } = useMemo(() => {
    if (!recipe) return { lanes: {}, makespan: 0, steps: [] };
    return computeSchedule(recipe);
  }, [recipe]);

  if (!recipe || makespan === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">
          Aucune donnée de timeline disponible.
        </Typography>
      </Box>
    );
  }

  // Build color map for sub-recipes
  const colorPalette = isDark ? SUB_RECIPE_COLORS_DARK : SUB_RECIPE_COLORS;
  const subRecipeNames = [...new Set(
    Object.values(lanes).flat().map((s) => s.subRecipeTitle)
  )];
  const colorMap = {};
  subRecipeNames.forEach((name, i) => {
    colorMap[name] = colorPalette[i % colorPalette.length];
  });

  // Sort lanes: "Vous" first, then others alphabetically
  const laneNames = Object.keys(lanes).sort((a, b) => {
    if (a === "Vous") return -1;
    if (b === "Vous") return 1;
    return a.localeCompare(b);
  });

  // Time scale
  const LANE_HEIGHT = 64;
  const LANE_GAP = 8;
  const LABEL_WIDTH = 120;
  const MIN_PX_PER_MIN = 6;
  const chartWidth = Math.max(800, makespan * MIN_PX_PER_MIN);

  // Time markers every 10 min (or 5 if short recipe)
  const interval = makespan <= 30 ? 5 : makespan <= 120 ? 10 : 15;
  const timeMarkers = [];
  for (let t = 0; t <= makespan; t += interval) {
    timeMarkers.push(t);
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        overflow: "auto",
        p: 3,
        bgcolor: "background.default",
      }}
    >
      {/* Legend */}
      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        {subRecipeNames.map((name) => (
          <Box
            key={name}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.75,
            }}
          >
            <Box
              sx={{
                width: 14,
                height: 14,
                borderRadius: "3px",
                bgcolor: colorMap[name].bg,
                border: `2px solid ${colorMap[name].border}`,
              }}
            />
            <Typography
              variant="caption"
              sx={{
                fontWeight: 600,
                color: "text.secondary",
                textTransform: "capitalize",
              }}
            >
              {name}
            </Typography>
          </Box>
        ))}
      </Box>

      {/* Chart */}
      <Box
        sx={{
          position: "relative",
          minWidth: chartWidth + LABEL_WIDTH + 20,
        }}
      >
        {/* Time axis header */}
        <Box
          sx={{
            display: "flex",
            ml: `${LABEL_WIDTH}px`,
            mb: 1,
            position: "relative",
            height: 24,
          }}
        >
          {timeMarkers.map((t) => (
            <Typography
              key={t}
              variant="caption"
              sx={{
                position: "absolute",
                left: `${(t / makespan) * chartWidth}px`,
                transform: "translateX(-50%)",
                color: "text.disabled",
                fontSize: "0.7rem",
                fontWeight: 500,
              }}
            >
              {formatTime(t)}
            </Typography>
          ))}
        </Box>

        {/* Lanes */}
        {laneNames.map((laneName, laneIdx) => {
          const laneSteps = lanes[laneName] || [];
          return (
            <Box
              key={laneName}
              sx={{
                display: "flex",
                alignItems: "center",
                mb: `${LANE_GAP}px`,
                height: `${LANE_HEIGHT}px`,
              }}
            >
              {/* Lane label */}
              <Box
                sx={{
                  width: `${LABEL_WIDTH}px`,
                  flexShrink: 0,
                  pr: 2,
                  textAlign: "right",
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: laneName === "Vous" ? 700 : 500,
                    color: laneName === "Vous" ? "text.primary" : "text.secondary",
                    fontSize: "0.85rem",
                  }}
                >
                  {laneName}
                </Typography>
              </Box>

              {/* Lane track */}
              <Box
                sx={{
                  position: "relative",
                  width: `${chartWidth}px`,
                  height: "100%",
                  bgcolor: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)",
                  borderRadius: "6px",
                  border: "1px solid",
                  borderColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
                }}
              >
                {/* Time grid lines */}
                {timeMarkers.map((t) => (
                  <Box
                    key={t}
                    sx={{
                      position: "absolute",
                      left: `${(t / makespan) * 100}%`,
                      top: 0,
                      bottom: 0,
                      width: "1px",
                      bgcolor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
                    }}
                  />
                ))}

                {/* Step blocks */}
                {laneSteps.map((step, stepIdx) => {
                  const left = (step.start / makespan) * 100;
                  const width = ((step.end - step.start) / makespan) * 100;
                  const colors = colorMap[step.subRecipeTitle] || colorPalette[0];

                  return (
                    <Tooltip
                      key={step.id || stepIdx}
                      title={
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {step.action}
                          </Typography>
                          <Typography variant="caption">
                            {formatTime(step.durationMin)}
                            {step.isPassive ? " (passif)" : " (actif)"}
                          </Typography>
                          {step.visualCue && (
                            <Typography variant="caption" sx={{ display: "block", fontStyle: "italic" }}>
                              {step.visualCue}
                            </Typography>
                          )}
                        </Box>
                      }
                      arrow
                      placement="top"
                    >
                      <Box
                        sx={{
                          position: "absolute",
                          left: `${left}%`,
                          width: `${Math.max(width, 1)}%`,
                          top: "6px",
                          bottom: "6px",
                          bgcolor: colors.bg,
                          border: `1.5px solid ${colors.border}`,
                          borderRadius: "4px",
                          display: "flex",
                          alignItems: "center",
                          px: 1,
                          overflow: "hidden",
                          cursor: "pointer",
                          transition: "transform 0.15s, box-shadow 0.15s",
                          "&:hover": {
                            transform: "scaleY(1.08)",
                            boxShadow: `0 2px 8px ${colors.border}40`,
                            zIndex: 10,
                          },
                          ...(step.isPassive && {
                            backgroundImage: `repeating-linear-gradient(
                              45deg,
                              transparent,
                              transparent 4px,
                              ${colors.border}15 4px,
                              ${colors.border}15 8px
                            )`,
                          }),
                        }}
                      >
                        <Typography
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: colors.text,
                            fontSize: "0.7rem",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            lineHeight: 1.2,
                          }}
                        >
                          {step.action?.substring(0, 50)}
                        </Typography>
                      </Box>
                    </Tooltip>
                  );
                })}
              </Box>
            </Box>
          );
        })}

        {/* Total time */}
        <Box sx={{ ml: `${LABEL_WIDTH}px`, mt: 2, display: "flex", gap: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Temps total : <strong>{formatTime(makespan)}</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {laneNames.length - 1} postes en parallèle
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default GanttContent;
