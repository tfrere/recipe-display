import React from "react";
import { Handle, Position } from "reactflow";
import { Box, Typography, Checkbox, useTheme } from "@mui/material";
import { useRecipe } from "../../../../contexts/RecipeContext";
import RecipeChip, { CHIP_TYPES } from "../../../common/RecipeChip";

const getNodeStyle = (type, isCompleted, theme, isUnused = false) => {
  const isDark = theme.palette.mode === 'dark';
  
  const baseStyle = {
    padding: type === "action" ? "15px" : "8px",
    width: type === "action" ? "250px" : "120px",
    height: type === "action" ? "250px" : "auto",
    minHeight: type === "action" ? "250px" : "60px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    transition: "all 0.2s ease",
    boxShadow: isDark ? "0 2px 4px rgba(0,0,0,0.3)" : "0 2px 4px rgba(0,0,0,0.1)",
    borderRadius: type === "action" ? "8px" : "4px",
    gap: type === "action" ? "10px" : "2px",
    opacity: isUnused ? 0.6 : 1,
  };

  if (type === "action" && isCompleted) {
    return {
      ...baseStyle,
      backgroundColor: isDark ? "#424242" : "#f5f5f5",
      border: `2px solid ${isDark ? "#757575" : "#bdbdbd"}`,
      opacity: 0.8,
    };
  }

  if (isUnused) {
    return {
      ...baseStyle,
      backgroundColor: isDark ? "#424242" : "#f5f5f5",
      border: `2px solid ${isDark ? "#757575" : "#bdbdbd"}`,
    };
  }

  switch (type) {
    case "ingredient":
      return {
        ...baseStyle,
        backgroundColor: isDark ? "#1a237e" : "#e3f2fd",
        border: `1px solid ${isDark ? "#5c6bc0" : "#90caf9"}`,
      };
    case "action":
      return {
        ...baseStyle,
        backgroundColor: isDark ? "#3e2723" : "#fff3e0",
        border: `2px solid ${isDark ? "#8d6e63" : "#ffb74d"}`,
      };
    case "state":
      return {
        ...baseStyle,
        backgroundColor: isDark ? "#4a148c" : "#f3e5f5",
        border: `2px solid ${isDark ? "#9c27b0" : "#ce93d8"}`,
      };
    default:
      return baseStyle;
  }
};

export const CustomNode = ({ data }) => {
  const theme = useTheme();
  const { formatMinutesToTime } = useRecipe();
  const {
    label,
    type,
    isCompleted,
    onClick,
    time,
    tools,
    quantity,
    id,
    isUnused,
  } = data;
  const style = getNodeStyle(type, isCompleted, theme, isUnused);

  // Convertir le temps en minutes si nécessaire
  const timeInMinutes = time ? parseInt(time.match(/\d+/)[0]) : 0;

  const renderContent = () => {
    if (type === "ingredient") {
      return (
        <>
          <Typography
            variant="body2"
            align="center"
            sx={{
              fontWeight: 500,
              fontSize: "0.875rem",
              lineHeight: 1.2,
              mb: 0.5,
            }}
          >
            {label}
          </Typography>
          <Typography
            variant="caption"
            align="center"
            sx={{
              color: "text.secondary",
              fontSize: "0.75rem",
              lineHeight: 1,
            }}
          >
            {quantity}
          </Typography>
        </>
      );
    }

    if (type === "action") {
      return (
        <>
          {onClick && (
            <Checkbox
              checked={isCompleted}
              onChange={onClick}
              sx={{ position: "absolute", top: 5, right: 5 }}
            />
          )}
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
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
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
        </>
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
      {renderContent()}
    </div>
  );
};

export default CustomNode;
