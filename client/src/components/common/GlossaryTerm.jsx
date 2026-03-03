import React, { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Chip, Popover, IconButton } from "@mui/material";
import AutoStoriesOutlinedIcon from "@mui/icons-material/AutoStoriesOutlined";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import { useTheme } from "../../contexts/ThemeContext";

const resolveLocalized = (entry, language) => {
  const loc = entry?.localized?.[language];
  return {
    term: loc?.term || entry?.term,
    definition: loc?.definition || entry?.definition,
  };
};

const CATEGORY_COLORS = {
  light: {
    cooking_method: { bg: "#FFF3E0", color: "#E65100" },
    knife_cut: { bg: "#E8F5E9", color: "#2E7D32" },
    sauce_technique: { bg: "#FBE9E7", color: "#BF360C" },
    preparation: { bg: "#E3F2FD", color: "#1565C0" },
    baking: { bg: "#FFF8E1", color: "#F9A825" },
    texture_state: { bg: "#F3E5F5", color: "#7B1FA2" },
  },
  dark: {
    cooking_method: { bg: "rgba(230, 81, 0, 0.15)", color: "#FFB74D" },
    knife_cut: { bg: "rgba(46, 125, 50, 0.15)", color: "#81C784" },
    sauce_technique: { bg: "rgba(191, 54, 12, 0.15)", color: "#FF8A65" },
    preparation: { bg: "rgba(21, 101, 192, 0.15)", color: "#64B5F6" },
    baking: { bg: "rgba(249, 168, 37, 0.15)", color: "#FFD54F" },
    texture_state: { bg: "rgba(123, 31, 162, 0.15)", color: "#CE93D8" },
  },
};

const DEFAULT_CATEGORY_COLOR = {
  light: { bg: "#F5F5F5", color: "#616161" },
  dark: { bg: "rgba(255,255,255,0.08)", color: "#aaa" },
};

const TermContent = ({ entry, categoryMap, onNavigate, showBack, language }) => {
  const { darkMode } = useTheme();
  const { t } = useTranslation();
  const mode = darkMode ? "dark" : "light";
  const catStyle = CATEGORY_COLORS[mode][entry.category] || DEFAULT_CATEGORY_COLOR[mode];
  const catLabel = categoryMap?.[entry.category] || entry.category;
  const { term, definition } = resolveLocalized(entry, language);

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        {showBack && (
          <IconButton size="small" onClick={onNavigate} sx={{ ml: -0.5, mr: -0.5 }}>
            <ArrowBackIosNewIcon sx={{ fontSize: 14 }} />
          </IconButton>
        )}
        <AutoStoriesOutlinedIcon sx={{ fontSize: 18, color: "text.secondary" }} />
        <Typography
          variant="subtitle2"
          sx={{ fontWeight: 700, textTransform: "capitalize" }}
        >
          {term}
        </Typography>
      </Box>

      <Chip
        label={catLabel}
        size="small"
        sx={{
          mb: 1.5,
          height: 22,
          fontSize: "0.7rem",
          fontWeight: 600,
          backgroundColor: catStyle.bg,
          color: catStyle.color,
        }}
      />

      <Typography
        variant="body2"
        sx={{ color: "text.secondary", lineHeight: 1.6 }}
      >
        {definition}
      </Typography>

      {entry.related?.length > 0 && (
        <Box
          sx={{
            mt: 1.5,
            display: "flex",
            flexWrap: "wrap",
            gap: 0.5,
            alignItems: "center",
          }}
        >
          <Typography variant="caption" sx={{ color: "text.disabled", mr: 0.5 }}>
            {t("glossary.related")}
          </Typography>
          {entry.related.map((id) => (
            <Chip
              key={id}
              label={id.replace(/_/g, " ")}
              size="small"
              variant="outlined"
              onClick={(e) => {
                e.stopPropagation();
                onNavigate?.(id);
              }}
              sx={{
                height: 20,
                fontSize: "0.65rem",
                textTransform: "capitalize",
                borderColor: "divider",
                cursor: "pointer",
                "&:hover": { borderColor: "text.secondary" },
              }}
            />
          ))}
        </Box>
      )}
    </Box>
  );
};

const GlossaryTerm = ({ entry, allTerms, categoryMap, language, children }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [activeEntry, setActiveEntry] = useState(null);

  const handleClick = useCallback((e) => {
    e.stopPropagation();
    e.preventDefault();
    setAnchorEl(e.currentTarget);
    setActiveEntry(null);
  }, []);

  const handleClose = useCallback(() => {
    setAnchorEl(null);
    setActiveEntry(null);
  }, []);

  const handleNavigate = useCallback(
    (termId) => {
      if (!termId) {
        setActiveEntry(null);
        return;
      }
      const found = allTerms?.find((t) => t.id === termId);
      if (found) setActiveEntry(found);
    },
    [allTerms]
  );

  const open = Boolean(anchorEl);
  const displayEntry = activeEntry || entry;

  return (
    <>
      <Box
        component="span"
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") handleClick(e);
        }}
        sx={{
          borderBottom: "1.5px dotted",
          borderColor: "text.disabled",
          cursor: "help",
          transition: "border-color 0.15s, color 0.15s",
          "&:hover": {
            borderColor: "primary.main",
            color: "primary.main",
          },
        }}
      >
        {children}
      </Box>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        transformOrigin={{ vertical: "top", horizontal: "center" }}
        onClick={(e) => e.stopPropagation()}
        slotProps={{
          paper: {
            sx: {
              maxWidth: 340,
              borderRadius: 2,
              boxShadow: (theme) => theme.palette.mode === "dark" ? "0 8px 32px rgba(0,0,0,0.4)" : "0 8px 32px rgba(0,0,0,0.12)",
              mt: 0.5,
            },
          },
        }}
      >
        <TermContent
          entry={displayEntry}
          categoryMap={categoryMap}
          showBack={!!activeEntry}
          onNavigate={activeEntry ? () => setActiveEntry(null) : handleNavigate}
          language={language}
        />
      </Popover>
    </>
  );
};

export default GlossaryTerm;
