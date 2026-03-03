import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
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

const CookingMode = ({ title }) => {
  const { t } = useTranslation();
  const { recipe } = useRecipe();
  const theme = useTheme();

  const allSteps = useMemo(() => flattenSteps(recipe), [recipe]);
  const multiSub = useMemo(
    () => checkMultipleSubRecipes(allSteps),
    [allSteps]
  );
  const [currentIdx, setCurrentIdx] = useState(0);
  const [completedSteps, setCompletedSteps] = useState(new Set());
  const [slideKey, setSlideKey] = useState(0);

  const step = allSteps[currentIdx] || null;

  const actionText = step?.action || "";
  const hasTime = hasExplicitTimeMention(actionText, step?.isPassive);
  const rawDuration = step?.time || step?.duration || null;
  const parsedMin = rawDuration ? parseTimeToMinutes(rawDuration) : 0;
  const hasDuration = hasTime && parsedMin > 0;
  const timer = useTimer(hasDuration ? parsedMin : 0);

  const remainingTime = useMemo(
    () => estimateRemainingTime(allSteps, currentIdx),
    [allSteps, currentIdx]
  );
  const remainingLabel = formatRemainingTime(remainingTime);

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

  if (!step) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">{t("cooking.noSteps")}</Typography>
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
      <Box sx={{ flexShrink: 0, pt: 1.5, px: { xs: 2, md: 3 } }}>
        {title && (
          <Typography
            sx={{
              fontSize: "0.72rem",
              fontWeight: 500,
              color: "text.disabled",
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              mb: 1,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              pr: 5,
            }}
          >
            {title}
          </Typography>
        )}
        <StepProgress
          steps={allSteps}
          currentIdx={currentIdx}
          completedSteps={completedSteps}
          onStepClick={navigateTo}
        />
      </Box>

      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "auto",
          px: { xs: 2.5, md: 5 },
          py: 2,
        }}
      >
        <StepContent
          step={step}
          timer={timer}
          hasDuration={hasDuration}
          slideKey={slideKey}
          isCompleted={isCompleted}
          showSubRecipeTitle={multiSub}
          language={recipe?.metadata?.language}
        />
      </Box>

      <Box
        sx={{
          px: { xs: 2, md: 3 },
          pb: { xs: 2, md: 2.5 },
          pt: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
        }}
      >
        <IconButton
          onClick={handlePrev}
          disabled={currentIdx === 0}
          sx={{
            width: 40,
            height: 40,
            flexShrink: 0,
            color: "text.disabled",
            "&:hover": { color: "text.secondary", bgcolor: "action.hover" },
            "&.Mui-disabled": { opacity: 0.2 },
            transition: "all 0.2s ease",
          }}
        >
          <ArrowBackIcon sx={{ fontSize: 18 }} />
        </IconButton>

        <Typography
          sx={{
            fontSize: "0.7rem",
            fontWeight: 500,
            color: "text.disabled",
            letterSpacing: "0.06em",
            fontVariantNumeric: "tabular-nums",
            minWidth: 80,
            textAlign: "center",
          }}
        >
          {currentIdx + 1} / {allSteps.length}
          {remainingLabel ? ` · ${remainingLabel}` : ""}
        </Typography>

        <Button
          endIcon={
            isLastStep ? (
              <CheckCircleOutlineIcon sx={{ fontSize: 16 }} />
            ) : (
              <ArrowForwardIcon sx={{ fontSize: 16 }} />
            )
          }
          onClick={handleNext}
          sx={{
            textTransform: "none",
            fontWeight: 600,
            fontSize: "0.82rem",
            px: 2.5,
            py: 1,
            minWidth: 120,
            borderRadius: "10px",
            flexShrink: 0,
            color: isLastStep ? "#fff" : "text.primary",
            bgcolor: isLastStep
              ? "rgba(76, 175, 80, 0.9)"
              : (t) =>
                  t.palette.mode === "light"
                    ? "rgba(0, 0, 0, 0.06)"
                    : "rgba(255, 255, 255, 0.07)",
            "&:hover": {
              bgcolor: isLastStep
                ? "rgba(76, 175, 80, 1)"
                : (t) =>
                    t.palette.mode === "light"
                      ? "rgba(0, 0, 0, 0.10)"
                      : "rgba(255, 255, 255, 0.12)",
            },
            transition: "all 0.2s ease",
          }}
        >
          {isLastStep ? t("cooking.finish") : t("cooking.next")}
        </Button>
      </Box>
    </Box>
  );
};

export default CookingMode;
