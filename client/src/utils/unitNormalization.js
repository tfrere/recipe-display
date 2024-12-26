// Constantes pour les unités
export const VOLUME_UNITS = new Set(['ml', 'millilitre', 'millilitres']);
export const MASS_UNITS = new Set(['g', 'gramme', 'grammes']);
export const SPOON_UNITS = new Set(['cuillère à soupe', 'cuillère à café', 'c.à.s', 'c.à.c']);

// Seuils de conversion
const THRESHOLDS = {
  VOLUME: 1000, // ml -> L
  MASS: 1000,   // g -> kg
};

// Mapping des abréviations de cuillères
const SPOON_MAPPING = {
  'cuillère à soupe': 'c.à.s',
  'cuillère à café': 'c.à.c'
};

/**
 * Normalise l'affichage d'une quantité avec son unité pour la cuisine
 * @param {number} amount - La quantité
 * @param {string} unit - L'unité de mesure
 * @returns {string} La quantité formatée avec son unité
 */
export const normalizeAmount = (amount, unit) => {
  if (!amount || !unit) return '';

  // Conversion des volumes (ml -> L)
  if (VOLUME_UNITS.has(unit)) {
    if (amount >= THRESHOLDS.VOLUME) {
      return `${(amount / THRESHOLDS.VOLUME).toFixed(1).replace('.', ',')} L`;
    }
    return `${Math.round(amount)} ml`;
  }

  // Conversion des masses (g -> kg)
  if (MASS_UNITS.has(unit)) {
    if (amount >= THRESHOLDS.MASS) {
      return `${(amount / THRESHOLDS.MASS).toFixed(1).replace('.', ',')} kg`;
    }
    return `${Math.round(amount)} g`;
  }

  // Pour les cuillères, utiliser les abréviations
  if (SPOON_UNITS.has(unit)) {
    const normalizedUnit = SPOON_MAPPING[unit] || unit;
    return `${amount} ${normalizedUnit}`;
  }

  // Pour toutes les autres unités, retourner la valeur avec un espace
  return `${amount} ${unit}`;
};
