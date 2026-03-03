import React, { useMemo, useState, useEffect, useCallback } from "react";
import {
  Box,
  Dialog,
  Fade,
  IconButton,
  useTheme,
  ThemeProvider,
  createTheme,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import CookingMode from "./CookingMode";

const EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)";

const CookingModal = ({ open, onClose, recipe }) => {
  const baseTheme = useTheme();
  const [alive, setAlive] = useState(false);
  const isLight = baseTheme.palette.mode === "light";

  useEffect(() => {
    if (open) {
      const id = requestAnimationFrame(() => {
        requestAnimationFrame(() => setAlive(true));
      });
      return () => cancelAnimationFrame(id);
    }
  }, [open]);

  const handleExited = useCallback(() => setAlive(false), []);

  const overlayColor = isLight
    ? "rgba(255, 255, 255, 0.88)"
    : "rgba(0, 0, 0, 0.62)";

  const contentTheme = useMemo(
    () =>
      createTheme({
        ...baseTheme,
        palette: {
          ...baseTheme.palette,
          mode: isLight ? "light" : "dark",
          text: isLight
            ? {
                primary: "rgba(0, 0, 0, 0.88)",
                secondary: "rgba(0, 0, 0, 0.50)",
                disabled: "rgba(0, 0, 0, 0.28)",
              }
            : {
                primary: "rgba(255, 255, 255, 0.92)",
                secondary: "rgba(255, 255, 255, 0.55)",
                disabled: "rgba(255, 255, 255, 0.30)",
              },
          background: {
            default: "transparent",
            paper: isLight ? "#f5f5f7" : "#1a1a1e",
          },
          divider: isLight
            ? "rgba(0, 0, 0, 0.10)"
            : "rgba(255, 255, 255, 0.08)",
        },
      }),
    [baseTheme, isLight]
  );

  if (!recipe) return null;

  const title = recipe.metadata?.title || recipe.title;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      fullScreen
      TransitionComponent={Fade}
      transitionDuration={{ enter: 1, exit: 220 }}
      TransitionProps={{ onExited: handleExited }}
      slotProps={{
        backdrop: { sx: { display: "none" } },
      }}
      PaperProps={{
        sx: {
          bgcolor: "transparent",
          boxShadow: "none",
          borderRadius: 0,
          m: 0,
          width: "100%",
          height: "100%",
          maxHeight: "100%",
          overflow: "hidden",
        },
      }}
    >
      <ThemeProvider theme={contentTheme}>
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            bgcolor: alive ? overlayColor : "transparent",
            backdropFilter: alive
              ? "blur(72px) saturate(1.4)"
              : "blur(0px) saturate(1)",
            WebkitBackdropFilter: alive
              ? "blur(72px) saturate(1.4)"
              : "blur(0px) saturate(1)",
            transition: alive
              ? `background-color 550ms ${EASE_OUT}, backdrop-filter 550ms ${EASE_OUT}, -webkit-backdrop-filter 550ms ${EASE_OUT}`
              : "none",
          }}
        />

        <Box
          sx={{
            position: "relative",
            zIndex: 1,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            opacity: alive ? 1 : 0,
            transform: alive ? "translateY(0)" : "translateY(6px)",
            transition: alive
              ? `opacity 420ms 60ms ${EASE_OUT}, transform 500ms 60ms ${EASE_OUT}`
              : "none",
            willChange: "transform, opacity",
          }}
        >
          <Box sx={{ position: "absolute", top: 12, right: 16, zIndex: 2 }}>
            <IconButton
              onClick={onClose}
              size="small"
              sx={{
                color: "text.disabled",
                "&:hover": {
                  color: "text.secondary",
                  bgcolor: "action.hover",
                },
                width: 36,
                height: 36,
                transition: "all 0.2s ease",
              }}
            >
              <CloseIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Box>

          <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
            <CookingMode title={title} />
          </Box>
        </Box>
      </ThemeProvider>
    </Dialog>
  );
};

export default CookingModal;
