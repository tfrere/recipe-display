import React from 'react';
import { Button } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useRecipeList } from '../../contexts/RecipeListContext';

const AddRecipeButton = (props) => {
  const { openAddRecipeModal } = useRecipeList();

  return (
    <Button
      startIcon={<AddIcon />}
      onClick={openAddRecipeModal}
      {...props}
    >
      Add Recipe
    </Button>
  );
};

export default AddRecipeButton;
