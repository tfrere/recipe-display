import React, { useEffect, useRef } from "react";
import { Box, Paper, Typography } from "@mui/material";
import * as d3 from "d3";
import recipeData from "../data/recipeFlow.json";

const RecipeFlow = ({ selectedComponent }) => {
  const svgRef = useRef();
  const gRef = useRef();

  useEffect(() => {
    if (!selectedComponent || !recipeData.components[selectedComponent]) return;

    const component = recipeData.components[selectedComponent];
    const nodes = Object.entries(component.nodes).map(([id, node]) => ({
      id,
      ...node,
    }));

    const edges = component.edges.flatMap((edge) => {
      const sources = Array.isArray(edge.from) ? edge.from : [edge.from];
      const targets = Array.isArray(edge.to) ? edge.to : [edge.to];

      return sources.flatMap((source) =>
        targets.map((target) => ({
          source,
          target,
          action: edge.action,
          tools: edge.tools,
          time: edge.time,
          temperature: edge.temperature,
        }))
      );
    });

    // Clear existing SVG
    d3.select(svgRef.current).selectAll("*").remove();

    // Set up dimensions
    const width = 800;
    const height = 600;

    // Create SVG with zoom support
    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Add zoom behavior
    const zoom = d3
      .zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Create main group for zoom/pan
    const g = svg.append("g");
    gRef.current = g;

    // Create arrow marker
    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "-0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .append("path")
      .attr("d", "M 0,-5 L 10,0 L 0,5")
      .attr("fill", "#999");

    // Create force simulation
    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(edges)
          .id((d) => d.id)
          .distance(150)
      )
      .force("charge", d3.forceManyBody().strength(-1000))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(70));

    // Add links
    const links = g
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#999")
      .attr("stroke-width", 1)
      .attr("marker-end", "url(#arrowhead)");

    // Create node groups
    const nodeGroups = g
      .append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(
        d3
          .drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended)
      );

    // Add node circles with hover effect
    nodeGroups
      .append("circle")
      .attr("r", 30)
      .attr("fill", (d) => {
        switch (d.type) {
          case "ingredient":
            return "#e3f2fd";
          case "state":
            return "#f3e5f5";
          default:
            return "#fff3e0";
        }
      })
      .attr("stroke", "#666")
      .attr("stroke-width", 2)
      .style("cursor", "grab")
      .on("mouseover", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 35)
          .attr("stroke-width", 3);
      })
      .on("mouseout", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 30)
          .attr("stroke-width", 2);
      });

    // Add node labels
    nodeGroups
      .append("text")
      .text((d) => d.label)
      .attr("text-anchor", "middle")
      .attr("dy", ".35em")
      .attr("font-size", "10px")
      .style("pointer-events", "none")
      .call(wrap, 60);

    // Add action labels with background
    const edgeLabels = g
      .append("g")
      .attr("class", "edge-labels")
      .selectAll("g")
      .data(edges)
      .join("g");

    // Add white background for edge labels
    edgeLabels.append("rect").attr("fill", "white").attr("opacity", 0.8);

    // Add edge text
    const edgeTexts = edgeLabels
      .append("text")
      .attr("font-size", "8px")
      .attr("text-anchor", "middle")
      .text(
        (d) =>
          `${d.action}${d.time ? ` (${d.time})` : ""}${
            d.temperature ? ` - ${d.temperature}` : ""
          }`
      );

    // Size the background rectangles
    edgeLabels.selectAll("rect").each(function (d) {
      const text = d3.select(this.parentNode).select("text");
      const bbox = text.node().getBBox();
      d3.select(this)
        .attr("x", bbox.x - 2)
        .attr("y", bbox.y - 2)
        .attr("width", bbox.width + 4)
        .attr("height", bbox.height + 4);
    });

    // Drag functions
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
      d3.select(this).select("circle").style("cursor", "grabbing");
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
      d3.select(this).select("circle").style("cursor", "grab");
    }

    // Update positions on simulation tick
    simulation.on("tick", () => {
      links
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      nodeGroups.attr("transform", (d) => `translate(${d.x},${d.y})`);

      edgeLabels.attr("transform", (d) => {
        const midX = (d.source.x + d.target.x) / 2;
        const midY = (d.source.y + d.target.y) / 2 - 10;
        return `translate(${midX},${midY})`;
      });
    });

    // Helper function to wrap text
    function wrap(text, width) {
      text.each(function () {
        const text = d3.select(this);
        const words = text.text().split(/\\s+/);
        const lineHeight = 1.1;
        const y = text.attr("y");
        const dy = parseFloat(text.attr("dy"));
        let tspan = text
          .text(null)
          .append("tspan")
          .attr("x", 0)
          .attr("y", y)
          .attr("dy", dy + "em");

        let line = [];
        let lineNumber = 0;
        let word;
        while ((word = words.pop())) {
          line.push(word);
          tspan.text(line.join(" "));
          if (tspan.node().getComputedTextLength() > width) {
            line.pop();
            tspan.text(line.join(" "));
            line = [word];
            tspan = text
              .append("tspan")
              .attr("x", 0)
              .attr("y", y)
              .attr("dy", ++lineNumber * lineHeight + dy + "em")
              .text(word);
          }
        }
      });
    }

    // Add zoom controls
    const zoomControls = svg
      .append("g")
      .attr("class", "zoom-controls")
      .attr("transform", "translate(20, 20)");

    // Zoom in button
    zoomControls
      .append("rect")
      .attr("x", 0)
      .attr("y", 0)
      .attr("width", 30)
      .attr("height", 30)
      .attr("fill", "#fff")
      .attr("stroke", "#999")
      .attr("rx", 5)
      .style("cursor", "pointer")
      .on("click", () => {
        svg.transition().duration(300).call(zoom.scaleBy, 1.3);
      });

    zoomControls
      .append("text")
      .attr("x", 15)
      .attr("y", 20)
      .attr("text-anchor", "middle")
      .text("+")
      .style("pointer-events", "none");

    // Zoom out button
    zoomControls
      .append("rect")
      .attr("x", 0)
      .attr("y", 40)
      .attr("width", 30)
      .attr("height", 30)
      .attr("fill", "#fff")
      .attr("stroke", "#999")
      .attr("rx", 5)
      .style("cursor", "pointer")
      .on("click", () => {
        svg.transition().duration(300).call(zoom.scaleBy, 0.7);
      });

    zoomControls
      .append("text")
      .attr("x", 15)
      .attr("y", 60)
      .attr("text-anchor", "middle")
      .text("-")
      .style("pointer-events", "none");

    // Reset zoom button
    zoomControls
      .append("rect")
      .attr("x", 0)
      .attr("y", 80)
      .attr("width", 30)
      .attr("height", 30)
      .attr("fill", "#fff")
      .attr("stroke", "#999")
      .attr("rx", 5)
      .style("cursor", "pointer")
      .on("click", () => {
        svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
      });

    zoomControls
      .append("text")
      .attr("x", 15)
      .attr("y", 100)
      .attr("text-anchor", "middle")
      .attr("font-size", "10px")
      .text("R")
      .style("pointer-events", "none");
  }, [selectedComponent]);

  if (!selectedComponent || !recipeData.components[selectedComponent]) {
    return null;
  }

  return (
    <Paper elevation={3} sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Flux de préparation : {recipeData.components[selectedComponent].title}
      </Typography>
      <Box sx={{ overflowX: "auto" }}>
        <svg ref={svgRef}></svg>
      </Box>
    </Paper>
  );
};

export default RecipeFlow;
