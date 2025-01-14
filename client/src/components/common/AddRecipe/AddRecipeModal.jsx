import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  CircularProgress,
} from "@mui/material";
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
    // Reset all states
    setImportType("url");
    reset();
    onClose();
  };

  // Update useEffect to handle automatic closing
  useEffect(() => {
    if (!isLoading && !error) {
      handleClose();
    }
  }, [isLoading, error]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={isLoading}
      onBackdropClick={isLoading ? undefined : handleClose}
      PaperProps={{
        sx: { minHeight: "400px" },
      }}
    >
      <DialogTitle>Add Recipe</DialogTitle>
      <DialogContent>
        {!isLoading && (
          <Box
            sx={{
              mb: 3,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Choose import type
            </Typography>
            <ToggleButtonGroup
              value={importType}
              exclusive
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
            {importType === "url" ? (
              <UrlRecipeForm onSubmit={generateRecipe} error={error} />
            ) : (
              <TextRecipeForm onSubmit={generateRecipe} error={error} />
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isLoading}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddRecipeModal;
