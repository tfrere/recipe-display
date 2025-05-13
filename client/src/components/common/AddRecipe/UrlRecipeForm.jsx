import React, { useState } from "react";
import { Box, TextField, Button, Typography } from "@mui/material";
import AuthenticationSection from "./AuthenticationSection";

const getCredentialsForUrl = (url, authType, authValues) => {
  if (!authType || !authValues) return null;

  const credentials = {
    type: authType,
    values: {},
    domain: authValues.cookieDomain,
  };

  switch (authType) {
    case "cookie":
      credentials.values[authValues.cookieName] = authValues.cookieValue;
      break;
    case "basic":
      credentials.values = {
        username: authValues.username,
        password: authValues.password,
      };
      break;
    case "bearer":
      credentials.values = { token: authValues.token };
      break;
    case "apikey":
      credentials.values = { key: authValues.apiKey };
      break;
  }

  return credentials;
};

const UrlRecipeForm = ({ onSubmit, error }) => {
  const [recipeSource, setRecipeSource] = useState("");
  const [showAuth, setShowAuth] = useState(false);
  const [authType, setAuthType] = useState("cookie");
  const [authValues, setAuthValues] = useState({
    cookieName: "",
    cookieValue: "",
    cookieDomain: "",
    username: "",
    password: "",
    token: "",
    apiKey: "",
  });

  const handleSubmit = async () => {
    const credentials = getCredentialsForUrl(
      recipeSource,
      authType,
      authValues
    );
    await onSubmit({
      type: "url",
      url: recipeSource,
      credentials,
    });
  };

  return (
    <Box>
      <TextField
        fullWidth
        label="Recipe URL"
        value={recipeSource}
        onChange={(e) => setRecipeSource(e.target.value)}
        error={!!error}
        helperText={error}
      />

      <AuthenticationSection
        showAuth={showAuth}
        onToggleAuth={() => setShowAuth(!showAuth)}
        authType={authType}
        authValues={authValues}
        onAuthTypeChange={setAuthType}
        onAuthValuesChange={setAuthValues}
      />

      <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 1 }}>
        <Button
          onClick={handleSubmit}
          disabled={!recipeSource}
          variant="contained"
        >
          Add
        </Button>
      </Box>
    </Box>
  );
};

export default UrlRecipeForm;
