import React, { useMemo } from "react";
import { Box, Typography } from "@mui/material";
import { groupStepsBySubRecipe } from "./utils";

/**
 * Stories-style progress bar with sub-recipe labels.
 * Labels give orientation ("Sauce", "Assemblage"), segments show progress.
 */
const StepProgress = ({
  steps,
  currentIdx,
  completedSteps,
  isDark,
  onStepClick,
}) => {
  const groups = useMemo(() => groupStepsBySubRecipe(steps), [steps]);

  return (
    <Box
      sx={{
        display: "flex",
        gap: 2,
        width: "100%",
        px: 2.5,
        pt: 1,
        pb: 0.5,
        alignItems: "flex-end",
      }}
    >
      {groups.map((group, gi) => {
        const hasCurrent = group.steps.some((s) => s.globalIdx === currentIdx);
        const allDone = group.steps.every((s) =>
          completedSteps.has(s.globalIdx)
        );

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
                fontSize: "0.6rem",
                fontWeight: hasCurrent ? 700 : 500,
                color: allDone
                  ? "#4caf50"
                  : hasCurrent
                  ? "text.secondary"
                  : "text.disabled",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
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
                      height: active ? 7 : 4,
                      borderRadius: active ? 3.5 : 2,
                      cursor: "pointer",
                      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                      bgcolor: done
                        ? "#4caf50"
                        : active
                        ? isDark
                          ? "#fff"
                          : "rgba(0,0,0,0.75)"
                        : isDark
                        ? "rgba(255,255,255,0.12)"
                        : "rgba(0,0,0,0.1)",
                      boxShadow: active
                        ? isDark
                          ? "0 0 8px rgba(255,255,255,0.25)"
                          : "0 0 8px rgba(0,0,0,0.15)"
                        : "none",
                      "&:hover": {
                        transform: active ? "none" : "scaleY(1.8)",
                        bgcolor: done
                          ? "#66bb6a"
                          : active
                          ? isDark
                            ? "#fff"
                            : "rgba(0,0,0,0.85)"
                          : isDark
                          ? "rgba(255,255,255,0.25)"
                          : "rgba(0,0,0,0.2)",
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
