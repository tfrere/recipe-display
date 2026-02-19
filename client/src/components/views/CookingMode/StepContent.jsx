import React from "react";
import { Box, Typography, Fade } from "@mui/material";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import VisibilityIcon from "@mui/icons-material/Visibility";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import SubdirectoryArrowRightIcon from "@mui/icons-material/SubdirectoryArrowRight";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CircularTimer from "./CircularTimer";
import { formatTemperature, getActionFontSize } from "./utils";

/* ── Context badge ── */
const ContextBadge = ({ icon, text, color, isDark }) => (
  <Box
    sx={{
      display: "inline-flex",
      alignItems: "center",
      gap: 0.75,
      px: 1.5,
      py: 0.625,
      borderRadius: "20px",
      bgcolor: isDark ? `${color}15` : `${color}0A`,
    }}
  >
    {icon}
    <Typography
      sx={{
        color,
        fontWeight: 500,
        fontSize: "0.85rem",
        lineHeight: 1.3,
      }}
    >
      {text}
    </Typography>
  </Box>
);

/* ── Ingredient pill — big enough to read from 1m ── */
const IngredientPill = ({ ingredient, isDark }) => {
  if (ingredient.isProducedState) {
    const displayName = ingredient.name
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

    return (
      <Box
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.75,
          px: 2,
          py: 1,
          borderRadius: "12px",
          bgcolor: isDark
            ? "rgba(33,150,243,0.08)"
            : "rgba(33,150,243,0.05)",
        }}
      >
        <SubdirectoryArrowRightIcon
          sx={{ fontSize: 16, color: "#42a5f5", opacity: 0.8 }}
        />
        <Typography
          sx={{
            fontSize: "1rem",
            fontWeight: 500,
            color: isDark ? "rgba(100,180,255,0.85)" : "#1565c0",
            lineHeight: 1.3,
            fontStyle: "italic",
          }}
        >
          {displayName}
        </Typography>
      </Box>
    );
  }

  const qty = `${ingredient.amount || ""} ${ingredient.unit || ""}`.trim();
  const name = (ingredient.name || ingredient.ref || "").trim();

  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "baseline",
        gap: 0.75,
        px: 2,
        py: 1,
        borderRadius: "12px",
        bgcolor: isDark
          ? "rgba(255,255,255,0.06)"
          : "rgba(0,0,0,0.04)",
      }}
    >
      {qty && (
        <Typography
          sx={{
            fontSize: "1rem",
            fontWeight: 700,
            color: "text.primary",
            lineHeight: 1.3,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {qty}
        </Typography>
      )}
      <Typography
        sx={{
          fontSize: "1rem",
          fontWeight: 400,
          color: "text.secondary",
          lineHeight: 1.3,
        }}
      >
        {name}
      </Typography>
    </Box>
  );
};

/* ── Completion screen ── */
const CompletionScreen = ({ isDark }) => (
  <Fade in timeout={500}>
    <Box
      sx={{
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 2,
      }}
    >
      <Box
        sx={{
          width: 80,
          height: 80,
          borderRadius: "50%",
          bgcolor: isDark
            ? "rgba(76,175,80,0.1)"
            : "rgba(76,175,80,0.07)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <CheckCircleOutlineIcon sx={{ fontSize: 40, color: "#4caf50" }} />
      </Box>
      <Typography
        sx={{
          fontWeight: 700,
          fontSize: "1.6rem",
          letterSpacing: "-0.02em",
          lineHeight: 1.2,
        }}
      >
        Bon appétit !
      </Typography>
      <Typography
        sx={{ color: "text.secondary", fontSize: "0.95rem", maxWidth: 320 }}
      >
        Toutes les étapes sont terminées.
      </Typography>
    </Box>
  </Fade>
);

/* ═══════════════════════════════════════════════════════════════════
   StepContent — the hero of the cooking mode.

   Design principle: the instruction IS the screen.
   Everything else supports it. Think flashcard, not dashboard.
   ═══════════════════════════════════════════════════════════════════ */

const StepContent = ({
  step,
  timer,
  hasDuration,
  isDark,
  slideKey,
  isCompleted,
  showSubRecipeTitle,
}) => {
  if (isCompleted) return <CompletionScreen isDark={isDark} />;

  const actionFontSize = getActionFontSize(step.action.length);
  const tempDisplay = formatTemperature(step.temperature);

  const hasIngredients = step.ingredients?.length > 0;
  const rawIngredients = hasIngredients
    ? step.ingredients.filter((i) => !i.isProducedState)
    : [];
  const stateIngredients = hasIngredients
    ? step.ingredients.filter((i) => i.isProducedState)
    : [];

  return (
    <Fade in key={slideKey} timeout={200}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "100%",
          maxWidth: 640,
          gap: 3,
        }}
      >
        {/* Sub-recipe context — only when there are multiple */}
        {showSubRecipeTitle && (
          <Typography
            sx={{
              fontSize: "0.78rem",
              fontWeight: 600,
              color: "text.disabled",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
            }}
          >
            {step.subRecipeTitle}
          </Typography>
        )}

        {/* ════ HERO: the instruction ════ */}
        <Typography
          sx={{
            fontWeight: 500,
            textAlign: "center",
            lineHeight: 1.65,
            fontSize: actionFontSize,
            letterSpacing: "-0.01em",
            color: "text.primary",
            maxWidth: 580,
            px: { xs: 1, md: 2 },
          }}
        >
          {step.action}
        </Typography>

        {/* Context badges: temperature, visual cue, passive */}
        {(tempDisplay || step.visualCue || step.isPassive) && (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 1,
              justifyContent: "center",
            }}
          >
            {tempDisplay && (
              <ContextBadge
                icon={
                  <LocalFireDepartmentIcon
                    sx={{ fontSize: 16, color: "#ef5350" }}
                  />
                }
                text={tempDisplay}
                color="#ef5350"
                isDark={isDark}
              />
            )}
            {step.visualCue && (
              <ContextBadge
                icon={
                  <VisibilityIcon sx={{ fontSize: 16, color: "#ffa726" }} />
                }
                text={step.visualCue}
                color="#ffa726"
                isDark={isDark}
              />
            )}
            {step.isPassive && (
              <ContextBadge
                icon={
                  <HourglassEmptyIcon
                    sx={{ fontSize: 16, color: "#42a5f5" }}
                  />
                }
                text="Hands-free"
                color="#42a5f5"
                isDark={isDark}
              />
            )}
          </Box>
        )}

        {/* Timer */}
        {hasDuration && <CircularTimer timer={timer} isDark={isDark} />}

        {/* Ingredients */}
        {hasIngredients && (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 1,
              justifyContent: "center",
              px: 1,
            }}
          >
            {rawIngredients.map((ing, i) => (
              <IngredientPill
                key={`raw-${i}`}
                ingredient={ing}
                isDark={isDark}
              />
            ))}
            {stateIngredients.map((ing, i) => (
              <IngredientPill
                key={`state-${i}`}
                ingredient={ing}
                isDark={isDark}
              />
            ))}
          </Box>
        )}
      </Box>
    </Fade>
  );
};

export default StepContent;
