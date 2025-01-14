import React from "react";
import { Typography } from "@mui/material";
import { parseTimeToMinutes, formatTime } from "../../utils/timeUtils";

const TimeDisplay = ({
  timeString,
  minutes,
  variant = "body2",
  component = "span",
  sx = {},
  detailed = false,
  ...props
}) => {
  let timeInMinutes = minutes;

  if (timeString) {
    // Si timeString est un nombre, on l'utilise directement
    timeInMinutes =
      typeof timeString === "number"
        ? timeString
        : parseTimeToMinutes(timeString);
  }

  if (!timeInMinutes) return null;

  return (
    <Typography variant={variant} component={component} sx={sx} {...props}>
      {formatTime(timeInMinutes, detailed)}
    </Typography>
  );
};

export default TimeDisplay;
