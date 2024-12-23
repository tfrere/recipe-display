import React from "react";
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

const ListDialog = ({
  open,
  onClose,
  title,
  content,
  buttonIcon,
  buttonText,
}) => (
  <>
    <Button
      variant="outlined"
      startIcon={buttonIcon}
      onClick={onClose}
      sx={{
        borderRadius: 2,
        textTransform: "none",
        px: 2,
      }}
    >
      {buttonText}
    </Button>
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          maxHeight: "80vh",
        },
      }}
      TransitionProps={{
        mountOnEnter: true,
        unmountOnExit: true,
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          pb: 1,
        }}
      >
        {title}
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>{content}</DialogContent>
    </Dialog>
  </>
);

export default ListDialog;
