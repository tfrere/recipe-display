import React from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Fade, useTheme } from "@mui/material";
import { useGlossary } from "../../../hooks/useGlossary";
import { segmentGlossaryOnly } from "../../../utils/textUtils";
import GlossaryTerm from "../../common/GlossaryTerm";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import VisibilityIcon from "@mui/icons-material/Visibility";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import SubdirectoryArrowRightIcon from "@mui/icons-material/SubdirectoryArrowRight";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CircularTimer from "./CircularTimer";
import { formatTemperature, getActionFontSize } from "./utils";
import { useRecipe } from "../../../contexts/RecipeContext";

const renderGlossarySegments = (segments, glossary) =>
  segments.map((seg, i) => {
    if (seg.type === "glossary" && seg.glossaryEntry) {
      return (
        <GlossaryTerm
          key={i}
          entry={seg.glossaryEntry}
          allTerms={glossary.terms}
          categoryMap={glossary.categoryMap}
          language={glossary.language}
        >
          {seg.text}
        </GlossaryTerm>
      );
    }
    return <React.Fragment key={i}>{seg.text}</React.Fragment>;
  });

const ContextBadge = ({ icon, text, color }) => (
  <Box
    sx={{
      display: "inline-flex",
      alignItems: "center",
      gap: 0.75,
      px: 1.5,
      py: 0.625,
      borderRadius: "20px",
      bgcolor: `${color}15`,
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

const IngredientPill = ({ ingredient, formatAmount, getAdjustedAmount }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  if (ingredient.isProducedState) {
    const displayName = ingredient.name
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

    return (
      <Box
        sx={{
          display: "inline-flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 0.25,
          px: 1.25,
          py: 0.5,
          borderRadius: "8px",
          bgcolor: "rgba(100, 180, 255, 0.06)",
          border: "1px solid rgba(100, 180, 255, 0.1)",
          minWidth: 48,
        }}
      >
        <Typography
          sx={{
            fontSize: "0.72rem",
            fontWeight: 500,
            color: "rgba(100,180,255,0.7)",
            lineHeight: 1.2,
            fontStyle: "italic",
            textAlign: "center",
          }}
        >
          {displayName}
        </Typography>
      </Box>
    );
  }

  const unit = ingredient.unit;
  const adjusted =
    ingredient.amount != null && getAdjustedAmount
      ? getAdjustedAmount(ingredient.amount, unit, ingredient.category)
      : ingredient.amount;
  const qty =
    adjusted != null && formatAmount
      ? formatAmount(adjusted, unit, ingredient)
      : `${ingredient.amount || ""} ${unit || ""}`.trim();
  const name = (ingredient.name || ingredient.ref || "").trim();

  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 1,
        px: 1.25,
        py: 0.5,
        borderRadius: "8px",
        bgcolor: isDark
          ? "rgba(255, 255, 255, 0.05)"
          : "rgba(0, 0, 0, 0.04)",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Typography
        sx={{
          fontSize: "0.82rem",
          fontWeight: 600,
          color: "text.primary",
          lineHeight: 1.25,
        }}
      >
        {name}
      </Typography>
      {qty && (
        <>
          <Box
            sx={{
              width: "1px",
              alignSelf: "stretch",
              my: 0.125,
              bgcolor: "divider",
            }}
          />
          <Typography
            sx={{
              fontSize: "0.68rem",
              fontWeight: 400,
              color: "text.disabled",
              lineHeight: 1.2,
              fontVariantNumeric: "tabular-nums",
              whiteSpace: "nowrap",
            }}
          >
            {qty}
          </Typography>
        </>
      )}
    </Box>
  );
};

const CompletionScreen = () => {
  const { t } = useTranslation();
  return (
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
            bgcolor: "rgba(76,175,80,0.1)",
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
            color: "text.primary",
          }}
        >
          {t("cooking.bonAppetit")}
        </Typography>
        <Typography sx={{ color: "text.secondary", fontSize: "0.95rem", maxWidth: 320 }}>
          {t("cooking.allStepsDone")}
        </Typography>
      </Box>
    </Fade>
  );
};

const StepContent = ({
  step,
  timer,
  hasDuration,
  slideKey,
  isCompleted,
  showSubRecipeTitle,
  language,
}) => {
  const { t } = useTranslation();
  const glossary = useGlossary(language);
  const { formatAmount, getAdjustedAmount } = useRecipe();

  if (isCompleted) return <CompletionScreen />;

  const actionFontSize = getActionFontSize(step.action.length);
  const tempDisplay = formatTemperature(step.temperature);

  const hasIngredients = step.ingredients?.length > 0;
  const rawIngredients = hasIngredients
    ? step.ingredients.filter((i) => !i.isProducedState)
    : [];
  const stateIngredients = hasIngredients
    ? step.ingredients.filter((i) => i.isProducedState)
    : [];

  const segments = segmentGlossaryOnly(step.action, glossary.matchTerms);

  return (
    <Fade in key={slideKey} timeout={200}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "100%",
          maxWidth: 600,
          gap: 2.5,
        }}
      >
        {showSubRecipeTitle && (
          <Typography
            sx={{
              fontSize: "0.68rem",
              fontWeight: 500,
              color: "text.disabled",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
            }}
          >
            {step.subRecipeTitle}
          </Typography>
        )}

        <Typography
          component="div"
          sx={{
            fontWeight: 400,
            textAlign: "center",
            lineHeight: 1.7,
            fontSize: actionFontSize,
            letterSpacing: "-0.01em",
            color: "text.primary",
            maxWidth: 540,
            maxHeight: { xs: "40vh", md: "35vh" },
            overflowY: "auto",
            px: { xs: 0.5, md: 1 },
          }}
        >
          {renderGlossarySegments(segments, glossary)}
        </Typography>

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
              />
            )}
            {step.visualCue && (
              <ContextBadge
                icon={
                  <VisibilityIcon sx={{ fontSize: 16, color: "#ffa726" }} />
                }
                text={step.visualCue}
                color="#ffa726"
              />
            )}
            {step.isPassive && (
              <ContextBadge
                icon={
                  <HourglassEmptyIcon
                    sx={{ fontSize: 16, color: "#42a5f5" }}
                  />
                }
                text={t("cooking.handsFree")}
                color="#42a5f5"
              />
            )}
          </Box>
        )}

        {hasDuration && <CircularTimer timer={timer} />}

        {hasIngredients && (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 0.75,
              justifyContent: "center",
            }}
          >
            {rawIngredients.map((ing, i) => (
              <IngredientPill
                key={`raw-${i}`}
                ingredient={ing}
                formatAmount={formatAmount}
                getAdjustedAmount={getAdjustedAmount}
              />
            ))}
            {stateIngredients.map((ing, i) => (
              <IngredientPill
                key={`state-${i}`}
                ingredient={ing}
                formatAmount={formatAmount}
                getAdjustedAmount={getAdjustedAmount}
              />
            ))}
          </Box>
        )}
      </Box>
    </Fade>
  );
};

export default StepContent;
