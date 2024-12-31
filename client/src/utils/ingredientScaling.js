
// Unités qui doivent être arrondies à l'entier le plus proche
export const INTEGER_UNITS = new Set([
  'unit',
  'piece'
]);

// Unités qui utilisent des grammes
export const GRAM_UNITS = new Set([
  'g',
  'gram',
  'grams'
]);

// Unités qui doivent être arrondies à des fractions pratiques (1/2, 1/4, etc.)
export const FRACTION_UNITS = new Set([
  'tablespoon',
  'teaspoon',
  'cup',
  'glass'
]);

// Catégories qui ne devraient pas augmenter proportionnellement
const SCALING_FACTORS = {
  'épices': (ratio) => Math.pow(ratio, 0.8),
  'assaisonnement': (ratio) => Math.pow(ratio, 0.8),
  'levure': (ratio) => Math.pow(ratio, 0.9),
};

const UNIT_TEXTS = {
  KILOGRAM: (count) => `${count} kg`,
  GRAM: (count) => `${count} g`
};

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
  if (amount >= 1600) {
    return UNIT_TEXTS.KILOGRAM((amount / 1000).toFixed(1).replace('.', ','));
  }
  return UNIT_TEXTS.GRAM(Math.round(amount));
};

export const scaleIngredientAmount = (amount, unit, category, ratio) => {
  if (!amount) return amount;

  // Appliquer le facteur d'échelle spécial pour certaines catégories
  const scalingFactor = SCALING_FACTORS[category] || ((r) => r);
  const adjustedRatio = scalingFactor(ratio);
  
  // Calculer la nouvelle quantité
  let scaledAmount = amount * adjustedRatio;

  // Arrondir selon l'unité
  if (INTEGER_UNITS.has(unit)) {
    // Pour les œufs et autres unités entières, arrondir à l'entier le plus proche
    // mais jamais en dessous de 1
    return Math.max(1, Math.round(scaledAmount));
  }

  if (GRAM_UNITS.has(unit)) {
    // Pour les grammes, utiliser l'arrondi adaptatif
    return roundGrams(scaledAmount);
  }

  if (FRACTION_UNITS.has(unit)) {
    // Pour les unités qui utilisent des fractions pratiques
    return roundToFraction(scaledAmount);
  }

  // Pour les autres unités, arrondir à une décimale
  return Math.round(scaledAmount * 10) / 10;
};
