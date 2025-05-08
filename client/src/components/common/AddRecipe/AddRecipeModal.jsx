import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  CircularProgress,
  Alert,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import UrlRecipeForm from "./UrlRecipeForm";
import TextRecipeForm from "./TextRecipeForm";
import ProgressTracker from "./ProgressTracker";
import { useRecipeGeneration } from "../../../hooks/useRecipeGeneration";

const AddRecipeModal = ({ open, onClose, onRecipeAdded }) => {
  // Import type state
  const [importType, setImportType] = useState("url");

  // Recipe generation state and logic
  const { isLoading, error, progress, loadingMessage, generateRecipe, reset } =
    useRecipeGeneration(onRecipeAdded);

  const handleImportTypeChange = (event, newType) => {
    if (newType !== null) {
      setImportType(newType);
    }
  };

  const handleClose = () => {
    // Only allow closing if not loading
    if (!isLoading) {
      // Reset all states
      setImportType("url");
      reset();
      onClose();
    }
  };

  // Update useEffect to handle automatic closing only on error
  useEffect(() => {
    if (!isLoading && error) {
      // If we have an error and loading is finished,
      // close the modal after a delay so the user can read the message
      const timer = setTimeout(() => {
        handleClose();
      }, 3000); // 3 seconds

      return () => clearTimeout(timer);
    }
  }, [isLoading, error]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={true}
      onBackdropClick={() => {}}
    >
      <DialogTitle sx={{ m: 0, p: 2 }}>
        Add Recipe
        {!isLoading && (
          <IconButton
            aria-label="close"
            onClick={handleClose}
            sx={{
              position: "absolute",
              right: 8,
              top: 8,
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <CloseIcon />
          </IconButton>
        )}
      </DialogTitle>
      <DialogContent>
        {!isLoading && (
          <Box
            sx={{
              mb: 3,
              display: "flex",
              flexDirection: "column",
              alignItems: "start",
            }}
          >
            <ToggleButtonGroup
              value={importType}
              exclusive
              fullWidth
              onChange={handleImportTypeChange}
              aria-label="recipe import type"
            >
              <ToggleButton value="url" aria-label="from URL">
                From URL
              </ToggleButton>
              <ToggleButton value="text" aria-label="from text">
                From Text
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        )}

        {isLoading ? (
          progress ? (
            <ProgressTracker progress={progress} message={loadingMessage} />
          ) : (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                minHeight: "200px",
                gap: 2,
              }}
            >
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">
                Adding recipe...
              </Typography>
            </Box>
          )
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            {importType === "url" ? (
              <UrlRecipeForm onSubmit={generateRecipe} error={error} />
            ) : (
              <TextRecipeForm onSubmit={generateRecipe} error={error} />
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default AddRecipeModal;
