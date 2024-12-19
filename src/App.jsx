import React, { useEffect, useRef } from "react";
import { Box, Container, Typography } from "@mui/material";
import * as d3 from "d3";

const App = () => {
  const svgRef = useRef();

  useEffect(() => {
    // Sample data
    const data = [
      { x: 0, y: 10 },
      { x: 1, y: 15 },
      { x: 2, y: 35 },
      { x: 3, y: 25 },
      { x: 4, y: 45 },
    ];

    // Set up dimensions
    const width = 600;
    const height = 400;
    const margin = { top: 20, right: 20, bottom: 30, left: 40 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Clear any existing SVG
    d3.select(svgRef.current).selectAll("*").remove();

    // Create SVG
    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    // Create scales
    const xScale = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.x)])
      .range([margin.left, innerWidth]);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.y)])
      .range([innerHeight, margin.top]);

    // Create line generator
    const line = d3
      .line()
      .x((d) => xScale(d.x))
      .y((d) => yScale(d.y))
      .curve(d3.curveMonotoneX);

    // Add line path
    svg
      .append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", "#2196f3")
      .attr("stroke-width", 2)
      .attr("d", line);

    // Add dots
    svg
      .selectAll("circle")
      .data(data)
      .enter()
      .append("circle")
      .attr("cx", (d) => xScale(d.x))
      .attr("cy", (d) => yScale(d.y))
      .attr("r", 5)
      .attr("fill", "#2196f3");

    // Add axes
    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale);

    svg
      .append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(xAxis);

    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(yAxis);
  }, []);

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Visualisation de données
      </Typography>
      <Box
        sx={{
          bgcolor: "background.paper",
          borderRadius: 1,
          p: 2,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <svg ref={svgRef}></svg>
      </Box>
    </Container>
  );
};

export default App;
