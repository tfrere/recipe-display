import React from "react";
import { Box, Typography, CircularProgress, Alert } from "@mui/material";
import RecipeGenerationStep from "./RecipeGenerationStep";

const ProgressTracker = ({ progress, loadingMessage }) => {
  console.log("ProgressTracker:", { progress, loadingMessage });

  // Identify the current step
  const currentStepId = progress?.currentStep;

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

      {progress?.steps?.map((step, index, stepsArray) => {
        console.log("Rendering step:", step);

        // Determine if this step should display details
        const shouldShowDetails =
          step.step === currentStepId && step.status === "in_progress";

        // Check if this is the last step
        const isLastStep = index === stepsArray.length - 1;

        // Remove details from steps that are not the current step
        const stepWithFilteredDetails = {
          ...step,
          details: shouldShowDetails ? step.details : null,
        };

        return (
          <RecipeGenerationStep
            key={step.step}
            step={stepWithFilteredDetails}
            startTime={progress.createdAt}
            isLastStep={isLastStep}
          />
        );
      })}
    </Box>
  );
};

export default ProgressTracker;
