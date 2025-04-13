/**
 * Convertit une chaîne de temps (ex: "1h30min") en minutes
 * @param {string|number} timeStr - La chaîne de temps à convertir ou un nombre de minutes
 * @returns {number} Le nombre de minutes
 */
export const parseTimeToMinutes = (timeStr) => {
  if (!timeStr) return 0;

  // Si timeStr est déjà un nombre, le retourner directement
  if (typeof timeStr === "number") return timeStr;

  // S'assurer que timeStr est une chaîne
  if (typeof timeStr !== "string") {
    console.warn(
      "parseTimeToMinutes: timeStr n'est pas une chaîne valide",
      timeStr
    );
    return 0;
  }

  let totalMinutes = 0;

  // Format "Xh" ou "XhYmin"
  const hourMatch = timeStr.match(/(\d+)h/);
  if (hourMatch) {
    totalMinutes += parseInt(hourMatch[1]) * 60;
  }

  // Format "X min"
  const minuteMatch = timeStr.match(/(\d+)min/);
  if (minuteMatch) {
    totalMinutes += parseInt(minuteMatch[1]);
  }

  // Format "X sec" ou "X s"
  const secondMatch = timeStr.match(/(\d+)\s*(?:sec|s)/);
  if (secondMatch) {
    totalMinutes += parseInt(secondMatch[1]) / 60;
  }

  return totalMinutes;
};

/**
 * Arrondit un nombre de minutes au multiple de 5 le plus proche
 * @param {number} minutes - Le nombre de minutes à arrondir
 * @returns {number} Le nombre de minutes arrondi au plus proche multiple de 5
 */
export const roundToNearestFive = (minutes) => {
  if (!minutes) return 0;
  return Math.round(minutes / 5) * 5;
};

/**
 * Convertit des minutes en une chaîne de temps formatée de manière compacte
 * @param {number} minutes - Le nombre de minutes à convertir
 * @returns {string} La chaîne de temps formatée de manière compacte (ex: "1h 30m")
 */
export const formatTimeCompact = (minutes) => {
  if (!minutes) return "0m";

  // Arrondir à 5 minutes près
  const roundedMinutes = roundToNearestFive(minutes);

  // Convertir en secondes pour plus de précision
  const totalSeconds = Math.round(roundedMinutes * 60);

  // Convertir en jours si plus de 24h
  if (totalSeconds >= 86400) {
    // 24h * 60min * 60sec
    const days = Math.floor(totalSeconds / 86400);
    const remainingHours = Math.floor((totalSeconds % 86400) / 3600);
    const remainingMinutes = Math.floor((totalSeconds % 3600) / 60);

    let result = `${days}j`;
    if (remainingHours > 0) {
      result += ` ${remainingHours}h`;
    }
    if (remainingMinutes > 0) {
      result += ` ${remainingMinutes}m`;
    }
    return result;
  }

  // Pour une heure ou plus (mais moins de 24h)
  const hours = Math.floor(totalSeconds / 3600);
  const remainingMinutes = Math.floor((totalSeconds % 3600) / 60);

  if (hours > 0) {
    if (remainingMinutes === 0) {
      return `${hours}h`;
    }
    return `${hours}h ${remainingMinutes}m`;
  }

  // Moins d'une heure
  return `${remainingMinutes}m`;
};

/**
 * Convertit des minutes en une chaîne de temps formatée
 * @param {number} minutes - Le nombre de minutes à convertir
 * @param {boolean} [detailed=false] - Si true, inclut les secondes pour les durées courtes
 * @returns {string} La chaîne de temps formatée
 */
export const formatTime = (minutes, detailed = false) => {
  if (!minutes) return "0 min";

  // Arrondir à 5 minutes près
  const roundedMinutes = roundToNearestFive(minutes);

  // Convertir en secondes pour plus de précision
  const totalSeconds = Math.round(roundedMinutes * 60);

  // Si moins d'une minute et mode détaillé
  if (totalSeconds < 60 && detailed) {
    return `${totalSeconds} sec`;
  }

  // Si moins d'une heure et mode détaillé
  if (totalSeconds < 3600 && detailed) {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    if (secs === 0) {
      return `${mins} min`;
    }
    return `${mins} min ${secs} sec`;
  }

  // Convertir en jours si plus de 24h
  if (totalSeconds >= 86400) {
    // 24h * 60min * 60sec
    const days = Math.floor(totalSeconds / 86400);
    const remainingHours = Math.floor((totalSeconds % 86400) / 3600);
    const remainingMinutes = Math.floor((totalSeconds % 3600) / 60);

    let result = days === 1 ? "1 day" : `${days} days`;
    if (remainingHours > 0) {
      result += ` ${remainingHours} ${remainingHours === 1 ? "hour" : "hours"}`;
    }
    if (remainingMinutes > 0) {
      result += ` ${remainingMinutes} min`;
    }
    return result;
  }

  // Pour une heure ou plus (mais moins de 24h)
  const hours = Math.floor(totalSeconds / 3600);
  const remainingMinutes = Math.floor((totalSeconds % 3600) / 60);

  if (hours > 0) {
    if (remainingMinutes === 0) {
      return hours === 1 ? "1 hour" : `${hours} hours`;
    }
    return `${hours} ${hours === 1 ? "hour" : "hours"} ${remainingMinutes} min`;
  }

  // Moins d'une heure
  return `${remainingMinutes} min`;
};

/**
 * Calcule le temps d'une recette, total ou de cuisson active selon les options
 * @param {Object} recipe - L'objet recette
 * @param {Object} options - Options pour le calcul
 * @param {boolean} [options.activeOnly=false] - Si true, ne compte que le temps de cuisson actif (étapes non passives)
 * @returns {string} Le temps formaté (ex: "1h30min")
 */
export const calculateRecipeTime = (recipe, options = {}) => {
  const { activeOnly = false } = options;

  if (!recipe?.subRecipes) return "0min";

  let totalMinutes = 0;

  Object.values(recipe.subRecipes).forEach((subRecipe) => {
    if (!subRecipe.steps) return;

    Object.values(subRecipe.steps).forEach((step) => {
      // Si activeOnly est true, ignorer les étapes passives
      if (step.time && (!activeOnly || step.stepMode !== "passive")) {
        totalMinutes += parseTimeToMinutes(step.time);
      }
    });
  });

  // Arrondir à 5 minutes près
  totalMinutes = roundToNearestFive(totalMinutes);

  // Format compact pour l'affichage du temps
  if (totalMinutes >= 60) {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return minutes > 0 ? `${hours}h${minutes}min` : `${hours}h`;
  }

  return `${totalMinutes}min`;
};

// Pour maintenir la compatibilité avec le code existant
export const calculateTotalTime = (recipe) => {
  return calculateRecipeTime(recipe, { activeOnly: false });
};

export const calculateTotalCookingTime = (recipe) => {
  return calculateRecipeTime(recipe, { activeOnly: true });
};
