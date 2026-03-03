import React from "react";
import { useTranslation } from "react-i18next";
import { Box, Tooltip } from "@mui/material";
import TimeDisplay from "./TimeDisplay";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import AlarmIcon from "@mui/icons-material/Alarm";

const RecipeTimes = ({
  totalTime,
  totalCookingTime,
  iconSize = "small",
  sx = { color: "white", fontWeight: 500 },
}) => {
  const { t } = useTranslation();

  return (
    <>
      {totalTime && (
        <Tooltip title={t("recipeTimes.totalTime")} arrow>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <AlarmIcon fontSize={iconSize} sx={{ color: sx.color }} />
            <TimeDisplay minutes={totalTime} variant="body2" sx={sx} />
          </Box>
        </Tooltip>
      )}

      {totalCookingTime && (
        <Tooltip title={t("recipeTimes.activeCookingTime")} arrow>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <LocalFireDepartmentOutlinedIcon
              fontSize={iconSize}
              sx={{ color: sx.color }}
            />
            <TimeDisplay minutes={totalCookingTime} variant="body2" sx={sx} />
          </Box>
        </Tooltip>
      )}
    </>
  );
};

export default RecipeTimes;
