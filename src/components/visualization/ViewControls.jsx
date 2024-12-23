import React from "react";
import * as d3 from "d3";

const ViewControls = ({ svgRef, zoom, width }) => {
  const handleZoomIn = () => {
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoom.scaleBy, 1.3);
  };

  const handleZoomOut = () => {
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoom.scaleBy, 0.7);
  };

  const handleReset = () => {
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoom.transform, d3.zoomIdentity);
  };

  // Calculer la position à droite (width - 40)
  const rightPosition = width - 40;

  return (
    <g className="view-controls" transform={`translate(${rightPosition}, 20)`}>
      <g onClick={handleZoomIn} style={{ cursor: "pointer" }}>
        <rect
          x="0"
          y="0"
          width="20"
          height="20"
          fill="#ffffff"
          fillOpacity="0.6"
          stroke="#9e9e9e"
          strokeWidth="0.5"
          rx="4"
        />
        <text
          x="10"
          y="14"
          textAnchor="middle"
          fontSize="12px"
          fill="#666666"
          style={{ pointerEvents: "none", userSelect: "none" }}
        >
          +
        </text>
      </g>

      <g onClick={handleZoomOut} style={{ cursor: "pointer" }}>
        <rect
          x="0"
          y="24"
          width="20"
          height="20"
          fill="#ffffff"
          fillOpacity="0.6"
          stroke="#9e9e9e"
          strokeWidth="0.5"
          rx="4"
        />
        <text
          x="10"
          y="38"
          textAnchor="middle"
          fontSize="12px"
          fill="#666666"
          style={{ pointerEvents: "none", userSelect: "none" }}
        >
          −
        </text>
      </g>

      <g onClick={handleReset} style={{ cursor: "pointer" }}>
        <rect
          x="0"
          y="48"
          width="20"
          height="20"
          fill="#ffffff"
          fillOpacity="0.6"
          stroke="#9e9e9e"
          strokeWidth="0.5"
          rx="4"
        />
        <text
          x="10"
          y="62"
          textAnchor="middle"
          fontSize="9px"
          fill="#666666"
          style={{ pointerEvents: "none", userSelect: "none" }}
        >
          R
        </text>
      </g>
    </g>
  );
};

export default ViewControls;
