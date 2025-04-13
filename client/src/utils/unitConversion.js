// Facteurs de conversion
const CONVERSION_FACTORS = {
  // Poids
  g: {
    oz: 0.03527396,  // once
    lb: 0.00220462,  // livre
  },
  kg: {
    lb: 2.20462,     // livre
  },

  // Volume
  ml: {
    'fl oz': 0.033814,   // once liquide
    'cup': 0.00422675,   // tasse américaine
    'tbsp': 0.067628,    // cuillère à soupe US
    'tsp': 0.202884,     // cuillère à café US
  },
  cl: {
    'fl oz': 0.33814,    // once liquide
    'cup': 0.0422675,    // tasse américaine
    'tbsp': 0.67628,     // cuillère à soupe US
    'tsp': 2.02884,      // cuillère à café US
  },
  l: {
    'fl oz': 33.814,     // once liquide
    'cup': 4.22675,      // tasse américaine
    'qt': 1.05669,       // quart
    'gal': 0.264172,     // gallon
  },

  // Température
  'c': {
    'f': (c) => (c * 9/5) + 32,  // Celsius vers Fahrenheit
  },

  // Longueur
  'cm': {
    'in': 0.393701,      // pouce
  },
  'mm': {
    'in': 0.0393701,     // pouce
  },
};

// Unités métriques qui ont une conversion
const METRIC_UNITS = ['g', 'kg', 'ml', 'cl', 'l', 'c', 'cm', 'mm'];

// Unités impériales correspondantes
const IMPERIAL_UNITS = {
  g: 'oz',      // once pour les petites quantités
  kg: 'lb',     // livre pour les grandes quantités
  ml: 'fl oz',  // once liquide pour les petites quantités
  cl: 'fl oz',  // once liquide
  l: 'cup',     // tasse pour les grandes quantités
  c: 'f',       // fahrenheit
  cm: 'in',     // pouce
  mm: 'in',     // pouce
};

// Règles spéciales pour choisir l'unité en fonction de la quantité
const QUANTITY_RULES = {
  g: {
    threshold: 453.59237,  // 1 livre
    highUnit: 'lb',
    lowUnit: 'oz',
  },
  ml: {
    threshold: 236.588,    // 1 tasse
    highUnit: 'cup',
    lowUnit: 'fl oz',
  },
};

export const convertToImperial = (value, unit) => {
  if (!METRIC_UNITS.includes(unit)) return { value, unit };

  // Gestion des règles spéciales basées sur la quantité
  const rules = QUANTITY_RULES[unit];
  let targetUnit = IMPERIAL_UNITS[unit];
  
  if (rules && value >= rules.threshold) {
    targetUnit = rules.highUnit;
  } else if (rules) {
    targetUnit = rules.lowUnit;
  }

  const factor = CONVERSION_FACTORS[unit][targetUnit];
  
  // Gestion spéciale pour la température
  if (unit === 'c' && typeof factor === 'function') {
    return {
      value: factor(value),
      unit: targetUnit
    };
  }

  return {
    value: value * factor,
    unit: targetUnit
  };
};
