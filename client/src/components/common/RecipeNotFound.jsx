import React from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography } from "@mui/material";
import { styled } from "@mui/material/styles";

const StyledBox = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  padding: theme.spacing(3),
  textAlign: 'center',
  backgroundColor: theme.palette.background.default,
  color: theme.palette.text.primary,
}));

const RecipeNotFound = () => {
  const { t } = useTranslation();
  return (
    <StyledBox>
      <Typography variant="h4" component="h1" gutterBottom>
        {t("common.recipeNotFound")}
      </Typography>
      <Typography variant="body1" color="text.secondary">
        {t("common.recipeNotFoundDescription")}
      </Typography>
    </StyledBox>
  );
};

export default RecipeNotFound;
