import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import PropTypes from "prop-types";

const Legend = ({ categories, categoryColors, theme }) => {
  const legendRef = useRef(null);

  useEffect(() => {
    if (!legendRef.current) return;

    // Nettoyer le SVG avant de dessiner
    d3.select(legendRef.current).selectAll("*").remove();

    // Dimensions et padding constants
    const padding = 24;
    const width = 220;
    const itemHeight = 24;
    const textOffset = 28;
    const sectionSpacing = 24;
    const headerSpacing = 12;

    // Calculer la hauteur totale
    const categorySection =
      categories.length > 0
        ? headerSpacing + categories.length * itemHeight
        : 0;
    const totalHeight = padding * 2 + 24 + categorySection + headerSpacing;

    // Création de la légende séparée qui restera fixe
    const legendSvg = d3
      .select(legendRef.current)
      .attr("width", width)
      .attr("height", totalHeight);

    // Groupe de légende
    const legendGroup = legendSvg
      .append("g")
      .attr("transform", `translate(0, 0)`);

    // Fond semi-transparent de la légende
    legendGroup
      .append("rect")
      .attr("width", width)
      .attr("height", totalHeight)
      .attr("fill", "#f5f5f5")
      .attr("opacity", 0.85)
      .attr("rx", 8);

    let currentY = padding + 10 + headerSpacing;

    // Sous-titre des catégories et éléments
    if (categories.length > 0) {
      // Sous-titre des catégories
      legendGroup
        .append("text")
        .attr("x", padding - 10)
        .attr("y", currentY - 15)
        .text("Main Categories")
        .style("font-weight", "500")
        .style("font-size", "14px")
        .style("fill", theme.palette.text.primary);

      currentY += headerSpacing;

      // Éléments de la légende pour les catégories
      categories.forEach((category, i) => {
        const elementY = currentY + i * itemHeight;

        // Cercle de catégorie
        legendGroup
          .append("circle")
          .attr("cx", padding)
          .attr("cy", elementY)
          .attr("r", 6)
          .attr("fill", categoryColors(category));

        // Texte de catégorie
        legendGroup
          .append("text")
          .attr("x", padding + textOffset)
          .attr("y", elementY + 4)
          .text(category)
          .style("font-size", "13px")
          .style("font-weight", "300")
          .style("fill", theme.palette.text.secondary);
      });

      currentY += categories.length * itemHeight + 8;

      // Autres catégories (sans couleur spécifique)
      legendGroup
        .append("circle")
        .attr("cx", padding)
        .attr("cy", currentY)
        .attr("r", 6)
        .attr("fill", theme.palette.grey[300]);

      legendGroup
        .append("text")
        .attr("x", padding + textOffset)
        .attr("y", currentY + 4)
        .text("Uncategorized")
        .style("font-size", "13px")
        .style("font-weight", "300")
        .style("fill", theme.palette.text.secondary);

      currentY += itemHeight + sectionSpacing;
    } else {
      currentY += headerSpacing;
    }
  }, [categories, categoryColors, theme]);

  return (
    <svg
      ref={legendRef}
      style={{
        position: "absolute",
        top: 20,
        right: 20,
        pointerEvents: "none",
        maxHeight: "calc(100% - 40px)",
      }}
    />
  );
};

Legend.propTypes = {
  categories: PropTypes.array.isRequired,
  categoryColors: PropTypes.func.isRequired,
  theme: PropTypes.object.isRequired,
};

export default Legend;
