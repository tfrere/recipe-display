import React from "react";
import { Typography } from "@mui/material";
import {
  parseTimeToMinutes,
  formatTime,
  formatTimeCompact,
  roundToNearestFive,
} from "../../utils/timeUtils";

const TimeDisplay = ({
  timeString,
  minutes,
  variant = "body2",
  component = "span",
  sx = {},
  detailed = false,
  compact = true,
  ...props
}) => {
  let timeInMinutes = minutes;

  if (timeString) {
    // Si timeString est un nombre, on l'utilise directement
    timeInMinutes =
      typeof timeString === "number"
        ? timeString
        : parseTimeToMinutes(timeString);

    // Arrondir à 5 minutes près seulement si la valeur vient de timeString
    timeInMinutes = roundToNearestFive(timeInMinutes);
  }

  if (!timeInMinutes) return null;

  return (
    <Typography variant={variant} component={component} sx={sx} {...props}>
      {compact
        ? formatTimeCompact(timeInMinutes)
        : formatTime(timeInMinutes, detailed)}
    </Typography>
  );
};

export default TimeDisplay;
