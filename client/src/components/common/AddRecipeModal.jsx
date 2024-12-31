import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  TextField, 
  DialogActions, 
  Button, 
  CircularProgress,
  Alert,
  Snackbar,
  Box,
  Typography,
  LinearProgress,
  Fade
} from '@mui/material';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const MODAL_TEXTS = {
  TITLE: 'Add a recipe',
  SOURCE: {
    LABEL: 'Recipe source',
    PLACEHOLDER: 'Enter a URL to a recipe',
    HELPER: 'Paste a URL to a recipe from your favorite cooking website'
  },
  STEPS: {
    FETCHING_URL: 'Fetching recipe from URL...',
    ANALYZING_CONTENT: 'Analyzing content...',
    EXTRACTING_RECIPE: 'Extracting recipe data...',
    TRANSLATING: 'Translating recipe...',
    PROCESSING_IMAGES: 'Processing images...',
    SAVING_RECIPE: 'Saving recipe...'
  },
  SUCCESS: 'Recipe successfully added!',
  ERROR: {
    GENERATION: 'Error generating recipe. Please try again.',
    NO_RESPONSE: 'No response from server. Please check your connection.',
    REQUEST: 'Error sending request. Please try again.'
  },
  BUTTONS: {
    CANCEL: 'Cancel',
    ADD: 'Add'
  }
};

const loadingSteps = [
  { key: 'fetch', message: MODAL_TEXTS.STEPS.FETCHING_URL, duration: 2000 },
  { key: 'analyze', message: MODAL_TEXTS.STEPS.ANALYZING_CONTENT, duration: 2000 },
  { key: 'extract', message: MODAL_TEXTS.STEPS.EXTRACTING_RECIPE, duration: 2000 },
  { key: 'translate', message: MODAL_TEXTS.STEPS.TRANSLATING, duration: 2000 },
  { key: 'images', message: MODAL_TEXTS.STEPS.PROCESSING_IMAGES, duration: 2000 },
  { key: 'save', message: MODAL_TEXTS.STEPS.SAVING_RECIPE, duration: 1000 },
];

const AddRecipeModal = ({ open, onClose, onRecipeAdded }) => {
  const [recipeSource, setRecipeSource] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setCurrentStep(0);
      setProgress(0);
      return;
    }

    let stepIndex = 0;
    let totalDuration = loadingSteps.reduce((acc, step) => acc + step.duration, 0);
    let startTime = Date.now();

    const updateProgress = () => {
      const elapsed = Date.now() - startTime;
      const currentStepDuration = loadingSteps[stepIndex].duration;
      let stepProgress = 0;
      let currentTime = 0;

      // Calculer l'étape actuelle et la progression
      for (let i = 0; i < loadingSteps.length; i++) {
        const stepDuration = loadingSteps[i].duration;
        if (currentTime + stepDuration > elapsed) {
          stepIndex = i;
          stepProgress = ((elapsed - currentTime) / stepDuration) * 100;
          break;
        }
        currentTime += stepDuration;
      }

      // Mettre à jour l'état
      setCurrentStep(stepIndex);
      setProgress((currentTime + stepProgress * loadingSteps[stepIndex].duration / 100) / totalDuration * 100);

      // Continuer l'animation si on n'a pas fini
      if (elapsed < totalDuration) {
        requestAnimationFrame(updateProgress);
      }
    };

    requestAnimationFrame(updateProgress);
  }, [isLoading]);

  const handleAddRecipe = async () => {
    if (!recipeSource) return;

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      console.log('Sending recipe generation request to:', `${API_BASE_URL}/api/recipes`);
      
      const response = await axios.post(`${API_BASE_URL}/api/recipes`, { 
        url: recipeSource 
      }, {
        timeout: 300000 
      });

      // Show success message
      setSuccessMessage(MODAL_TEXTS.SUCCESS);

      // Optional: call a callback to refresh recipe list
      if (onRecipeAdded) {
        onRecipeAdded(response.data);
      }

      // Close the modal after a short delay
      setTimeout(() => {
        onClose();
      }, 1500);

    } catch (err) {
      console.error('Error generating recipe:', err.response?.data || err.message);
      
      if (err.response) {
        setError(err.response.data || MODAL_TEXTS.ERROR.GENERATION);
      } else if (err.request) {
        setError(MODAL_TEXTS.ERROR.NO_RESPONSE);
      } else {
        setError(MODAL_TEXTS.ERROR.REQUEST);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSuccessMessage(null);
    setError(null);
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>{MODAL_TEXTS.TITLE}</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <TextField
            autoFocus
            margin="dense"
            label={MODAL_TEXTS.SOURCE.LABEL}
            fullWidth
            variant="outlined"
            value={recipeSource}
            onChange={(e) => setRecipeSource(e.target.value)}
            placeholder={MODAL_TEXTS.SOURCE.PLACEHOLDER}
            helperText={MODAL_TEXTS.SOURCE.HELPER}
            disabled={isLoading}
          />
          {isLoading && (
            <Box sx={{ mt: 3 }}>
              <LinearProgress variant="determinate" value={progress} sx={{ mb: 2 }} />
              <Box sx={{ minHeight: 60 }}>
                {loadingSteps.map((step, index) => (
                  <Fade
                    key={step.key}
                    in={currentStep === index}
                    timeout={500}
                    mountOnEnter
                    unmountOnExit
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <CircularProgress size={20} />
                      <Typography>
                        {step.message}
                      </Typography>
                    </Box>
                  </Fade>
                ))}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={isLoading}>
            {MODAL_TEXTS.BUTTONS.CANCEL}
          </Button>
          <Button 
            onClick={handleAddRecipe} 
            variant="contained" 
            disabled={!recipeSource || isLoading}
          >
            {MODAL_TEXTS.BUTTONS.ADD}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!successMessage}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        message={successMessage}
      />
    </>
  );
};

export default AddRecipeModal;
