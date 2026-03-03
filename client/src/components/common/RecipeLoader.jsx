import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, CircularProgress, Paper, alpha } from "@mui/material";
import { keyframes } from "@emotion/react";

const slideIn = keyframes`
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
`;

const slideOut = keyframes`
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-8px); }
`;

const INTERVAL = 3400;
const FADE_DURATION = 350;

export default function RecipeLoader() {
  const { t } = useTranslation();
  const tips = t("loader.tips", { returnObjects: true });
  const tipsArray = Array.isArray(tips) ? tips : [];
  const [index, setIndex] = useState(() =>
    tipsArray.length > 0 ? Math.floor(Math.random() * tipsArray.length) : 0
  );
  const [fading, setFading] = useState(false);

  useEffect(() => {
    if (tipsArray.length === 0) return;
    const timer = setInterval(() => {
      setFading(true);
      setTimeout(() => {
        setIndex((prev) => (prev + 1) % tipsArray.length);
        setFading(false);
      }, FADE_DURATION);
    }, INTERVAL);
    return () => clearInterval(timer);
  }, [tipsArray.length]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        flex: 1,
        px: 2,
      }}
    >
      {/* Spinner + label — grouped tight */}
      <CircularProgress size={24} thickness={3} sx={{ color: (theme) => alpha(theme.palette.text.primary, 0.15) }} />
      <Typography
        variant="body1"
        sx={{ color: "text.primary", fontWeight: 600, fontSize: "1rem", mt: 1.5 }}
      >
        {t("loader.loading")}
      </Typography>

      {/* Tip card */}
      <Paper
        elevation={0}
        sx={{
          mt: 5,
          px: 2.5,
          py: 1.5,
          borderRadius: 2,
          bgcolor: (theme) => alpha(theme.palette.text.primary, 0.03),
          border: (theme) => `1px solid ${alpha(theme.palette.divider, 0.06)}`,
          textAlign: "center",
          maxWidth: 340,
        }}
      >
        <Typography
          variant="overline"
          sx={{ color: "text.disabled", letterSpacing: 1.5, fontSize: "0.55rem", lineHeight: 1 }}
        >
          {t("loader.tip")}
        </Typography>
        <Box sx={{ minHeight: 40, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Typography
            variant="caption"
            key={index}
            sx={{
              color: "text.secondary",
              maxWidth: 300,
              lineHeight: 1.4,
              fontSize: "0.75rem",
              animation: `${fading ? slideOut : slideIn} ${FADE_DURATION}ms ease forwards`,
            }}
          >
            {tipsArray[index] ?? ""}
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}
