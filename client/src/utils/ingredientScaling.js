import constants from '@shared/constants.json';

const { integer: INTEGER_UNITS, weight: { gram: GRAM_UNITS }, volume: { spoons: SPOON_UNITS, containers: CONTAINER_UNITS } } = constants.units;
const INTEGER_UNITS_SET = new Set(INTEGER_UNITS);

const SCALING_FACTORS = Object.entries(constants.scaling_factors).reduce((acc, [category, factor]) => {
  acc[category] = (ratio) => Math.pow(ratio, factor);
  return acc;
}, {});

// Fonction pour arrondir les grammes de façon adaptative
const roundGrams = (value) => {
  if (value < 20) {
    // Pour les petites quantités, on arrondit à l'unité
    return Math.round(value);
  } else if (value < 100) {
    // Pour les quantités moyennes, on arrondit à 5g près
    return Math.round(value / 5) * 5;
  } else {
    // Pour les grandes quantités, on arrondit à 10g près
    return Math.round(value / 10) * 10;
  }
};

// Fonction pour arrondir à la fraction pratique la plus proche
const roundToFraction = (value) => {
  const fractions = [0.25, 0.33, 0.5, 0.66, 0.75];
  const wholePart = Math.floor(value);
  const fractionalPart = value - wholePart;

  if (fractionalPart === 0) return value;

  let closestFraction = fractions.reduce((prev, curr) => {
    return Math.abs(curr - fractionalPart) < Math.abs(prev - fractionalPart) ? curr : prev;
  });

  // Si la fraction est très proche de 1, on arrondit à l'entier supérieur
  if (Math.abs(closestFraction - 1) < 0.1) {
    return wholePart + 1;
  }

  return wholePart + closestFraction;
};

// Fonction pour obtenir une représentation textuelle d'une fraction
export const getFractionDisplay = (value) => {
  const wholePart = Math.floor(value);
  const fractionalPart = value - wholePart;

  const fractionMap = {
    0.25: '¼',
    0.33: '⅓',
    0.5: '½',
    0.66: '⅔',
    0.75: '¾'
  };

  if (fractionalPart === 0) {
    return wholePart.toString();
  }

  const closestFraction = Object.entries(fractionMap).reduce((prev, [fraction, display]) => {
    return Math.abs(fraction - fractionalPart) < Math.abs(prev[0] - fractionalPart) ? [fraction, display] : prev;
  }, ['1', '1'])[1];

  return wholePart === 0 ? closestFraction : `${wholePart}${closestFraction}`;
};

// Fonction pour normaliser l'affichage des grammes
export const normalizeGramsDisplay = (amount) => {
  const { display } = constants.units.weight;
  if (amount >= 1600) {
    return display.kilogram.replace('{count}', (amount / 1000).toFixed(1).replace('.', ','));
  }
  return display.gram.replace('{count}', Math.round(amount));
};

export const scaleIngredientAmount = (amount, unit, category, ratio) => {
  // Si pas d'unité ou pas de ratio, on retourne la valeur telle quelle
  if (!unit || !ratio) return amount;

  // Appliquer le facteur d'échelle spécifique à la catégorie si disponible
  const scalingFactor = SCALING_FACTORS[category] || ((r) => r);
  const scaledAmount = amount * scalingFactor(ratio);

  // Arrondir selon le type d'unité
  if (INTEGER_UNITS_SET.has(unit)) {
    return Math.round(scaledAmount);
  }

  if (GRAM_UNITS.includes(unit)) {
    return roundGrams(scaledAmount);
  }

  if ([...SPOON_UNITS, ...CONTAINER_UNITS].includes(unit)) {
    return roundToFraction(scaledAmount);
  }

  // Pour les autres unités, arrondir à 2 décimales
  return Math.round(scaledAmount * 100) / 100;
};
