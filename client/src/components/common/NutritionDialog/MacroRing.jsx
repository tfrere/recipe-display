import React, { useId } from "react";
import { Box } from "@mui/material";
import { pie, arc } from "d3-shape";
import { MACRO_COLORS } from "./constants";

const SIZE = 120;
const OUTER_RADIUS = 56;
const INNER_RADIUS = 32;
const PAD_ANGLE = 0.04;
const CORNER_RADIUS = 4;

const pieLayout = pie()
  .sort(null)
  .padAngle(PAD_ANGLE)
  .value((d) => d.value);

const arcPath = arc()
  .innerRadius(INNER_RADIUS)
  .outerRadius(OUTER_RADIUS)
  .cornerRadius(CORNER_RADIUS);

const REVEAL_R = OUTER_RADIUS;
const REVEAL_STROKE = OUTER_RADIUS * 2;
const CIRCUMFERENCE = 2 * Math.PI * REVEAL_R;

const MacroRing = ({ protein, carbs, fat, confidence }) => {
  const clipId = useId();
  const total = (protein || 0) * 4 + (carbs || 0) * 4 + (fat || 0) * 9;
  if (total === 0) return null;

  const isLow = confidence === "low";
  const finalOpacity = isLow ? 0.4 : 0.85;

  const data = [
    { value: (protein || 0) * 4, color: MACRO_COLORS.protein },
    { value: (carbs || 0) * 4, color: MACRO_COLORS.carbs },
    { value: (fat || 0) * 9, color: MACRO_COLORS.fat },
  ].filter((d) => d.value > 0);

  const slices = pieLayout(data);
  const center = SIZE / 2;

  return (
    <Box sx={{ width: SIZE, height: SIZE, flexShrink: 0 }}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width={SIZE} height={SIZE}>
        <defs>
          <clipPath id={clipId}>
            <circle
              cx={center}
              cy={center}
              r={REVEAL_R}
              fill="none"
              stroke="white"
              strokeWidth={REVEAL_STROKE}
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={CIRCUMFERENCE}
              transform={`rotate(-90 ${center} ${center})`}
            >
              <animate
                attributeName="stroke-dashoffset"
                from={CIRCUMFERENCE}
                to="0"
                dur="0.55s"
                fill="freeze"
                calcMode="spline"
                keySplines="0.25 0.1 0.25 1"
                keyTimes="0;1"
              />
            </circle>
          </clipPath>
        </defs>
        <g clipPath={`url(#${clipId})`}>
          <g transform={`translate(${center}, ${center})`}>
            {slices.map((s, i) => (
              <path
                key={i}
                d={arcPath(s)}
                fill={s.data.color}
                style={{ opacity: finalOpacity }}
              />
            ))}
          </g>
        </g>
      </svg>
    </Box>
  );
};

export default MacroRing;
