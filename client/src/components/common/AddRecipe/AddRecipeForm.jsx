import React from 'react';
import { TextField, Box } from '@mui/material';

const AddRecipeForm = ({ recipeSource, onChange, disabled, error }) => {
  return (
    <Box sx={{ mb: 2 }}>
      <TextField
        fullWidth
        label="Recipe source"
        placeholder="Enter a URL to a recipe"
        helperText={error || "Paste a URL to a recipe from your favorite cooking website"}
        value={recipeSource}
        onChange={(e) => onChange(e.target.value)}
        error={!!error}
        disabled={disabled}
        sx={{ mb: 1 }}
      />
    </Box>
  );
};

export default AddRecipeForm;
