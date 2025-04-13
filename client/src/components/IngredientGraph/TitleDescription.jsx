import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import PropTypes from "prop-types";

const TitleDescription = ({ theme }) => {
  const titleDescRef = useRef(null);

  useEffect(() => {
    if (!titleDescRef.current) return;

    // Nettoyer le SVG avant de dessiner
    d3.select(titleDescRef.current).selectAll("*").remove();

    // Créer le titre et la description (fixes)
    const titleDesc = d3.select(titleDescRef.current);

    // Dimensions et padding
    const padding = 24;
    const width = 400;
    const lineHeight = 22;
    const titleHeight = 32;

    // Fond pour le titre et la description
    titleDesc
      .append("rect")
      .attr("width", width)
      .attr("height", 190)
      .attr("fill", "#f5f5f5")
      .attr("opacity", 0.85)
      .attr("rx", 8);

    // Titre - plus grand et élégant
    titleDesc
      .append("text")
      .attr("x", padding)
      .attr("y", padding + titleHeight / 2)
      .style("font-size", "20px")
      .style("font-weight", "500") // Plus léger pour un style épuré
      .style("fill", theme.palette.text.primary)
      .style("letter-spacing", "0.05em") // Espacement des lettres pour élégance
      .text("Ingredient Flavor Similarity Map");

    // Description - texte plus léger
    const descriptions = [
      "This visualization shows ingredients positioned by",
      "flavor similarity using t-SNE dimensionality reduction.",
      "Closer ingredients share similar flavor compounds.",
    ];

    descriptions.forEach((text, i) => {
      titleDesc
        .append("text")
        .attr("x", padding)
        .attr("y", padding + titleHeight + 20 + i * lineHeight)
        .style("font-size", "14px")
        .style("font-weight", "300")
        .style("fill", theme.palette.text.secondary)
        .text(text);
    });

    // Instructions de navigation
    titleDesc
      .append("text")
      .attr("x", padding)
      .attr(
        "y",
        padding + titleHeight + 15 + descriptions.length * lineHeight + 24
      )
      .style("font-size", "13px")
      .style("font-style", "italic")
      .style("fill", theme.palette.text.secondary)
      .style("opacity", 0.8)
      .text("Drag to pan • Scroll to zoom • Hover for details");
  }, [theme]);

  return (
    <svg
      ref={titleDescRef}
      width="400"
      height="190"
      style={{
        position: "absolute",
        top: 20,
        left: 20,
        pointerEvents: "none",
        zIndex: 10,
      }}
    />
  );
};

TitleDescription.propTypes = {
  theme: PropTypes.object.isRequired,
};

export default TitleDescription;
