/**
 * Shared season detection utilities.
 *
 * Single source of truth for determining the current season
 * based on the calendar month (Northern Hemisphere, France).
 */

/**
 * Get the current season based on the current month.
 * @returns {"spring"|"summer"|"autumn"|"winter"}
 */
export const getCurrentSeason = () => {
  const month = new Date().getMonth();
  if (month >= 2 && month <= 4) return "spring";
  if (month >= 5 && month <= 7) return "summer";
  if (month >= 8 && month <= 10) return "autumn";
  return "winter";
};

export const SEASON_EMOJI = {
  spring: "\u{1F331}",
  summer: "\u2600\uFE0F",
  autumn: "\u{1F342}",
  winter: "\u2744\uFE0F",
};

export const SEASON_LABELS = {
  spring: "Spring",
  summer: "Summer",
  autumn: "Autumn",
  winter: "Winter",
};
