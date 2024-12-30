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
import { useTranslation } from 'react-i18next';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const loadingSteps = [
  { key: 'fetch', message: 'addRecipe.steps.fetchingUrl', duration: 2000 },
  { key: 'analyze', message: 'addRecipe.steps.analyzingContent', duration: 2000 },
  { key: 'extract', message: 'addRecipe.steps.extractingRecipe', duration: 2000 },
  { key: 'translate', message: 'addRecipe.steps.translating', duration: 2000 },
  { key: 'images', message: 'addRecipe.steps.processingImages', duration: 2000 },
  { key: 'save', message: 'addRecipe.steps.savingRecipe', duration: 1000 },
];

const AddRecipeModal = ({ open, onClose, onRecipeAdded }) => {
  const [recipeSource, setRecipeSource] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const { t } = useTranslation();

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
      setSuccessMessage(t('addRecipe.success'));

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
        setError(err.response.data || t('addRecipe.error.generation'));
      } else if (err.request) {
        setError(t('addRecipe.error.noResponse'));
      } else {
        setError(t('addRecipe.error.request'));
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
        <DialogTitle>{t('addRecipe.title')}</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <TextField
            autoFocus
            margin="dense"
            label={t('addRecipe.sourceLabel')}
            fullWidth
            variant="outlined"
            value={recipeSource}
            onChange={(e) => setRecipeSource(e.target.value)}
            placeholder={t('addRecipe.sourcePlaceholder')}
            helperText={t('addRecipe.sourceHelper')}
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
                        {t(step.message)}
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
            {t('common.cancel')}
          </Button>
          <Button 
            onClick={handleAddRecipe} 
            variant="contained" 
            disabled={!recipeSource || isLoading}
          >
            {t('common.add')}
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
