import React from "react";
import { Chip } from "@mui/material";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import RestaurantOutlinedIcon from "@mui/icons-material/RestaurantOutlined";
import ConstructionOutlinedIcon from "@mui/icons-material/ConstructionOutlined";
import GrassIcon from '@mui/icons-material/Grass';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';

// Types de chips possibles
export const CHIP_TYPES = {
  INGREDIENT: "ingredient",
  TOOL: "tool",
  STATE: "state",
  UNUSED: "unused",
  ACTION_COOKING: "action_cooking",
  ACTION_PREPARATION: "action_preparation",
  ACTION_ASSEMBLY: "action_assembly",
  DIET: "diet",
  SEASON: "season",
  RECIPE_TYPE: "recipe_type",
  NUTRITION: "nutrition",
};

// Configuration des couleurs par type
const CHIP_COLORS = {
  [CHIP_TYPES.INGREDIENT]: {
    color: "primary",
    baseColor: "#90caf9",
    bgColor: "rgba(144, 202, 249, 0.08)",
  },
  [CHIP_TYPES.TOOL]: {
    color: "warning",
    baseColor: "#ffb74d",
    bgColor: "rgba(255, 183, 77, 0.08)",
  },
  [CHIP_TYPES.STATE]: {
    color: "secondary",
    baseColor: "#ce93d8",
    bgColor: "rgba(206, 147, 216, 0.08)",
  },
  [CHIP_TYPES.UNUSED]: {
    color: "default",
    baseColor: "#bdbdbd",
    bgColor: "rgba(189, 189, 189, 0.08)",
  },
  [CHIP_TYPES.ACTION_COOKING]: {
    color: "error",
    baseColor: "#ef5350",
    bgColor: "rgba(239, 83, 80, 0.08)",
    icon: LocalFireDepartmentOutlinedIcon,
  },
  [CHIP_TYPES.ACTION_PREPARATION]: {
    color: "success",
    baseColor: "#66bb6a",
    bgColor: "rgba(102, 187, 106, 0.08)",
    icon: RestaurantOutlinedIcon,
  },
  [CHIP_TYPES.ACTION_ASSEMBLY]: {
    color: "info",
    baseColor: "#4fc3f7",
    bgColor: "rgba(79, 195, 247, 0.08)",
    icon: ConstructionOutlinedIcon,
  },
  [CHIP_TYPES.DIET]: {
    color: "success",
    baseColor: "#81c784",
    bgColor: "rgba(129, 199, 132, 0.08)",
    icon: GrassIcon,
  },
  [CHIP_TYPES.SEASON]: {
    color: "warning",
    baseColor: "#ffd54f",
    bgColor: "rgba(255, 213, 79, 0.08)",
    icon: WbSunnyIcon,
  },
  [CHIP_TYPES.RECIPE_TYPE]: {
    color: "secondary",
    baseColor: "#ba68c8",
    bgColor: "rgba(186, 104, 200, 0.08)",
    icon: RestaurantMenuIcon,
  },
  [CHIP_TYPES.NUTRITION]: {
    color: "info",
    baseColor: "#4fc3f7",
    bgColor: "rgba(79, 195, 247, 0.08)",
    icon: ScienceOutlinedIcon,
  },
};

const RecipeChip = ({
  label,
  type = CHIP_TYPES.STATE,
  isUnused = false,
  size = "medium",
  ...props
}) => {
  const chipType = isUnused ? CHIP_TYPES.UNUSED : type;
  const colorConfig = CHIP_COLORS[chipType];
  const Icon = colorConfig.icon;

  return (
    <Chip
      label={label}
      size={size}
      variant="outlined"
      color={colorConfig.color}
      icon={Icon ? <Icon sx={{ fontSize: "1rem" }} /> : undefined}
      sx={{
        // height: "24px",
        opacity: isUnused ? 0.6 : 1,
        // "& .MuiChip-label": {
        //   px: 3,
        //   py: 1,
        //   fontSize: "0.75rem",
        //   lineHeight: 1.2,
        //   fontWeight: 400,
        // },
        // "& .MuiChip-icon": {
        //   fontSize: "1rem",
        //   ml: 1.5,
        //   mr: -0.5,
        // },
        borderRadius: "6px",
        backgroundColor: colorConfig.bgColor,
        borderColor: colorConfig.baseColor,
        borderWidth: "1px",
        "&:hover": {
          backgroundColor: colorConfig.bgColor,
          opacity: 0.9,
        },
        ...props.sx,
      }}
      {...props}
    />
  );
};

export default RecipeChip;
