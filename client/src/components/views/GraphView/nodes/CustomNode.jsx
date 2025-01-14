import React, { useEffect, useRef, useState } from "react";
import { Handle, Position } from "reactflow";
import { Box, Typography, useTheme } from "@mui/material";
import { useRecipe } from "../../../../contexts/RecipeContext";
import RecipeChip, { CHIP_TYPES } from "../../../common/RecipeChip";
import {
  parseTimeToMinutes,
  calculateTotalTime,
} from "../../../../utils/timeUtils";

const formatMinutesToTime = (minutes) => {
  if (!minutes) return "";
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours > 0) {
    return `${hours}h${remainingMinutes > 0 ? ` ${remainingMinutes}min` : ""}`;
  }
  return `${remainingMinutes}min`;
};

const getNodeStyle = (type, isCompleted, theme, isUnused = false, height) => {
  const isDark = theme.palette.mode === "dark";

  const baseStyle = {
    padding: type === "action" ? "12px" : "8px",
    width: type === "action" ? "250px" : "120px",
    height: type === "action" ? `${height}px` : "auto",
    minHeight: type === "action" ? "60px" : "60px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    transition: "all 0.2s ease",
    boxShadow: isDark
      ? "0 4px 8px rgba(0,0,0,0.2)"
      : "0 4px 12px rgba(0,0,0,0.08)",
    borderRadius: type === "action" ? "8px" : "4px",
    gap: type === "action" ? "8px" : "2px",
    opacity: isUnused ? 0.6 : 1,
  };

  if (type === "action" && isCompleted) {
    return {
      ...baseStyle,
      backgroundColor: isDark ? "#424242" : "#f5f5f5",
      border: `1px solid ${isDark ? "#757575" : "#e0e0e0"}`,
      opacity: 0.8,
    };
  }

  if (isUnused) {
    return {
      ...baseStyle,
      backgroundColor: isDark ? "#424242" : "#f5f5f5",
      border: `1px solid ${isDark ? "#757575" : "#e0e0e0"}`,
    };
  }

  switch (type) {
    case "ingredient":
      return {
        ...baseStyle,
        backgroundColor:
          theme.palette.mode === "dark"
            ? theme.palette.grey[800]
            : theme.palette.primary.light + "20", // 20 = 12% opacity
        border: `2px solid ${theme.palette.primary.main}`,
      };
    case "action":
      return {
        ...baseStyle,
        backgroundColor: isDark ? "#424242" : "#ffffff",
        border: `1px solid ${theme.palette.divider}`,
        boxShadow: isDark
          ? "0 4px 12px rgba(0,0,0,0.3)"
          : "0 4px 16px rgba(0,0,0,0.1)",
      };
    case "state":
      return {
        ...baseStyle,
        backgroundColor:
          theme.palette.mode === "dark"
            ? theme.palette.grey[800]
            : theme.palette.secondary.light + "20", // 20 = 12% opacity
        border: `2px solid ${theme.palette.secondary.main}`,
      };
    default:
      return baseStyle;
  }
};

export const CustomNode = ({ data }) => {
  const theme = useTheme();
  const {
    label,
    type,
    isCompleted,
    time,
    tools,
    quantity,
    isUnused,
    height,
    state,
  } = data;

  const style = getNodeStyle(type, isCompleted, theme, isUnused, height);
  const timeInMinutes = time ? parseTimeToMinutes(time) : 0;

  const renderContent = () => {
    if (type === "ingredient") {
      return (
        <>
          <Typography
            variant="body2"
            sx={{
              textAlign: "center",
              fontWeight: 500,
              color: theme.palette.text.primary,
            }}
          >
            {label}
          </Typography>
          {quantity && (
            <Typography
              variant="caption"
              sx={{
                textAlign: "center",
                color: theme.palette.text.secondary,
              }}
            >
              {quantity}
            </Typography>
          )}
          {data.state && (
            <Typography
              variant="caption"
              sx={{
                textAlign: "center",
                color: theme.palette.text.secondary,
                fontStyle: "italic",
              }}
            >
              {data.state}
            </Typography>
          )}
        </>
      );
    }

    if (type === "action") {
      return (
        <Box sx={{ width: "100%" }}>
          <Typography
            variant="body1"
            align="center"
            sx={{
              fontWeight: 500,
              mb: 1,
              color: isCompleted ? "text.secondary" : "text.primary",
            }}
          >
            {label}
          </Typography>
          {time && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                mb: 1,
                justifyContent: "center",
              }}
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ fontWeight: 500 }}
              >
                {formatMinutesToTime(timeInMinutes)}
              </Typography>
            </Box>
          )}
          {tools && tools.length > 0 && (
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                gap: 0.5,
                justifyContent: "center",
              }}
            >
              {tools.map((tool, index) => (
                <RecipeChip
                  key={index}
                  label={tool}
                  type={CHIP_TYPES.TOOL}
                  size="small"
                />
              ))}
            </Box>
          )}
        </Box>
      );
    }

    return (
      <Typography
        variant="body2"
        align="center"
        sx={{
          fontWeight: 500,
          color: isCompleted ? "text.secondary" : "text.primary",
        }}
      >
        {label}
      </Typography>
    );
  };

  return (
    <div style={style}>
      <Handle
        type="target"
        position={Position.Left}
        style={{
          left: type === "action" ? -15 : -8,
          width: type === "action" ? "8px" : "6px",
          height: type === "action" ? "8px" : "6px",
          background: "#fff",
          border: "1px solid #666",
        }}
      />
      {renderContent()}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          right: type === "action" ? -15 : -8,
          width: type === "action" ? "8px" : "6px",
          height: type === "action" ? "8px" : "6px",
          background: "#fff",
          border: "1px solid #666",
        }}
      />
    </div>
  );
};

export default CustomNode;
