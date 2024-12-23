import React, { useState } from "react";
import { Box } from "@mui/material";
import TimelineView from "./visualization/TimelineView";
import GraphView from "./visualization/GraphView";
import StepByStepView from "./visualization/StepByStepView";
import RecipeTabs from "./recipe/RecipeTabs";
import SubRecipeHeader from "./recipe/SubRecipeHeader";

const RecipeDetails = () => {
  const [activeTab, setActiveTab] = useState("steps");

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const renderContent = () => {
    switch (activeTab) {
      case "steps":
        return <StepByStepView />;
      case "timeline":
        return <TimelineView />;
      case "graph":
        return <GraphView />;
      default:
        return null;
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      <SubRecipeHeader />
      <RecipeTabs activeTab={activeTab} onTabChange={handleTabChange} />
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          bgcolor: "grey.50",
        }}
      >
        {renderContent()}
      </Box>
    </Box>
  );
};

export default RecipeDetails;
