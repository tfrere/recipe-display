import React from "react";
import { Handle, Position } from "reactflow";
import { Box, Typography, Chip, Checkbox } from "@mui/material";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import { useRecipe } from "../../../contexts/RecipeContext";

const getNodeStyle = (type, isCompleted, isUnused = false) => {
  const baseStyle = {
    padding: type === "action" ? "15px" : "10px",
    width: type === "action" ? "250px" : "160px",
    height: type === "action" ? "250px" : "160px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    transition: "all 0.2s ease",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    borderRadius: type === "action" ? "8px" : "50%",
    gap: "10px",
    opacity: isUnused ? 0.6 : 1,
  };

  if (type === "action" && isCompleted) {
    return {
      ...baseStyle,
      backgroundColor: "#f5f5f5",
      border: "2px solid #bdbdbd",
      opacity: 0.8,
    };
  }

  if (isUnused) {
    return {
      ...baseStyle,
      backgroundColor: "#f5f5f5",
      border: "2px solid #bdbdbd",
    };
  }

  switch (type) {
    case "ingredient":
      return {
        ...baseStyle,
        backgroundColor: "#e3f2fd",
        border: "2px solid #90caf9",
      };
    case "action":
      return {
        ...baseStyle,
        backgroundColor: "#fff3e0",
        border: "2px solid #ffb74d",
      };
    case "state":
      return {
        ...baseStyle,
        backgroundColor: "#f3e5f5",
        border: "2px solid #ce93d8",
      };
    default:
      return baseStyle;
  }
};

export const CustomNode = ({ data }) => {
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
  const style = getNodeStyle(type, isCompleted, isUnused);

  return (
    <div style={style}>
      <Handle
        type="target"
        position={Position.Left}
        style={{
          left: type === "action" ? -15 : -10,
          width: "8px",
          height: "8px",
          background: "#fff",
          border: "2px solid #666",
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{
          right: type === "action" ? -15 : -10,
          width: "8px",
          height: "8px",
          background: "#fff",
          border: "2px solid #666",
        }}
      />

      {type === "action" && (
        <Box
          sx={{
            position: "absolute",
            top: "10px",
            right: "10px",
          }}
        >
          <Checkbox
            checked={isCompleted}
            onChange={onClick}
            sx={{
              color: "#ffb74d",
              "&.Mui-checked": {
                color: "#f57c00",
              },
            }}
          />
        </Box>
      )}

      <Typography
        variant="body1"
        sx={{
          fontWeight: "bold",
          textAlign: "center",
          color:
            type === "action"
              ? isCompleted
                ? "#9e9e9e"
                : "#EF6C00"
              : isUnused
              ? "#9e9e9e"
              : "#424242",
          fontSize: type === "action" ? "16px" : "18px",
          px: 1,
          maxWidth: "100%",
          wordBreak: "break-word",
          textDecoration:
            type === "action" && isCompleted ? "line-through" : "none",
        }}
      >
        {label}
      </Typography>

      {type === "ingredient" && quantity && (
        <Typography
          variant="body2"
          sx={{
            color: isUnused ? "#9e9e9e" : "#1565C0",
            opacity: isUnused ? 0.7 : 0.7,
          }}
        >
          {quantity}
        </Typography>
      )}

      {type === "action" && (
        <>
          {time && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                color: isCompleted ? "#9e9e9e" : "#666",
              }}
            >
              <TimerOutlinedIcon
                sx={{
                  fontSize: 18,
                  color: isCompleted ? "#9e9e9e" : "#666",
                }}
              />
              <Typography variant="body2" color="inherit">
                {time}
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
                width: "100%",
                px: 1,
              }}
            >
              {tools.map((tool, index) => (
                <Chip
                  key={index}
                  label={tool}
                  size="small"
                  sx={{
                    backgroundColor: isCompleted
                      ? "rgba(189, 189, 189, 0.1)"
                      : "rgba(255, 183, 77, 0.1)",
                    borderColor: isCompleted ? "#bdbdbd" : "#ffb74d",
                    color: isCompleted ? "#9e9e9e" : "#666",
                    fontSize: "12px",
                    height: "20px",
                  }}
                  variant="outlined"
                />
              ))}
            </Box>
          )}
        </>
      )}
    </div>
  );
};
