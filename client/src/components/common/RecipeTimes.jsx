import React from "react";
import { Box } from "@mui/material";
import TimeDisplay from "./TimeDisplay";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import AlarmIcon from "@mui/icons-material/Alarm";

/**
 * Composant pour afficher les temps de cuisson d'une recette
 * @param {Object} props - Les propriétés du composant
 * @param {number} props.totalTime - Le temps total de la recette en minutes
 * @param {number} props.totalCookingTime - Le temps de cuisson actif en minutes
 * @param {string} props.iconSize - La taille des icônes ('small' ou autre)
 * @param {Object} props.sx - Styles supplémentaires pour les textes
 * @returns {JSX.Element} - Le composant RecipeTimes
 */
const RecipeTimes = ({
  totalTime,
  totalCookingTime,
  iconSize = "small",
  sx = { color: "white", fontWeight: 500 },
}) => {
  return (
    <>
      {/* Temps total */}
      {totalTime && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <AlarmIcon fontSize={iconSize} sx={{ color: sx.color }} />
          <TimeDisplay minutes={totalTime} variant="body2" sx={sx} />
        </Box>
      )}

      {/* Temps de cuisson actif */}
      {totalCookingTime && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <LocalFireDepartmentOutlinedIcon
            fontSize={iconSize}
            sx={{ color: sx.color }}
          />
          <TimeDisplay minutes={totalCookingTime} variant="body2" sx={sx} />
        </Box>
      )}
    </>
  );
};

export default RecipeTimes;
