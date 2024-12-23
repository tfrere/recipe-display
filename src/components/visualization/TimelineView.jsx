import React, { useEffect, useRef } from "react";
import ReactDOM from "react-dom";
import { Box } from "@mui/material";
import * as d3 from "d3";
import ViewControls from "./ViewControls";
import { useRecipe } from "../../contexts/RecipeContext";

const TimelineView = () => {
  const { recipe, selectedSubRecipe } = useRecipe();
  const svgRef = useRef();
  const containerRef = useRef();

  useEffect(() => {
    if (!recipe || !selectedSubRecipe || !recipe.subRecipes[selectedSubRecipe])
      return;

    const subRecipe = recipe.subRecipes[selectedSubRecipe];
    const resizeObserver = new ResizeObserver(() => {
      renderTimeline(subRecipe);
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [recipe, selectedSubRecipe]);

  const renderTimeline = (subRecipe) => {
    // Get container dimensions
    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;

    // Set up dimensions
    const margin = { top: 60, right: 200, bottom: 40, left: 300 };
    const width = containerWidth;
    const height = containerHeight || 800;
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Calculate base width for 60 minutes
    const baseWidth = innerWidth;
    const minutesPerWidth = 60;
    const pixelsPerMinute = baseWidth / minutesPerWidth;

    // Clear existing SVG
    d3.select(svgRef.current).selectAll("*").remove();

    // Create SVG
    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    // Add zoom behavior
    const zoom = d3
      .zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        mainGroup.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Create main group for zoom/pan
    const mainGroup = svg.append("g");

    // Add ViewControls
    svg.append(() => {
      const controls = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "g"
      );
      ReactDOM.render(
        <ViewControls svgRef={svgRef} zoom={zoom} width={width} />,
        controls
      );
      return controls;
    });

    // Add legend (moved here, before the layers)
    const legendItems = [
      { label: "Cuisson", color: "#ffcdd2", stroke: "#ef5350" },
      { label: "Préparation", color: "#c8e6c9", stroke: "#66bb6a" },
      { label: "Autre", color: "#fff3e0", stroke: "#ffb74d" },
    ];

    const legend = svg
      .append("g")
      .attr("class", "legend")
      .attr("transform", `translate(20, 20)`);

    legend
      .selectAll(".legend-item")
      .data(legendItems)
      .join("g")
      .attr("class", "legend-item")
      .attr("transform", (d, i) => `translate(0, ${i * 25})`)
      .call((g) => {
        g.append("rect")
          .attr("width", 15)
          .attr("height", 15)
          .attr("rx", 2)
          .attr("fill", (d) => d.color)
          .attr("stroke", (d) => d.stroke);

        g.append("text")
          .attr("x", 25)
          .attr("y", 12)
          .attr("font-size", "12px")
          .text((d) => d.label);
      });

    // Create layers
    const backgroundGroup = mainGroup
      .append("g")
      .attr("class", "background-layer");
    const contentGroup = mainGroup.append("g").attr("class", "main-layer");
    const foregroundGroup = mainGroup
      .append("g")
      .attr("class", "foreground-layer");

    // Prepare timeline data
    const steps = subRecipe.steps;
    const timelineData = [];

    // Function to parse time string to minutes
    const parseTime = (timeStr) => {
      if (!timeStr) return 0;
      const match = timeStr.match(/(\d+)\s*min/);
      return match ? parseInt(match[1]) : 0;
    };

    // Function to get step by state reference
    const getStepByState = (stateRef) => {
      // If it's a reference to another sub-recipe
      if (stateRef.includes("/")) {
        const [subRecipeId, stateId] = stateRef.split("/");
        return recipe.subRecipes[subRecipeId]?.steps?.find(
          (s) => s.output.state === stateId
        );
      }
      // If it's a reference to current sub-recipe
      return subRecipe.steps.find((s) => s.output.state === stateRef);
    };

    // Calculate dependencies and earliest start times
    const dependencyMap = new Map();
    const reverseDependencyMap = new Map();
    subRecipe.steps.forEach((step) => {
      const dependencies = step.inputs
        .filter((input) => input.type === "state" || input.type === "subRecipe")
        .map((input) => {
          if (input.type === "subRecipe") {
            return input.ref; // Already in format "subRecipe/state"
          }
          return input.ref;
        });
      dependencyMap.set(step.id, dependencies);

      // Build reverse dependency map
      dependencies.forEach((depState) => {
        const sourceStep = getStepByState(depState);
        if (sourceStep) {
          if (!reverseDependencyMap.has(sourceStep.id)) {
            reverseDependencyMap.set(sourceStep.id, []);
          }
          reverseDependencyMap.get(sourceStep.id).push(step.id);
        }
      });
    });

    // Calculate earliest start times and parallel groups
    const startTimes = new Map();
    const parallelGroups = new Map();
    let currentGroup = 0;

    const calculateStartTime = (stepId) => {
      if (startTimes.has(stepId)) return startTimes.get(stepId);

      const step = subRecipe.steps.find((s) => s.id === stepId);
      const dependencies = dependencyMap.get(stepId) || [];

      if (dependencies.length === 0) {
        startTimes.set(stepId, 0);
        if (!parallelGroups.has(0)) parallelGroups.set(0, []);
        parallelGroups.get(0).push(stepId);
        return 0;
      }

      const maxDependencyEnd = Math.max(
        ...dependencies.map((depState) => {
          const depStep = getStepByState(depState);
          if (!depStep) return 0;
          const depStart = calculateStartTime(depStep.id);
          return depStart + parseTime(depStep.time || "0 min");
        })
      );

      startTimes.set(stepId, maxDependencyEnd);

      // Assign to parallel group
      const depGroups = dependencies.map((depState) => {
        const depStep = getStepByState(depState);
        if (!depStep) return 0;
        const group = Array.from(parallelGroups.entries()).find(([_, steps]) =>
          steps.includes(depStep.id)
        );
        return group ? group[0] : 0;
      });

      const maxDepGroup = Math.max(...depGroups);
      if (!parallelGroups.has(maxDepGroup + 1)) {
        parallelGroups.set(maxDepGroup + 1, []);
      }
      parallelGroups.get(maxDepGroup + 1).push(stepId);

      return maxDependencyEnd;
    };

    // Calculate all start times
    subRecipe.steps.forEach((step) => {
      const startTime = calculateStartTime(step.id);
      const stepType = step.temperature
        ? "cuisson"
        : (step.tools || []).some((t) => recipe.tools[t]?.type === "cuisson")
        ? "cuisson"
        : (step.tools || []).some(
            (t) => recipe.tools[t]?.type === "preparation"
          )
        ? "preparation"
        : "autre";

      timelineData.push({
        id: step.id,
        start: startTime,
        duration: parseTime(step.time),
        label: step.action,
        tools: step.tools || [],
        temperature: step.temperature,
        inputs: step.inputs,
        output: step.output,
        type: stepType,
        group: Array.from(parallelGroups.entries()).find(([_, steps]) =>
          steps.includes(step.id)
        )[0],
      });
    });

    // Calculate total duration
    const totalDuration = Math.max(
      ...timelineData.map((d) => d.start + d.duration)
    );

    // Create scales
    const xScale = d3
      .scaleLinear()
      .domain([0, totalDuration])
      .range([0, totalDuration * pixelsPerMinute]);

    const yScale = d3
      .scaleBand()
      .domain(timelineData.map((d) => d.id))
      .range([0, innerHeight])
      .padding(0.1);

    // Add background cells for each row
    backgroundGroup
      .append("g")
      .attr("class", "row-backgrounds")
      .selectAll("rect")
      .data(timelineData)
      .join("rect")
      .attr("x", 0)
      .attr("y", (d) => yScale(d.id))
      .attr("width", 20000)
      .attr("height", yScale.bandwidth())
      .attr("fill", "transparent")
      .attr("stroke", "#e0e0e0")
      .attr("stroke-width", 1);

    // Add grid lines in background
    backgroundGroup
      .append("g")
      .attr("class", "grid")
      .selectAll("line.vertical")
      .data(d3.range(0, totalDuration + 15, 15))
      .join("line")
      .attr("class", "vertical")
      .attr("x1", (d) => xScale(d))
      .attr("x2", (d) => xScale(d))
      .attr("y1", 0)
      .attr("y2", innerHeight)
      .attr("stroke", "#e0e0e0")
      .attr("stroke-width", 1);

    // Add axes
    const xAxis = d3
      .axisTop(xScale)
      .tickValues(d3.range(0, totalDuration + 15, 15)) // Ticks tous les 15 minutes
      .tickFormat((d) => {
        const minutes = d === 0 ? "" : "min";
        return `${d}${minutes}`;
      })
      .tickSize(-innerHeight);

    contentGroup
      .append("g")
      .attr("class", "x-axis")
      .call(xAxis)
      .call((g) => g.select(".domain").remove())
      .call((g) =>
        g
          .selectAll(".tick line")
          .attr("stroke", "#e0e0e0")
          .attr("stroke-width", 1)
      )
      .call((g) =>
        g
          .selectAll(".tick text")
          .attr("dy", -10)
          .attr("font-size", "14px")
          .attr("font-weight", 500)
          .style("opacity", 0.5)
      );

    // Supprimer l'axe Y
    // const yAxis = d3.axisLeft(yScale);
    // contentGroup
    //   .append("g")
    //   .attr("class", "y-axis")
    //   .call(yAxis)
    //   .call((g) => g.select(".domain").remove());

    // Add background for parallel groups
    // const groupColors = ["#f3e5f5", "#e8f5e9", "#e3f2fd", "#fff3e0", "#fce4ec"];
    // backgroundGroup
    //   .selectAll(".group-background")
    //   .data(Array.from(parallelGroups.entries()))
    //   .join("rect")
    //   .attr("class", "group-background")
    //   .attr("x", -10)
    //   .attr("y", (d) => Math.min(...d[1].map((id) => yScale(id))) - 5)
    //   .attr("width", innerWidth + 20)
    //   .attr("height", (d) => {
    //     const yValues = d[1].map((id) => yScale(id));
    //     return (
    //       Math.max(...yValues) - Math.min(...yValues) + yScale.bandwidth() + 10
    //     );
    //   })
    //   .attr("fill", (d, i) => groupColors[i % groupColors.length])
    //   .attr("opacity", 0.3);

    // Add dependency lines with improved styling
    const lineGenerator = d3.line().curve(d3.curveBasis);

    contentGroup
      .append("g")
      .attr("class", "dependency-lines")
      .selectAll("path")
      .data(
        timelineData.flatMap((step) => {
          const nextSteps = reverseDependencyMap.get(step.id) || [];
          return nextSteps.map((nextStepId) => ({
            source: step,
            target: timelineData.find((d) => d.id === nextStepId),
          }));
        })
      )
      .join("path")
      .attr("d", (d) => {
        const startX = xScale(d.source.start + d.source.duration);
        const startY = yScale(d.source.id) + yScale.bandwidth() / 2;
        const endX = xScale(d.target.start);
        const endY = yScale(d.target.id) + yScale.bandwidth() / 2;

        const controlPoint1X = startX + (endX - startX) / 3;
        const controlPoint2X = startX + (2 * (endX - startX)) / 3;

        return lineGenerator([
          [startX, startY],
          [controlPoint1X, startY],
          [controlPoint2X, endY],
          [endX, endY],
        ]);
      })
      .attr("fill", "none")
      .attr("stroke", "#e0e0e0")
      .attr("stroke-width", 3);

    // Add timeline bars with padding
    const cellPadding = 10;
    const bars = contentGroup
      .append("g")
      .attr("class", "timeline-bars")
      .selectAll(".timeline-bar")
      .data(timelineData)
      .join("g")
      .attr("class", "timeline-bar")
      .attr(
        "transform",
        (d) => `translate(${xScale(d.start)},${yScale(d.id)})`
      );

    // Add rectangles for steps with padding
    bars
      .append("rect")
      .attr("height", yScale.bandwidth() - 4)
      .attr("y", 2)
      .attr("x", cellPadding)
      .attr("width", (d) =>
        Math.max(0, xScale(d.duration) - xScale(0) - cellPadding * 2)
      )
      .attr("fill", (d) => {
        switch (d.type) {
          case "cuisson":
            return "#ffcdd2";
          case "preparation":
            return "#c8e6c9";
          default:
            return "#fff3e0";
        }
      })
      .attr("stroke", (d) => {
        switch (d.type) {
          case "cuisson":
            return "#ef5350";
          case "preparation":
            return "#66bb6a";
          default:
            return "#ffb74d";
        }
      })
      .attr("rx", 6)
      .style("cursor", "pointer")
      .on("mouseover", function (event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("filter", "brightness(0.95)");

        // Show tooltip
        const tooltip = d3.select("#tooltip");
        tooltip
          .style("visibility", "visible")
          .style("left", event.clientX + 15 + "px")
          .style("top", event.clientY - 15 + "px").html(`
            <strong>${d.label}</strong><br/>
            Durée: ${d.duration} min<br/>
            ${d.temperature ? `Température: ${d.temperature}<br/>` : ""}
            Ustensiles: ${d.tools
              .map((t) => recipe.tools[t].name)
              .join(", ")}<br/>
            <br/>
            <strong>Ingrédients:</strong><br/>
            ${d.inputs
              .filter((input) => input.type === "ingredient")
              .map((input) => {
                const ingredient = recipe.ingredients[input.ref];
                const amount = subRecipe.ingredients[input.ref].amount;
                return `- ${ingredient.name}: ${amount}${ingredient.unit}`;
              })
              .join("<br/>")}
            <br/>
            <strong>Résultat:</strong><br/>
            ${d.output.description}
          `);
      })
      .on("mouseout", function (event, d) {
        d3.select(this).transition().duration(200).attr("filter", null);
        d3.select("#tooltip").style("visibility", "hidden");
      });

    // Add step labels with padding
    bars
      .append("text")
      .attr("x", (d) => xScale(d.duration) + 5)
      .attr("y", yScale.bandwidth() / 2)
      .attr("dy", "0.35em")
      .attr("font-size", "14px")
      .attr("fill", "#424242")
      .attr("font-weight", 700)
      .text((d) => d.label)
      .call(wrap, 250);

    // Add duration labels with padding
    bars
      .append("text")
      .attr("x", (d) => xScale(d.duration) - cellPadding)
      .attr("y", yScale.bandwidth() / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", "end")
      .attr("font-size", "12px")
      .attr("fill", "#757575")
      .attr("font-weight", 500)
      .text((d) => (d.duration > 0 ? `${d.duration}min` : ""));
  };

  // Helper function to wrap text
  function wrap(text, width) {
    text.each(function () {
      const text = d3.select(this);
      const words = text.text().split(/\s+/).reverse();
      const lineHeight = 1.1;
      const y = text.attr("y");
      const dy = parseFloat(text.attr("dy"));

      // Effacer le contenu existant
      text.text(null);

      // Créer les lignes
      let lines = [];
      let line = [];
      let word;

      // Calculer les lignes
      while ((word = words.pop())) {
        line.push(word);
        const testLine = line.join(" ");
        const testElem = text.append("tspan").text(testLine);

        if (
          testElem.node().getComputedTextLength() > width &&
          line.length > 1
        ) {
          line.pop();
          lines.push(line.join(" "));
          line = [word];
        }

        testElem.remove();
      }
      lines.push(line.join(" "));

      // Calculer le décalage vertical pour centrer toutes les lignes
      const totalHeight = lines.length * lineHeight;
      const startY = y - (totalHeight * 12) / 2 + 12; // 12 est approximativement la hauteur d'une ligne en pixels

      // Ajouter les lignes avec le bon positionnement
      lines.forEach((lineText, i) => {
        text
          .append("tspan")
          .attr("x", text.attr("x"))
          .attr("y", startY)
          .attr("dy", `${i * lineHeight}em`)
          .text(lineText);
      });
    });
  }

  return (
    <Box sx={{ width: "100%", height: "100%", position: "relative" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }}>
        <svg ref={svgRef}></svg>
      </div>
    </Box>
  );
};

export default TimelineView;
