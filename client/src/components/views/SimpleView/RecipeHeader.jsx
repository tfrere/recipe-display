import React, { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  IconButton,
  Typography,
  useTheme,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
} from "@mui/material";
import PrintOutlinedIcon from "@mui/icons-material/PrintOutlined";
import ViewTimelineOutlinedIcon from "@mui/icons-material/ViewTimelineOutlined";
import RestaurantMenuIcon from "@mui/icons-material/RestaurantMenu";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import GroupOutlinedIcon from "@mui/icons-material/GroupOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import CloseIcon from "@mui/icons-material/Close";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import { useRecipe } from "../../../contexts/RecipeContext";
import { useConstants } from "../../../contexts/ConstantsContext";
import RecipeImage from "../../common/RecipeImage";
import { parseTimeToMinutes, formatTimeCompact } from "../../../utils/timeUtils";
import NutritionTooltip from "../../common/NutritionTooltip";
import { GanttModal } from "../../views/GanttView";
import { CookingModal } from "../../views/CookingMode";

const RecipeHeader = ({ recipe, onPrint }) => {
  const { t } = useTranslation();
  const {
    updateServings,
    currentServings,
    getRemainingTime,
    tools,
    formatAmount,
    getAdjustedAmount,
  } = useRecipe();
  const theme = useTheme();
  const { constants } = useConstants();
  const [openGantt, setOpenGantt] = useState(false);
  const [openCooking, setOpenCooking] = useState(false);
  const [imageRatio, setImageRatio] = useState(1);
  const [openOriginalText, setOpenOriginalText] = useState(false);
  const [notesExpanded, setNotesExpanded] = useState(false);

  // Attendre que les constantes soient chargées
  if (!constants) {
    return null;
  }

  const seasonText = useMemo(() => {
    const recipeSeasons = recipe.metadata?.seasons || recipe.seasons;

    if (Array.isArray(recipeSeasons) && recipeSeasons.length > 0) {
      if (recipeSeasons.includes("all")) {
        return t("seasons.all");
      }
      return recipeSeasons
        .map((seasonId) => t(`seasons.${seasonId}`, { defaultValue: seasonId }))
        .join(", ");
    }
    return t("seasons.all");
  }, [recipe.metadata?.seasons, recipe.seasons, t]);

  // Déstructurer les propriétés de la recette
  const { metadata = {} } = recipe || {};

  const handleImageLoad = (ratio) => {
    setImageRatio(ratio);
  };

  const handleServingsChange = (delta) => {
    const newServings = currentServings + delta;
    if (newServings >= 1) {
      updateServings(newServings);
    }
  };

  const handlePrint = () => {
    if (onPrint) onPrint();
    else window.print();
  };

  if (!recipe) {
    return null;
  }

  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          width: "100%",
          maxWidth: "100%",
          "@media print": { gap: 0.5 },
        }}
      >
        {/* Recipe Header Content */}
        <Box sx={{ width: "100%" }}>
          {/* Title and Image Section */}
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              gap: { xs: 3, md: 6 },
              mb: 3,
              width: "100%",
              "@media print": { mb: 0, gap: 0 },
            }}
          >
            {/* Square Image */}
            <Box
              sx={{
                width: "100%",
                maxWidth: { xs: "100%", md: 360 },
                maxHeight: 520,
                height: "auto",
                aspectRatio: "1 / 1",
                flexShrink: 0,
                position: "relative",
                borderRadius: 2,
                overflow: "hidden",
                boxShadow: (theme) =>
                  theme.palette.mode === "dark"
                    ? "0 12px 24px rgba(0, 0, 0, 0.3)"
                    : "0 12px 24px rgba(0, 0, 0, 0.1)",
                "&::after": {
                  content: '""',
                  position: "absolute",
                  inset: 0,
                  background: (theme) => `linear-gradient(to bottom, 
                  ${
                    theme.palette.mode === "dark"
                      ? "rgba(0, 0, 0, 0.2)"
                      : "rgba(255, 255, 255, 0.1)"
                  } 0%,
                  transparent 40%,
                  ${
                    theme.palette.mode === "dark"
                      ? "rgba(0, 0, 0, 0.4)"
                      : "rgba(0, 0, 0, 0.2)"
                  } 100%)`,
                  pointerEvents: "none",
                },
                "@media print": {
                  display: "none",
                },
              }}
            >
              <RecipeImage
                slug={recipe.slug}
                title={recipe.title}
                size="original"
                onLoad={handleImageLoad}
              />
            </Box>

            {/* Info Column */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                flex: 1,
                pt: 2,
                "@media print": { pt: 0 },
              }}
            >
              {/* ── Zone 1: Identity ── */}
              {metadata.author && (
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.disabled",
                    fontSize: "0.75rem",
                    fontWeight: 500,
                    letterSpacing: "0.02em",
                    textTransform: "uppercase",
                  }}
                >
                  {metadata.author}
                </Typography>
              )}
              <Typography
                variant="h3"
                component="h1"
                sx={{ fontWeight: 700, fontSize: "2rem", mb: 1, "@media print": { mb: 0.25, fontSize: "1.5rem" } }}
              >
                {recipe.metadata.title}
              </Typography>

              {recipe.metadata.description && (
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ lineHeight: 1.6, fontSize: "0.95rem", mb: 1.5, "@media print": { mb: 0.25, fontSize: "0.82rem", lineHeight: 1.4 } }}
                >
                  {recipe.metadata.description}
                </Typography>
              )}

              {/* Metadata line */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  flexWrap: "wrap",
                  width: "100%",
                  mt: 2,
                  py: 1.5,
                  borderTop: "1px solid",
                  borderColor: "divider",
                  "@media print": { mt: 0.5, py: 0.5, borderTop: "none" },
                }}
              >
                <Typography variant="body2" sx={{ textTransform: "capitalize", color: "text.secondary", fontSize: "0.82rem" }}>
                  {t(`types.${metadata.recipeType || metadata.type}`, { defaultValue: t("recipe.main") })}
                </Typography>
                <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0 }} />
                <Typography variant="body2" sx={{ textTransform: "capitalize", color: "text.secondary", fontSize: "0.82rem" }}>
                  {t(`diets.${metadata.diets?.[0]}`, { defaultValue: metadata.diets?.[0] || "" })}
                </Typography>
                <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0 }} />
                <Typography variant="body2" sx={{ textTransform: "capitalize", color: "text.secondary", fontSize: "0.82rem" }}>
                  {seasonText}
                </Typography>
              </Box>

              {/* ── Zone 2: Quick facts strip ── */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  flexWrap: "wrap",
                  width: "100%",
                  py: 1.5,
                  borderTop: "1px solid",
                  borderColor: "divider",
                  "@media print": {
                    py: 0.5,
                    borderTop: "none",
                  },
                }}
              >
                {/* Servings control */}
                {(() => {
                  const isModified = currentServings !== recipe.metadata.servings;
                  return (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 0.5,
                        }}
                      >
                        {currentServings === 1 ? (
                          <PersonOutlineIcon sx={{ color: "text.secondary", fontSize: 18 }} />
                        ) : (
                          <GroupOutlinedIcon sx={{ color: "text.secondary", fontSize: 18 }} />
                        )}
                        <Typography
                          variant="body2"
                          component="span"
                          sx={{
                            color: "text.secondary",
                            fontSize: "0.82rem",
                            fontWeight: isModified ? 700 : 500,
                            minWidth: "1.2em",
                            textAlign: "center",
                            display: "inline-block",
                            transition: "font-weight 0.2s ease",
                          }}
                        >
                          {currentServings}
                        </Typography>
                        <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.82rem", fontWeight: 500, whiteSpace: "nowrap" }}>
                          {currentServings === 1 ? t("recipe.servingLabel_one") : t("recipe.servingLabel_other")}
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", gap: 0.25, ml: 1, "@media print": { display: "none" } }}>
                        <Button
                          onClick={() => handleServingsChange(-1)}
                          disabled={currentServings <= 1}
                          size="small"
                          variant="outlined"
                          sx={{
                            minWidth: 0,
                            p: 0.25,
                            borderColor: currentServings < recipe.metadata.servings ? "text.secondary" : "divider",
                            color: "text.secondary",
                            transition: "border-color 0.2s ease",
                            "&:hover": { borderColor: "text.primary", backgroundColor: "action.hover" },
                            "&.Mui-disabled": { borderColor: currentServings < recipe.metadata.servings ? "text.secondary" : "divider", color: "text.disabled" },
                          }}
                        >
                          <KeyboardArrowDownIcon sx={{ fontSize: "0.9rem" }} />
                        </Button>
                        <Button
                          onClick={() => handleServingsChange(1)}
                          size="small"
                          variant="outlined"
                          sx={{
                            minWidth: 0,
                            p: 0.25,
                            borderColor: currentServings > recipe.metadata.servings ? "text.secondary" : "divider",
                            color: "text.secondary",
                            transition: "border-color 0.2s ease",
                            "&:hover": { borderColor: "text.primary", backgroundColor: "action.hover" },
                          }}
                        >
                          <KeyboardArrowUpIcon sx={{ fontSize: "0.9rem" }} />
                        </Button>
                      </Box>
                    </Box>
                  );
                })()}

                {/* Time display with rich tooltip */}
                {(() => {
                  const totalRaw = metadata.totalTimeMinutes || metadata.totalTime || recipe.totalTime;
                  if (!totalRaw) return null;
                  const total = typeof totalRaw === "number" ? totalRaw : parseTimeToMinutes(totalRaw);
                  const active = metadata.totalActiveTimeMinutes
                    || (metadata.totalActiveTime ? parseTimeToMinutes(metadata.totalActiveTime) : null);
                  const passive = metadata.totalPassiveTimeMinutes
                    || (metadata.totalPassiveTime ? parseTimeToMinutes(metadata.totalPassiveTime) : null);

                  const segments = [];
                  if (active && passive) {
                    segments.push({ label: t("recipeTimes.active"), value: active, color: "text.secondary" });
                    segments.push({ label: t("recipeTimes.passive"), value: passive, color: "text.disabled" });
                  } else if (active) {
                    segments.push({ label: t("recipeTimes.active"), value: active, color: "text.secondary" });
                    if (total > active) segments.push({ label: t("recipeTimes.passive"), value: total - active, color: "text.disabled" });
                  } else if (passive) {
                    if (total > passive) segments.push({ label: t("recipeTimes.active"), value: total - passive, color: "text.secondary" });
                    segments.push({ label: t("recipeTimes.passive"), value: passive, color: "text.disabled" });
                  }
                  const hasBar = segments.length > 1;

                  return (
                    <>
                      <Box sx={{ width: "1px", height: 24, bgcolor: "divider", flexShrink: 0 }} />
                      <Tooltip
                        arrow
                        placement="bottom"
                        title={hasBar ? (
                          <Box sx={{ py: 0.5, minWidth: 180 }}>
                            <Box sx={{ display: "flex", borderRadius: 1, overflow: "hidden", height: 6, mb: 1 }}>
                              {segments.map((seg, i) => (
                                <Box key={i} sx={{ flex: seg.value, bgcolor: i === 0 ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.25)" }} />
                              ))}
                            </Box>
                            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                              {segments.map((seg, i) => (
                                <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                  <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: i === 0 ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.25)", flexShrink: 0 }} />
                                  <Typography variant="caption" sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.6)" }}>
                                    {seg.label}
                                  </Typography>
                                  <Typography variant="caption" sx={{ fontSize: "0.7rem", fontWeight: 600 }}>
                                    {formatTimeCompact(seg.value)}
                                  </Typography>
                                </Box>
                              ))}
                            </Box>
                          </Box>
                        ) : ""}
                      >
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, cursor: hasBar ? "help" : "default" }}>
                          <AccessTimeOutlinedIcon sx={{ fontSize: "0.95rem", color: "text.disabled" }} />
                          <Typography
                            variant="body2"
                            sx={{ color: "text.secondary", fontWeight: 500, fontSize: "0.82rem", ...(hasBar && { textDecoration: "underline", textDecorationColor: "rgba(128,128,128,0.25)", textUnderlineOffset: "3px" }) }}
                          >
                            {formatTimeCompact(total)}
                          </Typography>
                        </Box>
                      </Tooltip>
                    </>
                  );
                })()}

                {/* Calories inline */}
                {metadata.nutritionPerServing && metadata.nutritionPerServing.confidence !== "none" && (
                  <>
                    <Box sx={{ width: "1px", height: 24, bgcolor: "divider", flexShrink: 0, "@media print": { display: "none" } }} />
                    <Box sx={{ display: "contents", "@media print": { display: "none" } }}>
                      <NutritionTooltip
                        show="calories"
                        recipeTitle={metadata.title}
                        nutritionTags={metadata.nutritionTags}
                        nutritionPerServing={{
                          ...metadata.nutritionPerServing,
                          servings: metadata.servings,
                        }}
                      />
                    </Box>
                  </>
                )}
              </Box>


              {/* ── Zone 3: Actions ── */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  width: "100%",
                  py: 1.5,
                  borderTop: "1px solid",
                  borderColor: "divider",
                  "@media print": { display: "none" },
                }}
              >
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 0.75, cursor: "pointer", "&:hover": { opacity: 0.7 } }}
                  onClick={() => setOpenCooking(true)}
                >
                  <RestaurantMenuIcon sx={{ fontSize: "0.95rem", color: "text.secondary" }} />
                  <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.82rem", fontWeight: 500, textDecoration: "underline", textDecorationColor: "rgba(128,128,128,0.25)", textUnderlineOffset: "3px" }}>
                    {t("recipe.showCooking")}
                  </Typography>
                </Box>

                {metadata.sourceUrl && (
                  <>
                    <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0 }} />
                    <Tooltip title={t("recipe.source")} arrow>
                      <Box
                        component="a"
                        href={metadata.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ display: "flex", alignItems: "center", p: 0.5, borderRadius: 1, color: "text.disabled", textDecoration: "none", "&:hover": { color: "text.secondary", bgcolor: "action.hover" } }}
                      >
                        <OpenInNewIcon sx={{ fontSize: "1rem" }} />
                      </Box>
                    </Tooltip>
                  </>
                )}
                {recipe.originalText && (
                  <>
                    <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0 }} />
                    <Tooltip title={t("recipe.originalText")} arrow>
                      <Box
                        sx={{ display: "flex", alignItems: "center", p: 0.5, borderRadius: 1, cursor: "pointer", color: "text.disabled", "&:hover": { color: "text.secondary", bgcolor: "action.hover" } }}
                        onClick={() => setOpenOriginalText(true)}
                      >
                        <DescriptionOutlinedIcon sx={{ fontSize: "1rem" }} />
                      </Box>
                    </Tooltip>
                  </>
                )}
                <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0, display: { xs: "none", md: "block" } }} />
                <Tooltip title={t("recipe.timeline")} arrow>
                  <Box
                    sx={{ display: { xs: "none", md: "flex" }, alignItems: "center", p: 0.5, borderRadius: 1, cursor: "pointer", color: "text.disabled", "&:hover": { color: "text.secondary", bgcolor: "action.hover" } }}
                    onClick={() => setOpenGantt(true)}
                  >
                    <ViewTimelineOutlinedIcon sx={{ fontSize: "1rem" }} />
                  </Box>
                </Tooltip>
                <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0, display: { xs: "none", md: "block" } }} />
                <Tooltip title={t("recipe.print")} arrow>
                  <Box
                    sx={{ display: { xs: "none", md: "flex" }, alignItems: "center", p: 0.5, borderRadius: 1, cursor: "pointer", color: "text.disabled", "&:hover": { color: "text.secondary", bgcolor: "action.hover" } }}
                    onClick={handlePrint}
                  >
                    <PrintOutlinedIcon sx={{ fontSize: "1rem" }} />
                  </Box>
                </Tooltip>
              </Box>

              {/* ── Notes — accordion ── */}
              {metadata.notes &&
                Array.isArray(metadata.notes) &&
                metadata.notes.length > 0 && (
                  <Box sx={{ mt: 1.5, width: "100%", "@media print": { mt: 0.25 } }}>
                    <Box
                      sx={{
                        overflow: "hidden",
                        maxHeight: notesExpanded ? "500px" : "2.4em",
                        transition: "max-height 0.3s ease",
                        "@media print": { maxHeight: "none" },
                      }}
                    >
                      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
                        {metadata.notes.map((note, i) => (
                          <Typography
                            key={i}
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontStyle: "italic", fontSize: "0.78rem", lineHeight: 1.5, opacity: 0.55 }}
                          >
                            {note}
                          </Typography>
                        ))}
                      </Box>
                    </Box>

                    {metadata.notes.length > 1 && (
                      <Box
                        onClick={() => setNotesExpanded((prev) => !prev)}
                        sx={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 0.25,
                          mt: 0.5,
                          cursor: "pointer",
                          color: "text.disabled",
                          "&:hover": { color: "text.secondary" },
                          "@media print": { display: "none" },
                        }}
                      >
                        <Typography component="span" variant="caption" sx={{ fontSize: "0.72rem" }}>
                          {notesExpanded ? t("recipe.readLess") : t("recipe.readMore")}
                        </Typography>
                        <KeyboardArrowDownIcon
                          sx={{
                            fontSize: "0.85rem",
                            transition: "transform 0.3s ease",
                            transform: notesExpanded ? "rotate(180deg)" : "rotate(0deg)",
                          }}
                        />
                      </Box>
                    )}
                  </Box>
                )}
            </Box>
          </Box>
        </Box>
      </Box>

      <GanttModal
        open={openGantt}
        onClose={() => setOpenGantt(false)}
        recipe={recipe}
      />

      <CookingModal
        open={openCooking}
        onClose={() => setOpenCooking(false)}
        recipe={recipe}
      />

      {/* Original recipe text modal */}
      <Dialog
        open={openOriginalText}
        onClose={() => setOpenOriginalText(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            pb: 1,
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("recipe.originalText")}
          </Typography>
          <IconButton
            onClick={() => setOpenOriginalText(false)}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Box
            sx={{
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              fontSize: "0.85rem",
              lineHeight: 1.7,
              color: "text.secondary",
              maxHeight: "60vh",
              overflow: "auto",
            }}
          >
            {recipe.originalText}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default RecipeHeader;
