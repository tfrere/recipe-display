import React from "react";
import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Button,
  Typography,
} from "@mui/material";

const DeleteConfirmationDialog = ({ open, onClose, onConfirm, recipeName }) => {
  const { t } = useTranslation();
  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="delete-dialog-title"
      aria-describedby="delete-dialog-description"
      PaperProps={{
        sx: {
          borderRadius: 2,
          width: "100%",
          maxWidth: "450px",
        },
      }}
    >
      <DialogTitle
        id="delete-dialog-title"
        sx={{
          pb: 1,
        }}
      >
        <Typography variant="h6" component="span" sx={{ fontWeight: 600 }}>
          {t("common.deleteTitle")}
        </Typography>
      </DialogTitle>
      <DialogContent>
        <DialogContentText
          id="delete-dialog-description"
          sx={{
            color: "text.primary",
            mb: 1,
          }}
        >
          {t("common.deleteContent")}
        </DialogContentText>
        {recipeName && (
          <Typography
            variant="body2"
            sx={{
              mt: 2,
              fontStyle: "italic",
              color: "text.secondary",
            }}
          >
            Recipe: {recipeName}
          </Typography>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button
          onClick={onClose}
          variant="outlined"
          sx={{
            borderColor: "divider",
            color: "text.secondary",
            "&:hover": {
              borderColor: "text.primary",
              backgroundColor: "action.hover",
            },
          }}
        >
          {t("common.cancel")}
        </Button>
        <Button
          onClick={onConfirm}
          color="error"
          variant="contained"
          autoFocus
          sx={{
            px: 3,
            "&:hover": {
              backgroundColor: "error.dark",
            },
          }}
        >
          {t("common.delete")}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DeleteConfirmationDialog;
