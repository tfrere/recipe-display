import React from "react";
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
  if (!recipe) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: "background.default",
          borderRadius: 3,
          maxHeight: "85vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          p: 2,
          pb: 1.5,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography
            component="div"
            variant="h6"
            sx={{ fontWeight: 700, fontSize: "1.05rem" }}
          >
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
              fontSize: "0.62rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {t("gantt.timeline")}
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
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <Box
        sx={{
          flexGrow: 1,
          overflow: "auto",
          bgcolor: "background.default",
        }}
      >
        <GanttContent />
      </Box>
    </Dialog>
  );
};

export default GanttModal;
