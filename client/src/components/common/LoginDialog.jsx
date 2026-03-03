import { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  TextField,
  IconButton,
  Box,
  CircularProgress,
  InputAdornment,
  Fade,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { useTranslation } from "react-i18next";

const LoginDialog = ({ open, onClose, onLogin }) => {
  const { t } = useTranslation();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setPassword("");
      setError("");
      setShowPassword(false);
    }
  }, [open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim() || loading) return;

    setLoading(true);
    setError("");

    try {
      await onLogin(password);
      setPassword("");
      onClose();
    } catch (err) {
      setError(
        err?.response?.status === 401
          ? t("auth.invalidPassword", { defaultValue: "Wrong password" })
          : t("auth.error", { defaultValue: "Connection error" })
      );
      setTimeout(() => inputRef.current?.focus(), 50);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          overflow: "hidden",
        },
      }}
    >
      <DialogContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2.5,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <LockOutlinedIcon sx={{ color: "text.secondary", fontSize: "1.1rem" }} />
            <Typography
              variant="body1"
              sx={{ fontWeight: 600, fontSize: "0.95rem" }}
            >
              {t("auth.login", { defaultValue: "Login" })}
            </Typography>
          </Box>
          <IconButton
            onClick={onClose}
            size="small"
            disabled={loading}
            sx={{ color: "text.secondary", mr: -0.5 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            inputRef={inputRef}
            autoFocus
            fullWidth
            type={showPassword ? "text" : "password"}
            size="small"
            placeholder={t("auth.passwordPlaceholder", {
              defaultValue: "Password",
            })}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (error) setError("");
            }}
            error={!!error}
            helperText={error}
            disabled={loading}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end" sx={{ gap: 0.25 }}>
                    {password && (
                      <Fade in>
                        <IconButton
                          size="small"
                          onClick={() => setShowPassword((v) => !v)}
                          edge="end"
                          tabIndex={-1}
                          sx={{ color: "text.secondary" }}
                        >
                          {showPassword ? (
                            <VisibilityOffOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                          ) : (
                            <VisibilityOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                          )}
                        </IconButton>
                      </Fade>
                    )}
                    <IconButton
                      size="small"
                      type="submit"
                      disabled={loading || !password.trim()}
                      edge="end"
                      sx={{
                        color: password.trim() ? "primary.main" : "text.disabled",
                        transition: "color 0.15s",
                      }}
                    >
                      {loading ? (
                        <CircularProgress size={18} color="inherit" />
                      ) : (
                        <ArrowForwardIcon sx={{ fontSize: "1.2rem" }} />
                      )}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
            sx={{
              "& .MuiOutlinedInput-root": {
                borderRadius: 2,
                pr: 0.5,
              },
            }}
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default LoginDialog;
