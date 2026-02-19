import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Box,
  Typography,
  Button,
  IconButton,
  useTheme,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { useRecipe } from "../../../contexts/RecipeContext";
import { parseTimeToMinutes } from "../../../utils/timeUtils";
import { useTimer } from "./useTimer";
import {
  flattenSteps,
  estimateRemainingTime,
  formatRemainingTime,
  hasExplicitTimeMention,
  hasMultipleSubRecipes as checkMultipleSubRecipes,
} from "./utils";
import StepProgress from "./StepProgress";
import StepContent from "./StepContent";

/* ═══════════════════════════════════════════════════════════════════
   CookingMode — step-by-step cooking guide.

   Design: the instruction dominates. Everything else supports it.
   Progress is ambient, navigation is effortless.
   ═══════════════════════════════════════════════════════════════════ */

const CookingMode = () => {
  const { recipe } = useRecipe();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  const allSteps = useMemo(() => flattenSteps(recipe), [recipe]);
  const multiSub = useMemo(
    () => checkMultipleSubRecipes(allSteps),
    [allSteps]
  );
  const [currentIdx, setCurrentIdx] = useState(0);
  const [completedSteps, setCompletedSteps] = useState(new Set());
  const [slideKey, setSlideKey] = useState(0);

  const step = allSteps[currentIdx] || null;

  /* ── Timer ── */
  const actionText = step?.action || "";
  const hasTime = hasExplicitTimeMention(actionText, step?.isPassive);
  const rawDuration = step?.time || step?.duration || null;
  const parsedMin = rawDuration ? parseTimeToMinutes(rawDuration) : 0;
  const hasDuration = hasTime && parsedMin > 0;
  const timer = useTimer(hasDuration ? parsedMin : 0);

  /* ── Remaining time ── */
  const remainingTime = useMemo(
    () => estimateRemainingTime(allSteps, currentIdx),
    [allSteps, currentIdx]
  );
  const remainingLabel = formatRemainingTime(remainingTime);

  /* ── Navigation ── */
  const navigateTo = useCallback((idx) => {
    setSlideKey((p) => p + 1);
    setCurrentIdx(idx);
  }, []);

  const handleNext = useCallback(() => {
    setCompletedSteps((prev) => new Set([...prev, currentIdx]));
    if (currentIdx < allSteps.length - 1) navigateTo(currentIdx + 1);
  }, [currentIdx, allSteps.length, navigateTo]);

  const handlePrev = useCallback(() => {
    if (currentIdx > 0) navigateTo(currentIdx - 1);
  }, [currentIdx, navigateTo]);

  /* ── Keyboard ── */
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        handleNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrev();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleNext, handlePrev]);

  /* ── Empty ── */
  if (!step) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">No steps available.</Typography>
      </Box>
    );
  }

  const isLastStep = currentIdx === allSteps.length - 1;
  const isCompleted = isLastStep && completedSteps.has(currentIdx);

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* ── Stories-style progress ── */}
      <StepProgress
        steps={allSteps}
        currentIdx={currentIdx}
        completedSteps={completedSteps}
        isDark={isDark}
        onStepClick={navigateTo}
      />

      {/* ── Content (the entire middle is the instruction) ── */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "auto",
          px: { xs: 2, md: 4 },
          py: 1,
        }}
      >
        <StepContent
          step={step}
          timer={timer}
          hasDuration={hasDuration}
          isDark={isDark}
          slideKey={slideKey}
          isCompleted={isCompleted}
          showSubRecipeTitle={multiSub}
        />
      </Box>

      {/* ── Navigation ── */}
      <Box
        sx={{
          px: { xs: 2, md: 3 },
          py: { xs: 1.5, md: 2 },
          display: "flex",
          alignItems: "center",
          gap: 1.5,
        }}
      >
        {/* Previous: small icon button */}
        <IconButton
          onClick={handlePrev}
          disabled={currentIdx === 0}
          sx={{
            width: 44,
            height: 44,
            flexShrink: 0,
            bgcolor: isDark
              ? "rgba(255,255,255,0.05)"
              : "rgba(0,0,0,0.04)",
            color: "text.secondary",
            "&:hover": {
              bgcolor: isDark
                ? "rgba(255,255,255,0.1)"
                : "rgba(0,0,0,0.08)",
            },
            "&.Mui-disabled": { opacity: 0.15 },
          }}
        >
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>

        {/* Center: step counter + remaining */}
        <Box sx={{ flex: 1, textAlign: "center", minWidth: 0 }}>
          <Typography
            sx={{
              fontSize: "0.75rem",
              fontWeight: 500,
              color: "text.disabled",
              letterSpacing: "0.02em",
            }}
          >
            {currentIdx + 1} / {allSteps.length}
            {remainingLabel ? ` \u00B7 ${remainingLabel}` : ""}
          </Typography>
        </Box>

        {/* Next: big primary CTA */}
        <Button
          endIcon={
            isLastStep ? (
              <CheckCircleOutlineIcon sx={{ fontSize: 18 }} />
            ) : (
              <ArrowForwardIcon sx={{ fontSize: 18 }} />
            )
          }
          onClick={handleNext}
          sx={{
            textTransform: "none",
            fontWeight: 600,
            fontSize: "0.88rem",
            px: 3,
            py: 1.25,
            minWidth: { xs: 130, md: 160 },
            borderRadius: "12px",
            flexShrink: 0,
            color: isLastStep
              ? "white"
              : isDark
              ? "rgba(255,255,255,0.9)"
              : "rgba(0,0,0,0.85)",
            bgcolor: isLastStep
              ? "#4caf50"
              : isDark
              ? "rgba(255,255,255,0.08)"
              : "rgba(0,0,0,0.06)",
            "&:hover": {
              bgcolor: isLastStep
                ? "#43a047"
                : isDark
                ? "rgba(255,255,255,0.14)"
                : "rgba(0,0,0,0.1)",
            },
            transition: "all 0.2s ease",
          }}
        >
          {isLastStep ? "Terminer" : "Suivant"}
        </Button>
      </Box>
    </Box>
  );
};

export default CookingMode;
