import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  IconButton,
  Box,
  Typography,
  CircularProgress,
  Paper,
  Alert,
} from "@mui/material";
import {
  Close as CloseIcon,
  ArrowBack as ArrowBackIcon,
  Link as LinkIcon,
  TextSnippet as TextSnippetIcon,
  PhotoCamera as PhotoCameraIcon,
  Edit as EditIcon,
} from "@mui/icons-material";
import UrlRecipeForm from "./UrlRecipeForm";
import TextRecipeForm from "./TextRecipeForm";
import ImageRecipeForm from "./ImageRecipeForm";
import ManualRecipeForm from "./ManualRecipeForm";
import ProgressTracker from "./ProgressTracker";
import { useRecipeGeneration } from "../../../hooks/useRecipeGeneration";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

// ─── Mode Definitions ────────────────────────────────────────

const MODE_OPTIONS = [
  {
    id: "url",
    title: "From URL",
    description: "Paste a recipe website URL to import it automatically",
    Icon: LinkIcon,
    color: "#2196f3",
  },
  {
    id: "text",
    title: "From Text",
    description: "Paste raw text and let AI structure your recipe",
    Icon: TextSnippetIcon,
    color: "#4caf50",
  },
  {
    id: "image",
    title: "From Image",
    description: "Upload a recipe photo to extract its content",
    Icon: PhotoCameraIcon,
    color: "#9c27b0",
  },
  {
    id: "manual",
    title: "Manual Entry",
    description: "Create your recipe step by step with a guided form",
    Icon: EditIcon,
    color: "#ff9800",
  },
];

// ─── Mode Card Component ─────────────────────────────────────

const ModeCard = ({ option, onClick }) => {
  const { Icon, color, title, description } = option;

  return (
    <Paper
      elevation={0}
      onClick={() => onClick(option.id)}
      sx={{
        p: 2.5,
        cursor: "pointer",
        border: 2,
        borderColor: "transparent",
        borderRadius: 3,
        bgcolor: `${color}06`,
        transition: "all 0.2s ease",
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        height: "100%",
        "&:hover": {
          borderColor: color,
          bgcolor: `${color}10`,
          transform: "translateY(-2px)",
          boxShadow: `0 4px 16px ${color}22`,
        },
        "&:active": {
          transform: "translateY(0)",
        },
      }}
    >
      <Box
        sx={{
          width: 44,
          height: 44,
          borderRadius: 2.5,
          bgcolor: `${color}14`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Icon sx={{ fontSize: 24, color }} />
      </Box>
      <Box>
        <Typography
          variant="subtitle1"
          sx={{ fontWeight: 650, lineHeight: 1.3, mb: 0.3 }}
        >
          {title}
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ lineHeight: 1.45, fontSize: "0.82rem" }}
        >
          {description}
        </Typography>
      </Box>
    </Paper>
  );
};

// ─── Mode Selector Screen ────────────────────────────────────

const ModeSelector = ({ onSelect }) => (
  <Box>
    <Box sx={{ textAlign: "center", mb: 3, mt: 1 }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
        Add a Recipe
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Choose how you'd like to add your recipe
      </Typography>
    </Box>

    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
        gap: 2,
        pb: 1,
      }}
    >
      {MODE_OPTIONS.map((option) => (
        <ModeCard key={option.id} option={option} onClick={onSelect} />
      ))}
    </Box>
  </Box>
);

// ─── Form Header ─────────────────────────────────────────────

const FormHeader = ({ mode, onBack, isBusy }) => {
  const modeInfo = MODE_OPTIONS.find((m) => m.id === mode);
  if (!modeInfo) return null;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        mb: 2.5,
        pb: 2,
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      {!isBusy && (
        <IconButton
          onClick={onBack}
          size="small"
          sx={{
            color: "text.secondary",
            "&:hover": { bgcolor: `${modeInfo.color}10` },
          }}
        >
          <ArrowBackIcon fontSize="small" />
        </IconButton>
      )}
      <Box
        sx={{
          width: 32,
          height: 32,
          borderRadius: 1.5,
          bgcolor: `${modeInfo.color}12`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <modeInfo.Icon sx={{ fontSize: 18, color: modeInfo.color }} />
      </Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
        {modeInfo.title}
      </Typography>
    </Box>
  );
};

// ─── Loading Screen ──────────────────────────────────────────

const LoadingScreen = ({ progress, loadingMessage, label }) => {
  if (progress) {
    return <ProgressTracker progress={progress} message={loadingMessage} />;
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        minHeight: 220,
        gap: 2,
      }}
    >
      <CircularProgress size={40} thickness={4} />
      <Typography variant="body2" color="text.secondary">
        {label || "Loading..."}
      </Typography>
    </Box>
  );
};

// ─── Main Modal Component ────────────────────────────────────

const AddRecipeModal = ({ open, onClose, onRecipeAdded }) => {
  const navigate = useNavigate();

  // Navigation state — null = mode selector, otherwise form mode
  const [selectedMode, setSelectedMode] = useState(null);

  // Manual recipe submission state
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [manualError, setManualError] = useState(null);

  // Recipe generation state (for URL/text/image)
  const {
    isLoading,
    error,
    success,
    progress,
    loadingMessage,
    generateRecipe,
    reset,
  } = useRecipeGeneration(onRecipeAdded);

  // ─── Handlers ────────────────────────────────────────

  const handleSelectMode = (modeId) => {
    setSelectedMode(modeId);
    setManualError(null);
  };

  const handleBack = () => {
    if (!isLoading && !manualSubmitting) {
      setSelectedMode(null);
      setManualError(null);
      reset();
    }
  };

  const handleClose = () => {
    if (!isLoading && !manualSubmitting) {
      setSelectedMode(null);
      setManualError(null);
      setManualSubmitting(false);
      reset();
      onClose();
    }
  };

  const handleManualSubmit = async (recipeData) => {
    setManualSubmitting(true);
    setManualError(null);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/recipes/manual`,
        recipeData
      );
      const slug = response.data?.slug;

      if (onRecipeAdded) {
        onRecipeAdded();
      }

      setManualSubmitting(false);
      setSelectedMode(null);
      onClose();

      if (slug) {
        navigate(`/recipe/${slug}`);
      } else {
        navigate("/");
      }
    } catch (err) {
      setManualSubmitting(false);
      const detail =
        err.response?.data?.detail ||
        err.message ||
        "Error creating recipe";
      setManualError(detail);
    }
  };

  // ─── Auto-close effects ──────────────────────────────

  useEffect(() => {
    if (!isLoading && error) {
      const timer = setTimeout(() => handleClose(), 3000);
      return () => clearTimeout(timer);
    }
  }, [isLoading, error]);

  useEffect(() => {
    if (success) {
      handleClose();
    }
  }, [success]);

  // ─── Derived state ───────────────────────────────────

  const isBusy = isLoading || manualSubmitting;
  const isManual = selectedMode === "manual";
  const showForm = selectedMode !== null;

  // ─── Render ──────────────────────────────────────────

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth={isManual ? "md" : "sm"}
      fullWidth
      disableEscapeKeyDown={isBusy}
      PaperProps={{
        sx: {
          borderRadius: 3,
          overflow: "hidden",
          transition: "max-width 0.35s cubic-bezier(.4,0,.2,1)",
          ...(isManual && { minHeight: "70vh" }),
        },
      }}
    >
      {/* Close button — always top right, only when not busy */}
      {!isBusy && (
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={{
            position: "absolute",
            right: 12,
            top: 12,
            zIndex: 1,
            color: "text.disabled",
            bgcolor: "background.paper",
            "&:hover": {
              color: "text.primary",
              bgcolor: "grey.100",
            },
          }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      )}

      <DialogContent
        sx={{
          p: { xs: 2.5, sm: 3.5 },
          pt: { xs: 3, sm: 3.5 },
        }}
      >
        {/* ─── Screen 1: Mode Selection ─── */}
        {!showForm && <ModeSelector onSelect={handleSelectMode} />}

        {/* ─── Screen 2: Active Form ─── */}
        {showForm && (
          <>
            <FormHeader
              mode={selectedMode}
              onBack={handleBack}
              isBusy={isBusy}
            />

            {isLoading ? (
              <LoadingScreen
                progress={progress}
                loadingMessage={loadingMessage}
                label="Generating recipe..."
              />
            ) : manualSubmitting ? (
              <LoadingScreen label="Creating recipe..." />
            ) : (
              <>
                {error && !isManual && (
                  <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
                    {error}
                  </Alert>
                )}

                {selectedMode === "url" && (
                  <UrlRecipeForm onSubmit={generateRecipe} error={error} />
                )}
                {selectedMode === "text" && (
                  <TextRecipeForm onSubmit={generateRecipe} error={error} />
                )}
                {selectedMode === "image" && (
                  <ImageRecipeForm onSubmit={generateRecipe} error={error} />
                )}
                {selectedMode === "manual" && (
                  <ManualRecipeForm
                    onSubmit={handleManualSubmit}
                    error={manualError}
                    isSubmitting={manualSubmitting}
                  />
                )}
              </>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default AddRecipeModal;
