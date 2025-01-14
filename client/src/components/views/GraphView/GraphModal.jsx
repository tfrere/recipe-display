import React from "react";
import {
  Box,
  Dialog,
  DialogTitle,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { ReactFlowProvider } from "reactflow";
import GraphContent from "./GraphContent";

const GraphModal = ({ open, onClose, recipe }) => {
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
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography component="div" variant="h6">{recipe.metadata.title}</Typography>
        </Box>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: "text.secondary",
            "&:hover": {
              color: "text.primary",
            },
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
        <ReactFlowProvider>
          <GraphContent />
        </ReactFlowProvider>
      </Box>
    </Dialog>
  );
};

export default GraphModal;
