import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Tooltip } from "@mui/material";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import NutritionDialog from "./NutritionDialog/NutritionDialog";
import {
  NUTRITION_TAG_KEYS,
  NUTRITION_TAG_CRITERIA_KEYS,
  CONFIDENCE_COLORS,
  roundCalories,
} from "./NutritionDialog/constants";

const tagStyle = (clickable) => ({
  fontSize: "0.82rem",
  fontWeight: 500,
  color: "text.secondary",
  whiteSpace: "nowrap",
  ...(clickable && {
    cursor: "pointer",
    textDecoration: "underline",
    textDecorationColor: "rgba(128,128,128,0.25)",
    textUnderlineOffset: "3px",
    "&:hover": { opacity: 0.7 },
  }),
});

const NutritionCalories = ({ nutritionPerServing, onOpenDialog }) => {
  const { t } = useTranslation();
  if (!nutritionPerServing || nutritionPerServing.confidence === "none") return null;

  const confidence = nutritionPerServing.confidence || "none";
  const isHighConfidence = confidence === "high";

  if (confidence === "low") {
    return (
      <Typography component="span" sx={tagStyle(true)} onClick={onOpenDialog}>
        {t("nutrition.dataInsufficient")}
      </Typography>
    );
  }

  return (
    <>
      <Box
        component="span"
        sx={{ display: "inline-flex", alignItems: "center", gap: 0.25, ...tagStyle(true) }}
        onClick={onOpenDialog}
      >
        <LocalFireDepartmentOutlinedIcon sx={{ fontSize: "0.85rem", color: "text.disabled" }} />
        ~{roundCalories(nutritionPerServing.calories)} {t("nutrition.kcalPerServing")}
      </Box>
      {confidence === "medium" && (
        <Typography variant="caption" sx={{ color: CONFIDENCE_COLORS.medium, fontSize: "0.65rem", fontWeight: 500, opacity: 0.8 }}>
          {t("nutrition.estimation")}
        </Typography>
      )}
    </>
  );
};

const NutritionTags = ({ nutritionTags, hasDetailedData, onOpenDialog }) => {
  const { t } = useTranslation();
  if (!nutritionTags || nutritionTags.length === 0) return null;

  return nutritionTags.map((tag, index) => (
    <React.Fragment key={tag}>
      {index > 0 && <Box sx={{ width: "1px", height: 16, bgcolor: "divider", flexShrink: 0 }} />}
      <Tooltip
        title={NUTRITION_TAG_CRITERIA_KEYS[tag] ? t(NUTRITION_TAG_CRITERIA_KEYS[tag]) : ""}
        arrow
        placement="top"
        enterDelay={300}
        slotProps={{ tooltip: { sx: { fontSize: "0.72rem", maxWidth: 240 } } }}
      >
        <Typography
          component="span"
          sx={tagStyle(hasDetailedData)}
          onClick={hasDetailedData ? onOpenDialog : undefined}
        >
          {NUTRITION_TAG_KEYS[tag] ? t(NUTRITION_TAG_KEYS[tag]) : tag}
        </Typography>
      </Tooltip>
    </React.Fragment>
  ));
};

const NutritionTooltip = ({ nutritionTags, nutritionPerServing, recipeTitle, show = "all" }) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  if ((!nutritionTags || nutritionTags.length === 0) && !nutritionPerServing) {
    return null;
  }

  const tags = nutritionTags || [];
  const hasDetailedData = nutritionPerServing && nutritionPerServing.confidence !== "none";
  const isHighConfidence = nutritionPerServing?.confidence === "high";
  const openDialog = () => setDialogOpen(true);

  return (
    <>
      {(show === "all" || show === "calories") && (
        <NutritionCalories nutritionPerServing={nutritionPerServing} onOpenDialog={openDialog} />
      )}

      {(show === "all" || show === "tags") && isHighConfidence && tags.length > 0 && (
        <NutritionTags nutritionTags={tags} hasDetailedData={hasDetailedData} onOpenDialog={openDialog} />
      )}

      {hasDetailedData && (
        <NutritionDialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          recipeTitle={recipeTitle}
          nutritionPerServing={nutritionPerServing}
          nutritionTags={tags}
        />
      )}
    </>
  );
};

export default NutritionTooltip;
