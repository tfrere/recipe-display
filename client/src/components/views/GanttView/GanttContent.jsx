import React, { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Tooltip, useTheme } from "@mui/material";
import { alpha } from "@mui/material/styles";
import AccessTimeFilledIcon from "@mui/icons-material/AccessTimeFilled";
import { useRecipe } from "../../../contexts/RecipeContext";
import { parseTimeToMinutes } from "../../../utils/timeUtils";

/* ─── Scheduling engine ─── */

const computeSchedule = (recipe) => {
  if (!recipe?.subRecipes)
    return { lanes: {}, makespan: 0, steps: [], activeTime: 0, passiveTime: 0 };

  const allSteps = [];
  (recipe.subRecipes || []).forEach((sr) => {
    (sr.steps || []).forEach((step) => {
      if (!step) return;
      allSteps.push({
        ...step,
        subRecipeTitle: sr.title || sr.id || "main",
        durationMin: step.time
          ? parseTimeToMinutes(step.time)
          : step.duration
            ? parseTimeToMinutes(step.duration)
            : 3,
      });
    });
  });

  const stateProducer = {};
  allSteps.forEach((step, i) => {
    if (step.produces) stateProducer[step.produces] = i;
  });

  const scheduled = allSteps.map(() => null);
  const laneEndTimes = {};

  const getStepLane = (step) =>
    step.isPassive || step.stepMode === "passive" ? step.subRecipeTitle : "__you__";

  const computeStart = (idx) => {
    if (scheduled[idx] !== null) return scheduled[idx].start;
    const step = allSteps[idx];
    let earliest = 0;

    [...(step.uses || []), ...(step.requires || [])].forEach((ref) => {
      if (stateProducer[ref] !== undefined) {
        const depIdx = stateProducer[ref];
        earliest = Math.max(earliest, computeStart(depIdx) + allSteps[depIdx].durationMin);
      }
    });

    const lane = getStepLane(step);
    earliest = Math.max(earliest, laneEndTimes[lane] || 0);

    scheduled[idx] = { start: earliest, end: earliest + step.durationMin, lane };
    laneEndTimes[lane] = earliest + step.durationMin;
    return earliest;
  };

  allSteps.forEach((_, i) => computeStart(i));

  const lanes = {};
  let makespan = 0;
  let activeTime = 0;
  let passiveTime = 0;

  const stepsWithSchedule = allSteps.map((step, i) => {
    const sched = scheduled[i];
    if (!lanes[sched.lane]) lanes[sched.lane] = [];
    const entry = { ...step, start: sched.start, end: sched.end, lane: sched.lane, _index: i };
    lanes[sched.lane].push(entry);
    makespan = Math.max(makespan, sched.end);
    if (step.isPassive || step.stepMode === "passive") {
      passiveTime += step.durationMin;
    } else {
      activeTime += step.durationMin;
    }
    return entry;
  });

  return { lanes, makespan, steps: stepsWithSchedule, activeTime, passiveTime };
};

/* ─── Constants & palettes ─── */

const SUB_RECIPE_COLORS = [
  { bg: "#EEF2FF", border: "#818CF8", text: "#4338CA", hover: "#E0E7FF" },
  { bg: "#FEF2F2", border: "#F87171", text: "#DC2626", hover: "#FEE2E2" },
  { bg: "#ECFDF5", border: "#34D399", text: "#059669", hover: "#D1FAE5" },
  { bg: "#FFF7ED", border: "#FB923C", text: "#EA580C", hover: "#FFEDD5" },
  { bg: "#FAF5FF", border: "#C084FC", text: "#9333EA", hover: "#F3E8FF" },
  { bg: "#ECFEFF", border: "#22D3EE", text: "#0891B2", hover: "#CFFAFE" },
  { bg: "#FEFCE8", border: "#FACC15", text: "#CA8A04", hover: "#FEF9C3" },
];

const SUB_RECIPE_COLORS_DARK = [
  { bg: "#1E1B4B", border: "#818CF8", text: "#C7D2FE", hover: "#272368" },
  { bg: "#450A0A", border: "#F87171", text: "#FECACA", hover: "#5C1010" },
  { bg: "#022C22", border: "#34D399", text: "#A7F3D0", hover: "#053D2E" },
  { bg: "#431407", border: "#FB923C", text: "#FED7AA", hover: "#5A1D0C" },
  { bg: "#2E1065", border: "#C084FC", text: "#DDD6FE", hover: "#3B1580" },
  { bg: "#083344", border: "#22D3EE", text: "#A5F3FC", hover: "#0C4358" },
  { bg: "#422006", border: "#FACC15", text: "#FEF08A", hover: "#553009" },
];

const STEP_TYPE_COLORS = {
  prep: "#6366F1",
  cook: "#EF4444",
  combine: "#10B981",
  rest: "#8B5CF6",
  serve: "#F59E0B",
};

const formatTime = (minutes) => {
  if (minutes < 60) return `${Math.round(minutes)}min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m > 0 ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
};

const LANE_HEIGHT = 56;
const LANE_GAP = 6;
const TIME_AXIS_HEIGHT = 22;
const BASE_PX_PER_MIN = 12;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 4;

const scrollbarSx = (isDark) => ({
  "&::-webkit-scrollbar": { height: 6 },
  "&::-webkit-scrollbar-track": { bgcolor: "transparent" },
  "&::-webkit-scrollbar-thumb": {
    borderRadius: 3,
    bgcolor: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)",
    "&:hover": {
      bgcolor: isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.2)",
    },
  },
  scrollbarWidth: "thin",
  scrollbarColor: isDark
    ? "rgba(255,255,255,0.12) transparent"
    : "rgba(0,0,0,0.12) transparent",
});

/* ─── Sub-components ─── */

const GanttSummary = ({ makespan, activeTime, passiveTime, isDark, t }) => {
  const parts = [];
  if (activeTime > 0) parts.push(`${formatTime(activeTime)} ${t("gantt.activeLabel")}`);
  if (passiveTime > 0) parts.push(`${formatTime(passiveTime)} ${t("gantt.passiveLabel")}`);

  return (
    <Box sx={{ display: "flex", alignItems: "center", mb: 1.5, gap: 1 }}>
      <Typography
        variant="body2"
        sx={{ fontWeight: 700, fontSize: "0.88rem", whiteSpace: "nowrap" }}
      >
        {formatTime(makespan)}
      </Typography>
      {parts.length > 0 && (
        <Typography
          variant="caption"
          sx={{ color: "text.disabled", fontSize: "0.68rem", whiteSpace: "nowrap" }}
        >
          ({parts.join(" · ")})
        </Typography>
      )}
      <Typography
        variant="caption"
        sx={{ ml: "auto", color: "text.disabled", fontSize: "0.58rem", whiteSpace: "nowrap" }}
      >
        {t("gantt.zoomHint", { defaultValue: "Ctrl + scroll to zoom · Alt + drag to pan" })}
      </Typography>
    </Box>
  );
};


const StepTooltipContent = ({ step, colors, isDark, t }) => {
  const isPassive = step.isPassive || step.stepMode === "passive";
  const typeColor = STEP_TYPE_COLORS[step.stepType] || "#6B7280";

  return (
    <Box sx={{ maxWidth: 320, p: 0.5 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.82rem", mb: 0.75, lineHeight: 1.5 }}>
        {step.action}
      </Typography>

      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mb: step.visualCue ? 1 : 0.25 }}>
        <Box
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: 0.4,
            px: 0.75,
            py: 0.15,
            borderRadius: 0.75,
            bgcolor: "rgba(255,255,255,0.1)",
            fontSize: "0.68rem",
            fontWeight: 600,
          }}
        >
          <AccessTimeFilledIcon sx={{ fontSize: 10 }} />
          {formatTime(step.durationMin)}
        </Box>
        {step.stepType && (
          <Box
            sx={{
              display: "inline-flex",
              alignItems: "center",
              gap: 0.4,
              px: 0.75,
              py: 0.15,
              borderRadius: 0.75,
              bgcolor: alpha(typeColor, 0.25),
              color: typeColor,
              fontSize: "0.68rem",
              fontWeight: 600,
              textTransform: "capitalize",
            }}
          >
            <Box sx={{ width: 5, height: 5, borderRadius: "50%", bgcolor: typeColor }} />
            {step.stepType}
          </Box>
        )}
        <Box
          sx={{
            px: 0.75,
            py: 0.15,
            borderRadius: 0.75,
            bgcolor: isPassive ? alpha("#8B5CF6", 0.2) : alpha("#10B981", 0.2),
            color: isPassive ? "#C4B5FD" : "#6EE7B7",
            fontSize: "0.68rem",
            fontWeight: 600,
          }}
        >
          {isPassive ? t("gantt.passive") : t("gantt.active")}
        </Box>
      </Box>

      {step.visualCue && (
        <Typography
          sx={{
            fontStyle: "italic",
            fontSize: "0.75rem",
            opacity: 0.8,
            lineHeight: 1.4,
            pl: 1,
            borderLeft: "2px solid",
            borderColor: colors.border,
            mb: 0.5,
          }}
        >
          {step.visualCue}
        </Typography>
      )}

      <Typography sx={{ fontSize: "0.65rem", opacity: 0.5, mt: 0.5 }}>
        {formatTime(step.start)} → {formatTime(step.end)}
      </Typography>
    </Box>
  );
};

const StepBlock = ({ step, left, width, colors, isDark, label, hasMultipleSubs }) => {
  const { t } = useTranslation();
  const isPassive = step.isPassive || step.stepMode === "passive";

  return (
    <Tooltip
      title={<StepTooltipContent step={step} colors={colors} isDark={isDark} t={t} />}
      placement="top"
      arrow
      enterDelay={200}
      leaveDelay={100}
      slotProps={{
        tooltip: {
          sx: {
            bgcolor: isDark ? "#1E293B" : "#1E293B",
            color: "#F1F5F9",
            borderRadius: 2,
            p: 1.5,
            boxShadow: "0 8px 32px rgba(0,0,0,0.35)",
            maxWidth: 340,
            "& .MuiTooltip-arrow": {
              color: "#1E293B",
            },
          },
        },
      }}
    >
      <Box
        sx={{
          position: "absolute",
          left: `${left}%`,
          width: `${Math.max(width, 1.5)}%`,
          top: "4px",
          bottom: "4px",
          bgcolor: isPassive
            ? alpha(colors.border, isDark ? 0.08 : 0.05)
            : colors.bg,
          border: `1.5px ${isPassive ? "dashed" : "solid"} ${colors.border}`,
          borderRadius: "6px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          px: 0.75,
          py: 0.25,
          overflow: "hidden",
          cursor: "pointer",
          transition: "all 0.15s ease",
          boxSizing: "border-box",
          "&:hover": {
            boxShadow: `0 2px 8px ${isDark ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0.1)"}`,
            zIndex: 10,
            bgcolor: isPassive
              ? alpha(colors.border, isDark ? 0.15 : 0.1)
              : colors.hover,
          },
        }}
      >
        <Typography
          variant="caption"
          sx={{
            fontWeight: 600,
            color: colors.text,
            fontSize: "0.66rem",
            lineHeight: 1.25,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            textTransform: hasMultipleSubs ? "capitalize" : "none",
          }}
        >
          {label}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontSize: "0.56rem",
            color: alpha(colors.text, isDark ? 0.5 : 0.4),
            fontWeight: 500,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {formatTime(step.durationMin)}
        </Typography>
      </Box>
    </Tooltip>
  );
};

const GanttChart = ({
  lanes,
  laneNames,
  makespan,
  colorMap,
  colorPalette,
  subRecipeNames,
  timeMarkers,
  isDark,
  zoom,
}) => {
  const chartWidth = Math.max(650, makespan * BASE_PX_PER_MIN * zoom);
  const hasMultipleSubs = subRecipeNames.length > 1;

  return (
    <Box sx={{ width: chartWidth, minWidth: "100%" }}>
      {/* Time axis */}
      <Box sx={{ position: "relative", height: TIME_AXIS_HEIGHT }}>
        {timeMarkers.map((m) => (
          <Typography
            key={m}
            variant="caption"
            sx={{
              position: "absolute",
              left: `${(m / makespan) * 100}%`,
              transform: "translateX(-50%)",
              color: "text.disabled",
              fontSize: "0.63rem",
              fontWeight: 500,
              userSelect: "none",
              whiteSpace: "nowrap",
            }}
          >
            {formatTime(m)}
          </Typography>
        ))}
      </Box>

      {/* Lane tracks */}
      {laneNames.map((laneName) => {
        const laneSteps = lanes[laneName] || [];
        const isYou = laneName === "__you__";

        return (
          <Box
            key={laneName}
            sx={{
              position: "relative",
              height: LANE_HEIGHT,
              mb: `${LANE_GAP}px`,
              bgcolor: isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.012)",
              borderRadius: "8px",
              border: "1px solid",
              borderColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
              ...(isYou && {
                bgcolor: isDark ? "rgba(255,255,255,0.035)" : "rgba(0,0,0,0.022)",
                borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
              }),
            }}
          >
            {/* Grid lines */}
            {timeMarkers.map((m) => (
              <Box
                key={m}
                sx={{
                  position: "absolute",
                  left: `${(m / makespan) * 100}%`,
                  top: 0,
                  bottom: 0,
                  width: "1px",
                  bgcolor: isDark ? "rgba(255,255,255,0.035)" : "rgba(0,0,0,0.035)",
                }}
              />
            ))}

            {/* Step blocks */}
            {laneSteps.map((step, stepIdx) => {
              const left = (step.start / makespan) * 100;
              const width = ((step.end - step.start) / makespan) * 100;
              const colors = colorMap[step.subRecipeTitle] || colorPalette[0];

              const label = hasMultipleSubs
                ? step.subRecipeTitle
                : step.action?.split(/[.,;!?]/).filter(Boolean)[0] || step.action;

              return (
                <StepBlock
                  key={step.id || stepIdx}
                  step={step}
                  left={left}
                  width={width}
                  colors={colors}
                  isDark={isDark}
                  label={label}
                  hasMultipleSubs={hasMultipleSubs}
                />
              );
            })}
          </Box>
        );
      })}
    </Box>
  );
};

/* ─── Main component ─── */

const GanttContent = () => {
  const { t } = useTranslation();
  const { recipe } = useRecipe();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  const scrollRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, scrollLeft: 0 });

  const { lanes, makespan, activeTime, passiveTime } = useMemo(() => {
    if (!recipe) return { lanes: {}, makespan: 0, steps: [], activeTime: 0, passiveTime: 0 };
    return computeSchedule(recipe);
  }, [recipe]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const onWheel = (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();

      const rect = el.getBoundingClientRect();
      const pointerX = e.clientX - rect.left + el.scrollLeft;
      const oldZoom = zoomRef.current;
      const delta = e.deltaY > 0 ? -0.15 : 0.15;
      const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, oldZoom + delta));

      setZoom(newZoom);

      requestAnimationFrame(() => {
        const scale = newZoom / oldZoom;
        el.scrollLeft = pointerX * scale - (e.clientX - rect.left);
      });
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const handlePointerDown = useCallback((e) => {
    if (e.button !== 1 && !(e.button === 0 && e.altKey)) return;
    e.preventDefault();
    const container = scrollRef.current;
    if (!container) return;
    isPanning.current = true;
    panStart.current = { x: e.clientX, scrollLeft: container.scrollLeft };
    container.style.cursor = "grabbing";
    container.setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback((e) => {
    if (!isPanning.current) return;
    const container = scrollRef.current;
    if (!container) return;
    container.scrollLeft = panStart.current.scrollLeft - (e.clientX - panStart.current.x);
  }, []);

  const handlePointerUp = useCallback((e) => {
    if (!isPanning.current) return;
    isPanning.current = false;
    const container = scrollRef.current;
    if (container) {
      container.style.cursor = "";
      container.releasePointerCapture(e.pointerId);
    }
  }, []);

  if (!recipe || makespan === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">{t("gantt.noData")}</Typography>
      </Box>
    );
  }

  const colorPalette = isDark ? SUB_RECIPE_COLORS_DARK : SUB_RECIPE_COLORS;
  const subRecipeNames = [...new Set(Object.values(lanes).flat().map((s) => s.subRecipeTitle))];
  const colorMap = {};
  subRecipeNames.forEach((name, i) => {
    colorMap[name] = colorPalette[i % colorPalette.length];
  });

  const laneNames = Object.keys(lanes).sort((a, b) => {
    if (a === "__you__") return -1;
    if (b === "__you__") return 1;
    return a.localeCompare(b);
  });

  const interval = makespan <= 30 ? 5 : makespan <= 90 ? 10 : 15;
  const timeMarkers = [];
  for (let m = 0; m <= makespan; m += interval) timeMarkers.push(m);
  if (timeMarkers[timeMarkers.length - 1] < makespan) timeMarkers.push(makespan);

  return (
    <Box sx={{ px: 3, pb: 3, pt: 1.5 }}>
      <GanttSummary
        makespan={makespan}
        activeTime={activeTime}
        passiveTime={passiveTime}
        isDark={isDark}
        t={t}
      />

      <Box
        ref={scrollRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        sx={{
          overflowX: "auto",
          overflowY: "hidden",
          pb: 1,
          ...scrollbarSx(isDark),
        }}
      >
        <GanttChart
          lanes={lanes}
          laneNames={laneNames}
          makespan={makespan}
          colorMap={colorMap}
          colorPalette={colorPalette}
          subRecipeNames={subRecipeNames}
          timeMarkers={timeMarkers}
          isDark={isDark}
          zoom={zoom}
        />
      </Box>
    </Box>
  );
};

export default GanttContent;
