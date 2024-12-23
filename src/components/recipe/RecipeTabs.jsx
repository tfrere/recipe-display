import React from "react";
import { Box, Tab, Tabs } from "@mui/material";

const RecipeTabs = ({ activeTab, onTabChange }) => {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
      <Tabs
        value={activeTab}
        onChange={onTabChange}
        aria-label="recipe visualization tabs"
      >
        <Tab label="Étapes" value="steps" />
        <Tab label="Timeline" value="timeline" />
        <Tab label="Graph" value="graph" />
      </Tabs>
    </Box>
  );
};

export default RecipeTabs;
