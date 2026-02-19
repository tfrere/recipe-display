import React from "react";
import { Box, Dialog, IconButton, Typography, useTheme } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import CookingMode from "./CookingMode";

const CookingModal = ({ open, onClose, recipe }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  if (!recipe) return null;

  const title = recipe.metadata?.title || recipe.title;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      fullScreen
      PaperProps={{
        sx: {
          bgcolor: isDark ? "#1a1a1a" : "#fafafa",
          borderRadius: "12px",
          mx: "16px",
          my: "16px",
          height: "calc(100% - 32px)",
          maxHeight: "calc(100% - 32px)",
          overflow: "hidden",
        },
      }}
    >
      {/* Header: recipe name + close */}
      <Box
        sx={{
          px: 2.5,
          py: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          minHeight: 44,
          flexShrink: 0,
        }}
      >
        <Typography
          sx={{
            fontSize: "0.82rem",
            fontWeight: 600,
            color: "text.disabled",
            letterSpacing: "0.01em",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            mr: 2,
          }}
        >
          {title}
        </Typography>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: "text.secondary",
            bgcolor: isDark
              ? "rgba(255,255,255,0.05)"
              : "rgba(0,0,0,0.04)",
            "&:hover": {
              color: "text.primary",
              bgcolor: isDark
                ? "rgba(255,255,255,0.1)"
                : "rgba(0,0,0,0.08)",
            },
            width: 32,
            height: 32,
            flexShrink: 0,
          }}
        >
          <CloseIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </Box>

      {/* Content */}
      <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
        <CookingMode />
      </Box>
    </Dialog>
  );
};

export default CookingModal;
