/**
 * Convertit une chaîne de temps (ex: "1h30min") en minutes
 * @param {string} timeStr - La chaîne de temps à convertir
 * @returns {number} Le nombre de minutes
 */
export const parseTimeToMinutes = (timeStr) => {
  if (!timeStr) return 0;

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
 * Convertit des minutes en une chaîne de temps formatée
 * @param {number} minutes - Le nombre de minutes à convertir
 * @param {boolean} [detailed=false] - Si true, inclut les secondes pour les durées courtes
 * @returns {string} La chaîne de temps formatée
 */
export const formatTime = (minutes, detailed = false) => {
  if (!minutes) return "0 min";

  // Convertir en secondes pour plus de précision
  const totalSeconds = Math.round(minutes * 60);
  
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
  if (totalSeconds >= 86400) { // 24h * 60min * 60sec
    const days = Math.floor(totalSeconds / 86400);
    const remainingHours = Math.floor((totalSeconds % 86400) / 3600);
    const remainingMinutes = Math.floor((totalSeconds % 3600) / 60);

    let result = days === 1 ? "1 day" : `${days} days`;
    if (remainingHours > 0) {
      result += ` ${remainingHours} ${remainingHours === 1 ? 'hour' : 'hours'}`;
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
    return `${hours} ${hours === 1 ? 'hour' : 'hours'} ${remainingMinutes} min`;
  }
  
  // Moins d'une heure
  return `${remainingMinutes} min`;
};

/**
 * Calcule le temps total d'une recette
 * @param {Object} recipe - L'objet recette
 * @returns {string} Le temps total formaté (ex: "1h30min")
 */
export const calculateTotalTime = (recipe) => {
  if (!recipe?.subRecipes) return '0min';

  let totalMinutes = 0;

  Object.values(recipe.subRecipes).forEach(subRecipe => {
    if (!subRecipe.steps) return;
    
    Object.values(subRecipe.steps).forEach(step => {
      if (step.time) {
        totalMinutes += parseTimeToMinutes(step.time);
      }
    });
  });

  // Format compact pour l'affichage du temps total
  if (totalMinutes >= 60) {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return minutes > 0 ? `${hours}h${minutes}min` : `${hours}h`;
  }

  return `${totalMinutes}min`;
};
