import React from "react";
import { Box, Typography, Checkbox } from "@mui/material";
import { segmentGlossaryOnly } from "../../../../utils/textUtils";
import GlossaryTerm from "../../../common/GlossaryTerm";

const renderGlossarySegments = (text, glossary) => {
  if (!glossary?.matchTerms?.length) return text;

  const segments = segmentGlossaryOnly(text, glossary.matchTerms);
  return segments.map((seg, i) => {
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
};

const IngredientItem = ({
  ingredient,
  sortByCategory,
  isChecked,
  onCheckChange,
  glossary,
}) => {
  return (
    <Box
      key={`${ingredient.subRecipeId}-${ingredient.id}`}
      sx={{
        display: "grid",
        gridTemplateColumns: sortByCategory
          ? "0.3fr 0.7fr auto"
          : "0.3fr 0.7fr",
        gap: 2,
        alignItems: "start",
        py: 0.25,
        mb: 0.75,
        opacity: sortByCategory
          ? isChecked ? 0.5 : 1
          : ingredient.isUnused ? 0.5 : 1,
        textDecoration: sortByCategory
          ? isChecked ? "line-through" : "none"
          : ingredient.isUnused
          ? "line-through"
          : "none",
        transition: "opacity 0.15s, text-decoration 0.15s",
      }}
    >
      <Typography
        variant="body1"
        sx={{
          color: "text.secondary",
          textAlign: "left",
        }}
      >
        {ingredient.displayAmount}
      </Typography>

      <Box sx={{ textAlign: "right" }}>
        <Typography variant="body1" component="span">
          {ingredient.name}
          {ingredient.displayState && (
            <span style={{ fontStyle: "italic", marginLeft: "4px" }}>
              ({renderGlossarySegments(ingredient.displayState, glossary)})
            </span>
          )}
        </Typography>
        {ingredient.initialState && !sortByCategory && (
          <Typography
            variant="body2"
            component="div"
            sx={{
              fontStyle: "italic",
              color: "text.secondary",
              fontSize: "0.85em",
              mt: 0,
              opacity: 0.8,
            }}
          >
            {renderGlossarySegments(ingredient.initialState, glossary)}
          </Typography>
        )}
      </Box>

      {sortByCategory && (
        <Box sx={{ textAlign: "right", "@media print": { display: "none" } }}>
          <Checkbox
            checked={isChecked}
            onChange={(e) => onCheckChange(ingredient, e.target.checked)}
            size="small"
            sx={{ p: 0.2 }}
          />
        </Box>
      )}
    </Box>
  );
};

export default IngredientItem;
