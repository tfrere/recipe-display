// Text constants for UI elements
export const INGREDIENTS_TEXTS = {
  TITLE: "Ingredients",
  COPY_SUCCESS: "Ingredients copied to clipboard!",
  SHOPPING_MODE: "Shopping list",
  COPY_BUTTON: "Copy list",
};

// Custom styling for the switch component
export const switchStyle = {
  "& .MuiSwitch-track": {
    bgcolor: "background.paper",
    border: "1px solid",
    borderColor: "divider",
    opacity: "1 !important",
  },
  "& .MuiSwitch-thumb": {
    bgcolor: "background.paper",
    border: "1px solid",
    borderColor: "text.secondary",
  },
  "&.Mui-checked": {
    "& .MuiSwitch-thumb": {
      bgcolor: "background.paper",
      borderColor: "text.primary",
    },
    "& + .MuiSwitch-track": {
      bgcolor: "background.paper !important",
      borderColor: "text.primary",
      opacity: "1 !important",
    },
  },
};
