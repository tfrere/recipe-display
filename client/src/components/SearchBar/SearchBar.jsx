import React from 'react';
import { Box, TextField, InputAdornment, IconButton } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import { useTranslation } from 'react-i18next';

const SearchBar = ({ value, onChange, onClear }) => {
  const { t } = useTranslation();

  const handleClear = () => {
    onChange('');
    onClear?.();
  };

  return (
    <Box sx={{ width: '100%', maxWidth: 800, mx: 'auto', mb: 3 }}>
      <TextField
        fullWidth
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t('search.placeholder')}
        variant="outlined"
        size="large"
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon color="action" fontSize="large" />
            </InputAdornment>
          ),
          endAdornment: value ? (
            <InputAdornment position="end">
              <IconButton
                aria-label="clear search"
                onClick={handleClear}
                edge="end"
                size="medium"
              >
                <ClearIcon fontSize="medium" />
              </IconButton>
            </InputAdornment>
          ) : null,
          sx: {
            borderRadius: 2,
            bgcolor: 'background.paper',
            '&:hover': {
              bgcolor: 'background.paper',
            },
            height: '64px', 
            fontSize: '1.2rem', 
          },
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: 'divider',
            },
            '&:hover fieldset': {
              borderColor: 'primary.main',
            },
            '&.Mui-focused fieldset': {
              borderColor: 'primary.main',
            },
          },
        }}
      />
    </Box>
  );
};

export default SearchBar;
