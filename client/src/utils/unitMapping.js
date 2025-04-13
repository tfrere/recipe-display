// Mapping entre les unités stockées en français et les clés de traduction
export const UNIT_MAPPING = {
  // Unités de base
  'g': 'g',
  'gramme': 'gram',
  'grammes': 'grams',
  'kg': 'kg',
  'kilogramme': 'kilogram',
  'kilogrammes': 'kilograms',
  'ml': 'ml',
  'l': 'l',
  
  // Unités impériales
  'oz': 'oz',
  'fl oz': 'fl oz',
  'once': 'oz',
  'once fluide': 'fl oz',
  'livre': 'lb',
  
  // Unités de volume
  'cuillère à soupe': 'tablespoon',
  'cuillères à soupe': 'tablespoons',
  'cuillère à café': 'teaspoon',
  'cuillères à café': 'teaspoons',
  'tasse': 'cup',
  'tasses': 'cups',
  'verre': 'glass',
  'verres': 'glasses',
  
  // Unités entières
  'unité': 'unit',
  'unités': 'units',
  'pièce': 'piece',
  'pièces': 'pieces'
};

/**
 * Convertit une unité stockée en français vers sa clé de traduction
 * @param {string} unit - L'unité en français
 * @returns {string} La clé de traduction correspondante ou l'unité d'origine si non trouvée
 */
export const mapUnitToTranslationKey = (unit) => {
  return UNIT_MAPPING[unit] || unit;
};
