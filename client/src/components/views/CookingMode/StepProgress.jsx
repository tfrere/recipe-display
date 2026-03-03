import React, { useMemo } from "react";
import { Box, Typography, useTheme } from "@mui/material";
import { groupStepsBySubRecipe } from "./utils";

const StepProgress = ({ steps, currentIdx, completedSteps, onStepClick }) => {
  const theme = useTheme();
  const groups = useMemo(() => groupStepsBySubRecipe(steps), [steps]);
  const isDark = theme.palette.mode === "dark";

  const barColor = {
    active: isDark ? "#fff" : theme.palette.text.primary,
    done: theme.palette.text.secondary,
    idle: theme.palette.divider,
    hoverIdle: isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.16)",
    hoverDone: isDark ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.42)",
    glow: isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.08)",
  };

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1.5,
        width: "100%",
        alignItems: "flex-end",
      }}
    >
      {groups.map((group, gi) => {
        const hasCurrent = group.steps.some((s) => s.globalIdx === currentIdx);

        return (
          <Box
            key={gi}
            sx={{
              flex: group.steps.length,
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              minWidth: 0,
            }}
          >
            <Typography
              sx={{
                fontSize: "0.58rem",
                fontWeight: 500,
                color: hasCurrent ? "text.secondary" : "text.disabled",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                lineHeight: 1,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                transition: "color 0.3s ease",
              }}
            >
              {group.title}
            </Typography>

            <Box sx={{ display: "flex", gap: "3px", alignItems: "center" }}>
              {group.steps.map((s) => {
                const i = s.globalIdx;
                const done = completedSteps.has(i);
                const active = i === currentIdx;

                return (
                  <Box
                    key={i}
                    onClick={() => onStepClick(i)}
                    sx={{
                      flex: 1,
                      height: active ? 3 : 2,
                      borderRadius: 2,
                      cursor: "pointer",
                      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                      bgcolor: done
                        ? barColor.done
                        : active
                        ? barColor.active
                        : barColor.idle,
                      boxShadow: active
                        ? `0 0 6px ${barColor.glow}`
                        : "none",
                      "&:hover": {
                        transform: active ? "none" : "scaleY(2)",
                        bgcolor: done
                          ? barColor.hoverDone
                          : active
                          ? barColor.active
                          : barColor.hoverIdle,
                      },
                    }}
                  />
                );
              })}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
};

export default StepProgress;
