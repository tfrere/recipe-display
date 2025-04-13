import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Chip,
  Divider,
  Paper,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useElapsedTime } from "../../../hooks/useElapsedTime";
import { useAutoScroll } from "../../../hooks/useAutoScroll";

const STATUS_COLORS = {
  completed: "success",
  in_progress: "primary",
  error: "error",
  pending: "default",
};

const StepDetails = ({ details, onScroll, scrollRef, theme }) => (
  <Box
    ref={scrollRef}
    onScroll={onScroll}
    sx={{
      height: "10em",
      overflowY: "auto",
      p: 2,
      bgcolor: theme.palette.mode === "dark" ? "grey.800" : "grey.100",
      borderRadius: 1,
      mx: 2,
      mb: 2,
      border: 1,
      borderColor: theme.palette.mode === "dark" ? "grey.700" : "grey.200",
    }}
  >
    <Typography
      variant="body2"
      sx={{
        whiteSpace: "pre-wrap",
        fontFamily: "monospace",
        color: theme.palette.mode === "dark" ? "grey.300" : "grey.900",
        lineHeight: "1.5em",
      }}
    >
      {details}
    </Typography>
  </Box>
);

const TimeChip = ({ elapsedTime, status, theme }) => (
  <Chip
    label={`${elapsedTime}s`}
    size="small"
    color={STATUS_COLORS[status]}
    sx={{
      minWidth: 60,
      fontWeight: 500,
      bgcolor:
        theme.palette.mode === "dark"
          ? status === "completed"
            ? theme.palette.success.dark
            : status === "in_progress"
            ? theme.palette.primary.dark
            : theme.palette.grey[800]
          : status === "completed"
          ? theme.palette.success.light
          : status === "in_progress"
          ? theme.palette.primary.light
          : theme.palette.grey[200],
      color:
        theme.palette.mode === "dark"
          ? theme.palette.common.white
          : status === "completed"
          ? theme.palette.success.dark
          : status === "in_progress"
          ? theme.palette.primary.dark
          : theme.palette.grey[800],
      "& .MuiChip-label": {
        color: "inherit",
      },
    }}
  />
);

const RecipeGenerationStep = ({ step, startTime }) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const theme = useTheme();
  const { autoScroll, elementRef, handleScroll } = useAutoScroll(step.details);

  useEffect(() => {
    let intervalId;

    if (step.status === "in_progress" && step.startedAt) {
      // Calculate elapsed time from step start
      const updateElapsedTime = () => {
        const startDate = new Date(step.startedAt);
        const now = new Date();
        const elapsed = Math.floor((now - startDate) / 1000); // Convert to seconds
        setElapsedTime(elapsed);
      };

      updateElapsedTime(); // Initial calculation
      intervalId = setInterval(updateElapsedTime, 1000);
    } else if (step.status === "completed") {
      // Keep the last elapsed time when step is completed
      const startDate = new Date(step.startedAt);
      const endDate = new Date(); // We could add an endedAt field if we want to be more precise
      const elapsed = Math.floor((endDate - startDate) / 1000);
      setElapsedTime(elapsed);
    } else {
      setElapsedTime(0);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [step.status, step.startedAt]);

  const isActive = step.status === "in_progress";
  const isCompleted = step.status === "completed";
  const isPending = step.status === "pending";

  return (
    <Box>
      <Paper
        elevation={isActive ? 1 : 0}
        sx={{
          opacity: isPending ? 0.5 : 1,
          mb: 2,
          bgcolor: isActive
            ? theme.palette.mode === "dark"
              ? "grey.900"
              : "grey.50"
            : "transparent",
          transition: "all 0.2s ease-in-out",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            width: "100%",
            p: isActive ? 1.5 : 1,
            borderRadius: 1,
          }}
        >
          <CircularProgress
            size={24}
            variant={isActive ? "indeterminate" : "determinate"}
            value={isCompleted ? 100 : 0}
          />
          <Typography
            sx={{
              flex: 1,
              fontWeight: isActive ? 500 : 400,
            }}
          >
            {step.message}
          </Typography>
          {(isActive || isCompleted) && startTime && (
            <TimeChip
              elapsedTime={elapsedTime}
              status={step.status}
              theme={theme}
            />
          )}
        </Box>

        {step.details && (
          <StepDetails
            details={step.details}
            onScroll={handleScroll}
            scrollRef={elementRef}
            theme={theme}
          />
        )}
      </Paper>
      <Divider sx={{ my: 1 }} />
    </Box>
  );
};

export default RecipeGenerationStep;
