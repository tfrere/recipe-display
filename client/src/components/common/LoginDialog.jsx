import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Button,
  Typography,
  IconButton,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";

const LoginDialog = ({ open, onClose, onLogin }) => {
  const { t } = useTranslation();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim()) return;

    setLoading(true);
    setError("");

    try {
      await onLogin(password);
      setPassword("");
      onClose();
    } catch (err) {
      setError(
        err?.response?.status === 401
          ? t("auth.invalidPassword", { defaultValue: "Invalid password" })
          : t("auth.error", { defaultValue: "Connection error" })
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPassword("");
    setError("");
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{ sx: { borderRadius: 3 } }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pb: 0.5,
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "1rem" }}>
          {t("auth.login", { defaultValue: "Login" })}
        </Typography>
        <IconButton
          onClick={handleClose}
          size="small"
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box component="form" onSubmit={handleSubmit} sx={{ pt: 1 }}>
          <TextField
            autoFocus
            fullWidth
            type="password"
            size="small"
            placeholder={t("auth.passwordPlaceholder", {
              defaultValue: "Password",
            })}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setError("");
            }}
            error={!!error}
            helperText={error}
            sx={{ mb: 2 }}
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={loading || !password.trim()}
            disableElevation
            sx={{ textTransform: "none", fontWeight: 600 }}
          >
            {loading
              ? t("auth.loggingIn", { defaultValue: "Logging in..." })
              : t("auth.login", { defaultValue: "Login" })}
          </Button>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default LoginDialog;
