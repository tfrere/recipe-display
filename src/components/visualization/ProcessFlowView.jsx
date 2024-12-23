import React from "react";
import { Box } from "@mui/material";
import GraphView from "./GraphView";

const ProcessFlowView = () => {
  return (
    <Box sx={{ width: "100%", height: "100%", overflow: "hidden" }}>
      <GraphView />
    </Box>
  );
};

export default ProcessFlowView;
