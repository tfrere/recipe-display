import React, { useState } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  TextField, 
  DialogActions, 
  Button, 
  CircularProgress,
  Alert,
  Snackbar
} from '@mui/material';
import axios from 'axios';
import { useTranslation } from 'react-i18next';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const AddRecipeModal = ({ open, onClose, onRecipeAdded }) => {
  const [recipeSource, setRecipeSource] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const { t } = useTranslation();

  const handleAddRecipe = async () => {
    if (!recipeSource) return;

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      console.log('Sending recipe generation request to:', `${API_BASE_URL}/api/recipes/generate`);
      
      // Show initial loading message
      setSuccessMessage('Récupération de la recette en cours...');

      const response = await axios.post(`${API_BASE_URL}/api/recipes/generate`, { 
        source: recipeSource 
      }, {
        // Add a timeout to handle long-running requests
        timeout: 30000 
      });

      // Show success message
      setSuccessMessage('Recette générée avec succès !');

      // Optional: call a callback to refresh recipe list or do something with the new recipe
      if (onRecipeAdded) {
        onRecipeAdded(response.data);
      }

      // Close the modal after a short delay to show success message
      setTimeout(() => {
        onClose();
      }, 1500);

    } catch (err) {
      console.error('Error generating recipe:', err.response?.data || err.message);
      
      // Detailed error handling
      if (err.response) {
        // The request was made and the server responded with a status code
        setError(err.response.data || 'Erreur lors de la génération de la recette');
      } else if (err.request) {
        // The request was made but no response was received
        setError('Pas de réponse du serveur. Vérifiez votre connexion.');
      } else {
        // Something happened in setting up the request
        setError('Erreur de configuration de la requête');
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
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} color="secondary">
            {t('common.cancel')}
          </Button>
          <Button 
            onClick={handleAddRecipe} 
            color="primary" 
            disabled={!recipeSource || isLoading}
          >
            {isLoading ? <CircularProgress size={24} /> : t('addRecipe.submit')}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!successMessage || !!error}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={error ? 'error' : 'success'}
          sx={{ width: '100%' }}
        >
          {successMessage || error}
        </Alert>
      </Snackbar>
    </>
  );
};

export default AddRecipeModal;
