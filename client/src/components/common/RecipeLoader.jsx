import { useState, useEffect } from "react";
import { Box, Typography, CircularProgress, alpha } from "@mui/material";
import { keyframes } from "@emotion/react";

const tips = [
  "Filter recipes by season, diet, or dish type",
  "Adjust servings on any recipe and ingredients scale automatically",
  "Open the pantry to mark what you already have at home",
  "Cooking mode walks you through each step with timers",
  "The meal planner picks recipes that share ingredients",
  "Use the shopping list mode to check off ingredients as you shop",
  "Pantry items are auto-checked in shopping lists",
  "Search works on titles, ingredients, and authors",
  "Toggle \"Quick recipes\" to find meals under 30 minutes",
  "\"Few ingredients\" shows recipes with short shopping lists",
  "The meal planner balances macros across your week",
  "Print any recipe with a clean, ink-friendly layout",
];

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
  const [index, setIndex] = useState(() => Math.floor(Math.random() * tips.length));
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setFading(true);
      setTimeout(() => {
        setIndex((prev) => (prev + 1) % tips.length);
        setFading(false);
      }, FADE_DURATION);
    }, INTERVAL);
    return () => clearInterval(timer);
  }, []);

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
      <CircularProgress size={24} thickness={3} sx={{ color: alpha("#000", 0.15) }} />
      <Typography
        variant="body1"
        sx={{ color: "text.primary", fontWeight: 600, fontSize: "1rem", mt: 1.5 }}
      >
        Loading recipes
      </Typography>

      {/* Tip section — clearly secondary */}
      <Box
        sx={{
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          mt: 5,
          gap: 0.25,
        }}
      >
        <Typography
          variant="overline"
          sx={{ color: "text.disabled", letterSpacing: 1.5, fontSize: "0.55rem", lineHeight: 1 }}
        >
          tip
        </Typography>
        <Box sx={{ minHeight: 40, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Typography
            variant="caption"
            key={index}
            sx={{
              color: "text.disabled",
              maxWidth: 300,
              lineHeight: 1.4,
              fontSize: "0.75rem",
              animation: `${fading ? slideOut : slideIn} ${FADE_DURATION}ms ease forwards`,
            }}
          >
            {tips[index]}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
