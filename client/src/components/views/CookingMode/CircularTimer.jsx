import React from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, IconButton, CircularProgress, useTheme } from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { formatTimerDisplay } from "./utils";

const CircularTimer = ({ timer }) => {
  const { t } = useTranslation();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const size = 140;
  const thickness = 2.5;

  const timerColor = timer.isFinished
    ? "#4caf50"
    : timer.isRunning
    ? "#2196f3"
    : theme.palette.text.disabled;

  const trackColor = isDark
    ? "rgba(255,255,255,0.04)"
    : "rgba(0,0,0,0.05)";

  return (
    <Box
      sx={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 1.5,
      }}
    >
      <Box sx={{ position: "relative", width: size, height: size }}>
        <CircularProgress
          variant="determinate"
          value={100}
          size={size}
          thickness={thickness}
          sx={{ position: "absolute", color: trackColor }}
        />
        <CircularProgress
          variant="determinate"
          value={timer.progress}
          size={size}
          thickness={thickness}
          sx={{
            position: "absolute",
            color: timerColor,
            transition: "color 0.3s ease",
            "& .MuiCircularProgress-circle": {
              strokeLinecap: "round",
              transition: "stroke-dashoffset 0.5s ease",
            },
          }}
        />
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography
            sx={{
              fontFamily: "'SF Mono', 'Fira Code', 'Consolas', monospace",
              fontWeight: 600,
              fontSize: "1.75rem",
              letterSpacing: "0.02em",
              color: timer.isFinished ? "#4caf50" : "text.primary",
              lineHeight: 1,
            }}
          >
            {formatTimerDisplay(timer.remainingSeconds)}
          </Typography>
          {timer.isFinished && (
            <Typography
              sx={{
                fontSize: "0.6rem",
                fontWeight: 700,
                color: "#4caf50",
                mt: 0.5,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              {t("cooking.timerDone")}
            </Typography>
          )}
        </Box>
      </Box>

      <Box sx={{ display: "flex", gap: 0.75 }}>
        <IconButton
          onClick={timer.toggle}
          sx={{
            width: 38,
            height: 38,
            bgcolor: timer.isRunning
              ? "rgba(244,67,54,0.12)"
              : "rgba(33,150,243,0.12)",
            color: timer.isRunning ? "#f44336" : "#2196f3",
            "&:hover": {
              bgcolor: timer.isRunning
                ? "rgba(244,67,54,0.2)"
                : "rgba(33,150,243,0.2)",
            },
          }}
        >
          {timer.isRunning ? (
            <PauseIcon sx={{ fontSize: 20 }} />
          ) : (
            <PlayArrowIcon sx={{ fontSize: 20 }} />
          )}
        </IconButton>
        <IconButton
          onClick={timer.reset}
          sx={{
            width: 38,
            height: 38,
            bgcolor: isDark
              ? "rgba(255,255,255,0.04)"
              : "rgba(0,0,0,0.04)",
            color: "text.disabled",
            "&:hover": {
              bgcolor: isDark
                ? "rgba(255,255,255,0.08)"
                : "rgba(0,0,0,0.08)",
              color: "text.secondary",
            },
          }}
        >
          <RestartAltIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </Box>
    </Box>
  );
};

export default CircularTimer;
