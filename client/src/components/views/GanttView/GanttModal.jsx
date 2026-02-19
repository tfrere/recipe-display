import React from "react";
import {
  Box,
  Dialog,
  DialogTitle,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import GanttContent from "./GanttContent";

const GanttModal = ({ open, onClose, recipe }) => {
  if (!recipe) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      fullScreen
      PaperProps={{
        sx: {
          bgcolor: "background.default",
          mx: "20px",
          my: "20px",
          height: "calc(100% - 40px)",
          maxHeight: "calc(100% - 40px)",
        },
      }}
    >
      <DialogTitle
        sx={{
          p: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography component="div" variant="h6">
            {recipe.metadata?.title || recipe.title}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              bgcolor: "action.selected",
              px: 1,
              py: 0.25,
              borderRadius: 1,
              fontWeight: 600,
            }}
          >
            Timeline
          </Typography>
        </Box>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: "text.secondary",
            "&:hover": { color: "text.primary" },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <Box
        sx={{
          flexGrow: 1,
          height: "calc(100vh - 64px)",
          bgcolor: "background.default",
        }}
      >
        <GanttContent />
      </Box>
    </Dialog>
  );
};

export default GanttModal;
