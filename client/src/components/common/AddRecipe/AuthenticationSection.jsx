import React, { useState, useEffect } from "react";
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Typography,
  Collapse,
  IconButton,
  Chip,
  Divider,
} from "@mui/material";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DeleteIcon from "@mui/icons-material/Delete";
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";

const AuthenticationSection = ({
  showAuth,
  onToggleAuth,
  authType,
  authValues,
  onAuthTypeChange,
  onAuthValuesChange,
  disabled,
}) => {
  const [presets, setPresets] = useState([]);

  // Load presets on mount
  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/auth/presets`);
        // Convert map to array
        const presetsArray = Object.entries(response.data).map(
          ([domain, preset]) => ({
            ...preset,
            domain: domain,
          })
        );
        setPresets(presetsArray);
      } catch (error) {
        console.error("Error fetching auth presets:", error);
      }
    };
    fetchPresets();
  }, []);

  const handleDeletePreset = async (id, event) => {
    event.stopPropagation();
    try {
      await axios.delete(`${API_BASE_URL}/api/auth/presets/${id}`);
      setPresets(presets.filter((p) => p.id !== id));
    } catch (error) {
      console.error("Error deleting auth preset:", error);
    }
  };

  const handleApplyPreset = (preset) => {
    onAuthTypeChange(preset.type);
    onAuthValuesChange({
      ...authValues,
      // Reset all values
      cookieName: "",
      cookieValue: "",
      cookieDomain: "",
      username: "",
      password: "",
      token: "",
      apiKey: "",
      // Apply new values based on type
      ...(preset.type === "cookie" && {
        cookieName: Object.keys(preset.values)[0] || "",
        cookieValue: Object.values(preset.values)[0] || "",
        cookieDomain: preset.domain || "",
      }),
      ...(preset.type === "basic" && {
        username: preset.values.username || "",
        password: preset.values.password || "",
      }),
      ...(preset.type === "bearer" && {
        token: preset.values.token || "",
      }),
      ...(preset.type === "apikey" && {
        apiKey: preset.values.key || "",
      }),
    });
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          cursor: "pointer",
          mb: 1,
        }}
        onClick={() => !disabled && onToggleAuth()}
      >
        <IconButton size="small" sx={{ mr: 1 }} disabled={disabled}>
          {showAuth ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
        <Typography
          variant="body2"
          color={disabled ? "text.disabled" : "text.primary"}
        >
          Authentication options
        </Typography>
      </Box>

      <Collapse in={showAuth}>
        <Box sx={{ mt: 2 }}>
          {/* Presets section */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Saved authentications
            </Typography>
            {presets.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No saved authentications yet
              </Typography>
            ) : (
              <Box>
                {presets.map((preset) => (
                  <Chip
                    key={preset.id}
                    label={preset.domain}
                    onClick={() => handleApplyPreset(preset)}
                    onDelete={(e) => handleDeletePreset(preset.id, e)}
                    deleteIcon={<DeleteIcon />}
                    sx={{ mr: 1, mb: 1 }}
                  />
                ))}
              </Box>
            )}
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Authentication form */}
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Authentication type</InputLabel>
            <Select
              value={authType}
              onChange={(e) => onAuthTypeChange(e.target.value)}
              disabled={disabled}
            >
              <MenuItem value="cookie">Cookie</MenuItem>
              <MenuItem value="basic">Basic Auth</MenuItem>
              <MenuItem value="bearer">Bearer Token</MenuItem>
              <MenuItem value="apikey">API Key</MenuItem>
            </Select>
          </FormControl>

          {authType === "cookie" && (
            <>
              <TextField
                fullWidth
                label="Cookie name"
                value={authValues.cookieName}
                onChange={(e) =>
                  onAuthValuesChange({
                    ...authValues,
                    cookieName: e.target.value,
                  })
                }
                disabled={disabled}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Cookie value"
                value={authValues.cookieValue}
                onChange={(e) =>
                  onAuthValuesChange({
                    ...authValues,
                    cookieValue: e.target.value,
                  })
                }
                disabled={disabled}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Cookie domain"
                value={authValues.cookieDomain}
                onChange={(e) =>
                  onAuthValuesChange({
                    ...authValues,
                    cookieDomain: e.target.value,
                  })
                }
                disabled={disabled}
              />
            </>
          )}

          {authType === "basic" && (
            <>
              <TextField
                fullWidth
                label="Username"
                value={authValues.username}
                onChange={(e) =>
                  onAuthValuesChange({
                    ...authValues,
                    username: e.target.value,
                  })
                }
                disabled={disabled}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                type="password"
                label="Password"
                value={authValues.password}
                onChange={(e) =>
                  onAuthValuesChange({
                    ...authValues,
                    password: e.target.value,
                  })
                }
                disabled={disabled}
              />
            </>
          )}

          {authType === "bearer" && (
            <TextField
              fullWidth
              label="Token"
              value={authValues.token}
              onChange={(e) =>
                onAuthValuesChange({ ...authValues, token: e.target.value })
              }
              disabled={disabled}
            />
          )}

          {authType === "apikey" && (
            <TextField
              fullWidth
              label="API Key"
              value={authValues.apiKey}
              onChange={(e) =>
                onAuthValuesChange({ ...authValues, apiKey: e.target.value })
              }
              disabled={disabled}
            />
          )}
        </Box>
      </Collapse>
    </Box>
  );
};

export default AuthenticationSection;
