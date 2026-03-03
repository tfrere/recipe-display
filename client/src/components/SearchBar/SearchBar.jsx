import React from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Typography,
  Tooltip,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useRecipeList } from "../../contexts/RecipeListContext";

const SearchBar = ({
  value,
  onChange,
  filteredCount,
  totalCount,
  hasActiveFilters,
}) => {
  const { t } = useTranslation();
  const { resetFilters } = useRecipeList();
  const showCount =
    typeof filteredCount === "number" && typeof totalCount === "number";
  const isPristine = !value && !hasActiveFilters;
  const showRefresh = !isPristine;

  const handleInputChange = (e) => {
    onChange(e.target.value);
  };

  const handleReset = () => {
    onChange("");
    resetFilters();
  };

  return (
    <Box sx={{ width: "100%" }}>
      <TextField
        fullWidth
        value={value}
        onChange={handleInputChange}
        placeholder={t("search.placeholder")}
        variant="outlined"
        size="large"
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon color="action" fontSize="large" />
            </InputAdornment>
          ),
          endAdornment: (
            <>
              {showCount && (
                <InputAdornment position="end">
                  <Typography
                    variant="body2"
                    color={isPristine ? "text.secondary" : "primary"}
                    sx={{
                      fontWeight: isPristine ? 400 : 700,
                      minWidth: 80,
                      textAlign: "right",
                      mr: showRefresh ? 1 : 0,
                    }}
                  >
                    {isPristine
                      ? totalCount
                      : `${filteredCount} / ${totalCount}`}
                  </Typography>
                </InputAdornment>
              )}
              {showRefresh && (
                <InputAdornment position="end">
                  <Tooltip title={t("search.resetFilters")} placement="top">
                    <IconButton
                      aria-label="reset filters"
                      onClick={handleReset}
                      edge="end"
                      size="medium"
                    >
                      <RefreshIcon fontSize="medium" />
                    </IconButton>
                  </Tooltip>
                </InputAdornment>
              )}
            </>
          ),
          sx: {
            borderRadius: 6,
            bgcolor: "background.paper",
            "&:hover": {
              bgcolor: "background.paper",
            },
            height: "64px",
            fontSize: "1.2rem",
            paddingRight: "24px",
          },
        }}
        sx={{
          "& .MuiOutlinedInput-root": {
            "& fieldset": {
              borderColor: "divider",
            },
            "&:hover fieldset": {
              borderColor: "divider",
            },
            "&.Mui-focused fieldset": {
              borderColor: "primary.main",
            },
          },
        }}
      />
    </Box>
  );
};

export default SearchBar;
