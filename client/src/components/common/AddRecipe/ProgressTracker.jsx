import React from "react";
import { Box, Typography, CircularProgress, Alert } from "@mui/material";
import RecipeGenerationStep from "./RecipeGenerationStep";

const ProgressTracker = ({ progress, loadingMessage }) => {
  console.log("ProgressTracker:", { progress, loadingMessage });

  return (
    <Box sx={{ mt: 2 }}>
      {progress?.status === "error" && progress.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {progress.error}
        </Alert>
      )}

      {loadingMessage && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}
        >
          <CircularProgress size={16} />
          {loadingMessage}
        </Typography>
      )}

      {progress?.steps?.map((step, index) => {
        console.log("Rendering step:", step);
        return (
          <RecipeGenerationStep
            key={step.step}
            step={step}
            startTime={progress.createdAt}
          />
        );
      })}
    </Box>
  );
};

export default ProgressTracker;
