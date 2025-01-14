// Constantes pour les unités
const UNIT_MAPPING = {
  "c.à.s": "cuillère à soupe",
  "c.à.c": "cuillère à café",
  "c à s": "cuillère à soupe",
  "c à c": "cuillère à café",
  cas: "cuillère à soupe",
  cac: "cuillère à café",
  "cuillere a soupe": "cuillère à soupe",
  "cuillere a cafe": "cuillère à café",
  "cuillères à soupe": "cuillère à soupe",
  "cuillères à café": "cuillère à café",
};

export const VOLUME_UNITS = new Set(["ml", "millilitre", "millilitres"]);
export const MASS_UNITS = new Set(["g", "gramme", "grammes"]);

// Seuils de conversion
const THRESHOLDS = {
  VOLUME: 1000, // ml -> L
  MASS: 1000, // g -> kg
};

/**
 * Normalise l'affichage d'une quantité avec son unité pour la cuisine
 * @param {number} amount - La quantité
 * @param {string} unit - L'unité de mesure
 * @param {object} constants - Les constantes de l'application
 * @returns {string} La quantité formatée avec son unité
 */
export const normalizeAmount = (amount, unit, constants) => {
  if (!amount || !unit) return "";

  const SPOON_UNITS = new Set(constants?.units?.volume?.spoons || []);

  // Conversion des volumes (ml -> L)
  if (VOLUME_UNITS.has(unit)) {
    if (amount >= THRESHOLDS.VOLUME) {
      return `${(amount / THRESHOLDS.VOLUME).toFixed(1).replace(".", ",")} L`;
    }
    return `${Math.round(amount)} ml`;
  }

  // Conversion des masses (g -> kg)
  if (MASS_UNITS.has(unit)) {
    if (amount >= THRESHOLDS.MASS) {
      return `${(amount / THRESHOLDS.MASS).toFixed(1).replace(".", ",")} kg`;
    }
    return `${Math.round(amount)} g`;
  }

  // Pour les cuillères, utiliser les abréviations
  if (SPOON_UNITS.has(unit)) {
    const normalizedUnit = UNIT_MAPPING[unit] || unit;
    return `${amount} ${normalizedUnit}`;
  }

  // Pour toutes les autres unités, retourner la valeur avec un espace
  return `${amount} ${unit}`;
};
