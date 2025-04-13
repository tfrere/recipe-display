import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useTheme } from "@mui/material";
import * as d3 from "d3";
import Legend from "./Legend";
import TitleDescription from "./TitleDescription";

// Catégories principales à colorer distinctement
const MAIN_CATEGORIES = [
  "Dairy",
  "Fruit",

  "Plant/Vegetable",
  "Meat/Animal Product",
  "Cereal/Crop/Bean",
  "Nut/Seed",
  "Seafood",
  "Spice",
  "Fungus",
];

// Positions des étiquettes des catégories principales dans le graphique
// Ces positions peuvent être facilement ajustées selon les besoins
const CATEGORY_LABELS = [
  { category: "Plant/Vegetable", x: 0.7, y: 0.5 },
  { category: "Cereal/Crop/Bean", x: 0.5, y: 0.5 },
  { category: "Seafood", x: 0.5, y: 0.7 },
  { category: "Fruit", x: 0.4, y: 0.75 },
  { category: "Dairy", x: 0.5, y: 0.09 },
  { category: "Nut/Seed", x: 0.4, y: 0.6 },
  { category: "Meat/Animal Product", x: 0.6, y: 0.6 },
];

const IngredientGraph = ({ data, navHeight = 0 }) => {
  const svgRef = useRef(null);
  const tooltipRef = useRef(null);
  const theme = useTheme();
  const [categories, setCategories] = useState([]);
  const [categoryColors, setCategoryColors] = useState(() =>
    d3.scaleOrdinal().range(d3.schemeCategory10)
  );

  useEffect(() => {
    if (!data.length || !svgRef.current) return;

    // Nettoyer le SVG avant de dessiner
    d3.select(svgRef.current).selectAll("*").remove();

    // Dimensions
    const width = window.innerWidth;
    const height = window.innerHeight - navHeight; // Soustraire la hauteur de la barre de navigation
    const margin = { top: 50, right: 50, bottom: 50, left: 50 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Créer le SVG principal pour la visualisation
    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    // Groupe pour les éléments qui seront zoomables
    const zoomableGroup = svg.append("g").attr("class", "zoomable-group");

    // Créer le tooltip
    const tooltip = d3
      .select(tooltipRef.current)
      .style("opacity", 0)
      .style("position", "absolute")
      .style("padding", "10px")
      .style("background", theme.palette.background.paper)
      .style("border-radius", "5px")
      .style("box-shadow", "0 3px 14px rgba(0,0,0,0.2)")
      .style("pointer-events", "none")
      .style("font-size", "12px")
      .style("z-index", 1000);

    // Échelles
    const xExtent = d3.extent(data, (d) => d.coordinates.x);
    const yExtent = d3.extent(data, (d) => d.coordinates.y);

    // Ajouter une marge aux échelles
    const xPadding = (xExtent[1] - xExtent[0]) * 0.05;
    const yPadding = (yExtent[1] - yExtent[0]) * 0.05;

    const xScale = d3
      .scaleLinear()
      .domain([xExtent[0] - xPadding, xExtent[1] + xPadding])
      .range([0, innerWidth]);

    const yScale = d3
      .scaleLinear()
      .domain([yExtent[0] - yPadding, yExtent[1] + yPadding])
      .range([innerHeight, 0]);

    // Récupérer uniquement les catégories principales qui existent dans les données
    const existingMainCategories = MAIN_CATEGORIES.filter((category) =>
      data.some((d) => d.category === category)
    );

    setCategories(existingMainCategories);

    // Fonction pour déterminer la couleur en fonction de la catégorie
    const colorScale = d3
      .scaleOrdinal()
      .domain(existingMainCategories)
      .range(d3.schemeCategory10.slice(0, existingMainCategories.length));

    // Fonction de couleur qui retourne une couleur spécifique uniquement pour les catégories principales
    const getColor = (d) => {
      if (d.category && existingMainCategories.includes(d.category)) {
        return colorScale(d.category);
      }
      // Pour les autres catégories ou si pas de catégorie, utiliser un gris léger
      return theme.palette.grey[400];
    };

    setCategoryColors(
      () => (category) =>
        existingMainCategories.includes(category)
          ? colorScale(category)
          : theme.palette.grey[300]
    );

    // Ajouter des cercles pour les ingrédients non populaires d'abord
    zoomableGroup
      .selectAll(".non-hub-ingredient")
      .data(data.filter((d) => !d.is_hub))
      .enter()
      .append("circle")
      .attr("class", "non-hub-ingredient")
      .attr("cx", (d) => xScale(d.coordinates.x))
      .attr("cy", (d) => yScale(d.coordinates.y))
      .attr("r", 1.5)
      .attr("fill", getColor)
      .attr("opacity", 0.6)
      .attr("stroke", "none")
      .attr("stroke-width", 0)
      .on("mouseover", function (event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 4)
          .attr("opacity", 1);

        tooltip.transition().duration(200).style("opacity", 0.9);

        tooltip
          .html(
            `
          <strong>${d.name}</strong>
          ${d.category ? `<br/>Category: ${d.category}` : ""}
        `
          )
          .style("left", `${event.pageX + 15}px`)
          .style("top", `${event.pageY - 30}px`);
      })
      .on("mouseout", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 1.5)
          .attr("opacity", 0.6);

        tooltip.transition().duration(500).style("opacity", 0);
      });

    // Ensuite, ajouter des cercles pour les ingrédients populaires (qui seront au-dessus)
    zoomableGroup
      .selectAll(".hub-ingredient")
      .data(data.filter((d) => d.is_hub))
      .enter()
      .append("circle")
      .attr("class", "hub-ingredient")
      .attr("cx", (d) => xScale(d.coordinates.x))
      .attr("cy", (d) => yScale(d.coordinates.y))
      .attr("r", (d) => {
        // Si l'ingrédient est populaire mais non catégorisé (ou dans une catégorie non principale),
        // lui donner une taille plus petite
        if (!d.category || !existingMainCategories.includes(d.category)) {
          return 1;
        }
        // Sinon garder la taille originale pour les ingrédients populaires catégorisés
        return 8;
      })
      .attr("fill", getColor)
      .attr("opacity", 0.8)
      .attr("stroke", (d) => {
        // Bordure pour les ingrédients populaires, plus subtile
        const fillColor = getColor(d);
        // Si c'est déjà un gris, utiliser un gris plus foncé
        if (fillColor === theme.palette.grey[300]) {
          return theme.palette.grey[500];
        }
        // Sinon, générer une version plus foncée de la couleur
        return d3.color(fillColor).darker(0.5);
      })
      .attr("stroke-width", 1)
      .on("mouseover", function (event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", (d) => {
            // Même logique pour le hover
            if (!d.category || !existingMainCategories.includes(d.category)) {
              return 5;
            }
            return 12;
          })
          .attr("opacity", 1);

        tooltip.transition().duration(200).style("opacity", 0.9);

        tooltip
          .html(
            `
          <strong>${d.name}</strong>
          ${d.category ? `<br/>Category: ${d.category}` : ""}
          <br/><em>Popular ingredient</em>
        `
          )
          .style("left", `${event.pageX + 15}px`)
          .style("top", `${event.pageY - 30}px`);
      })
      .on("mouseout", function (d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", (d) => {
            // Rétablir la taille d'origine sur mouseout
            if (!d.category || !existingMainCategories.includes(d.category)) {
              return 3;
            }
            return 10;
          })
          .attr("opacity", 0.8);

        tooltip.transition().duration(500).style("opacity", 0);
      });

    // Fonction de zoom qui n'affecte que le groupe zoomable
    const zoom = d3
      .zoom()
      .scaleExtent([1, 10])
      .on("zoom", (event) => {
        zoomableGroup.attr("transform", event.transform);
      });

    // Initialiser la transformation de zoom à la même position que notre translation initiale
    // pour éviter le décalage lors du premier pan
    const initialTransform = d3.zoomIdentity
      .translate(margin.left, margin.top)
      .scale(1);

    // Appliquer la transformation initiale
    svg.call(zoom.transform, initialTransform);

    // Ajouter les étiquettes des catégories principales
    CATEGORY_LABELS.forEach((label) => {
      // Conversion des coordonnées relatives en coordonnées absolues
      const labelX =
        xScale.domain()[0] +
        (xScale.domain()[1] - xScale.domain()[0]) * label.x;
      const labelY =
        yScale.domain()[0] +
        (yScale.domain()[1] - yScale.domain()[0]) * label.y;

      // Vérifier si la catégorie est dans les catégories existantes
      if (existingMainCategories.includes(label.category)) {
        const labelColor = colorScale(label.category);

        // Ajout du texte avec bordure
        zoomableGroup
          .append("text")
          .attr("x", xScale(labelX))
          .attr("y", yScale(labelY))
          .text(label.category)
          .attr("font-size", "24px")
          .attr("font-weight", "bold")
          .attr("text-anchor", "middle")
          .attr("fill", labelColor)
          .attr("stroke", d3.color(labelColor).darker(0.5))
          .attr("stroke-width", "0.5px")
          .attr("stroke", "rgba(255,255,255,1)")
          .attr("stroke-width", "7.5px")
          .attr("paint-order", "stroke")
          .attr("stroke-linejoin", "round");
      }
    });

    // Ajouter la fonctionnalité de zoom
    svg.call(zoom);
  }, [data, theme, navHeight]);

  return (
    <>
      <svg ref={svgRef} width="100%" height="100%" />
      {categoryColors && (
        <Legend
          categories={categories}
          categoryColors={categoryColors}
          theme={theme}
        />
      )}
      <TitleDescription theme={theme} />
      <div ref={tooltipRef} />
    </>
  );
};

IngredientGraph.propTypes = {
  data: PropTypes.array.isRequired,
  navHeight: PropTypes.number,
};

export default IngredientGraph;
