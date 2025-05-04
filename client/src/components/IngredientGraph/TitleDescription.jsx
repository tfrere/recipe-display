import React from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";

const TitleDescription = ({ theme }) => {
  return (
    <Box
      sx={{
        position: "absolute",
        top: 20,
        left: 20,
        width: 400,
        padding: 3,
        backgroundColor: "#f5f5f5",
        opacity: 0.85,
        borderRadius: 2,
        pointerEvents: "none",
        zIndex: 10,
      }}
    >
      <Typography
        variant="h6"
        sx={{
          fontSize: "20px",
          fontWeight: 500,
          letterSpacing: "0.05em",
          color: theme.palette.text.primary,
          marginBottom: 2,
        }}
      >
        Ingredient Flavor Similarity Map
      </Typography>

      <Typography
        variant="body2"
        sx={{
          color: theme.palette.text.secondary,
          fontWeight: 300,
          marginBottom: 2,
        }}
      >
        This visualization shows ingredients positioned by flavor similarity
        using t-SNE dimensionality reduction.
        <br />
        <span style={{ fontWeight: 500 }}>
          Closer ingredients share similar flavor
        </span>
        <span style={{ fontWeight: 300 }}> compounds.</span>
      </Typography>

      <Typography
        variant="caption"
        sx={{
          color: theme.palette.text.secondary,
          fontStyle: "italic",
          opacity: 0.8,
        }}
      >
        Drag to pan • Scroll to zoom • Hover for details
      </Typography>
    </Box>
  );
};

TitleDescription.propTypes = {
  theme: PropTypes.object.isRequired,
};

export default TitleDescription;
