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
    return Math.abs(curr - fractionalPart) < Math.abs(prev - fractionalPart)
      ? curr
      : prev;
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
    0.25: "¼",
    0.33: "⅓",
    0.5: "½",
    0.66: "⅔",
    0.75: "¾",
  };

  if (fractionalPart === 0) {
    return wholePart.toString();
  }

  const closestFraction = Object.entries(fractionMap).reduce(
    (prev, [fraction, display]) => {
      return Math.abs(fraction - fractionalPart) <
        Math.abs(prev[0] - fractionalPart)
        ? [fraction, display]
        : prev;
    },
    ["1", "1"]
  )[1];

  return wholePart === 0 ? closestFraction : `${wholePart}${closestFraction}`;
};

// Fonction pour normaliser l'affichage des grammes
export const normalizeGramsDisplay = (amount, constants) => {
  const { display } = constants?.units?.weight || {
    display: { kilogram: "{count}kg", gram: "{count}g" },
  };
  if (amount >= 1600) {
    return display.kilogram.replace(
      "{count}",
      (amount / 1000).toFixed(1).replace(".", ",")
    );
  }
  return display.gram.replace("{count}", Math.round(amount));
};

export const scaleIngredientAmount = (
  amount,
  unit,
  category,
  ratio,
  constants
) => {
  // Si pas de ratio, on retourne la valeur telle quelle
  if (!ratio) return amount;

  // Extraire les unités des constantes avec des valeurs par défaut
  const INTEGER_UNITS = constants?.units?.integer || [];
  const GRAM_UNITS = constants?.units?.weight?.gram || [];
  const SPOON_UNITS = constants?.units?.volume?.spoons || [];
  const CONTAINER_UNITS = constants?.units?.volume?.containers || [];
  const INTEGER_UNITS_SET = new Set(INTEGER_UNITS);

  // Créer les facteurs d'échelle à partir des constantes
  const SCALING_FACTORS = Object.entries(
    constants?.scaling_factors || {}
  ).reduce((acc, [cat, factor]) => {
    acc[cat] = (r) => Math.pow(r, factor);
    return acc;
  }, {});

  // Appliquer le facteur d'échelle spécifique à la catégorie si disponible
  const scalingFactor = SCALING_FACTORS[category] || ((r) => r);
  const scaledAmount = amount * scalingFactor(ratio);

  // Arrondir selon le type d'unité
  if (unit && INTEGER_UNITS_SET.has(unit)) {
    return Math.round(scaledAmount);
  }

  if (unit && GRAM_UNITS.includes(unit)) {
    return roundGrams(scaledAmount);
  }

  if (unit && [...SPOON_UNITS, ...CONTAINER_UNITS].includes(unit)) {
    return roundToFraction(scaledAmount);
  }

  // Pour les autres unités ou sans unité, arrondir à 2 décimales
  return Math.round(scaledAmount * 100) / 100;
};
