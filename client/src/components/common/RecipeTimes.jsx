import React from "react";
import { Box } from "@mui/material";
import TimeDisplay from "./TimeDisplay";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import AlarmIcon from "@mui/icons-material/Alarm";
import { parseTimeToMinutes } from "../../utils/timeUtils";

/**
 * Composant pour afficher les temps de cuisson d'une recette
 * @param {Object} props - Les propriétés du composant
 * @param {string} props.totalTime - Le temps total de la recette
 * @param {string} props.totalCookingTime - Le temps de cuisson actif
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
      {/* Temps de cuisson actif */}
      {totalCookingTime && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <LocalFireDepartmentOutlinedIcon
            fontSize={iconSize}
            sx={{ color: sx.color }}
          />
          <TimeDisplay timeString={totalCookingTime} variant="body2" sx={sx} />
        </Box>
      )}

      {/* Temps passif (temps total - temps de cuisson actif) */}
      {totalTime &&
        totalCookingTime &&
        (() => {
          try {
            const totalTimeMinutes = parseTimeToMinutes(totalTime);
            const cookingTimeMinutes = parseTimeToMinutes(totalCookingTime);
            const passiveTimeMinutes = totalTimeMinutes - cookingTimeMinutes;

            // Ne pas afficher si le temps passif est nul ou négatif
            if (passiveTimeMinutes <= 0) return null;

            return (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <AlarmIcon fontSize={iconSize} sx={{ color: sx.color }} />
                <TimeDisplay
                  minutes={passiveTimeMinutes}
                  variant="body2"
                  sx={sx}
                />
              </Box>
            );
          } catch (error) {
            console.error("Erreur lors du calcul du temps passif:", error);
            return null;
          }
        })()}
    </>
  );
};

export default RecipeTimes;
