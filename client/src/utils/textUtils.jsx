// Unicode-aware word boundary: treats accented Latin chars (à-ÿ) as word characters,
// unlike JS's \b which sees them as non-word and breaks matching on "sauté", "flambé", etc.
const WORD_CHAR = String.raw`[a-zA-Z\u00C0-\u024F0-9_]`;

const createWordBoundaryRegex = (term) => {
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<!${WORD_CHAR})(${escaped})(?!${WORD_CHAR})`, "gi");
};

const segmentByTerms = (segments, terms, matchType) => {
  let result = segments;
  terms.forEach((term) => {
    result = result.flatMap((segment) => {
      if (segment.type !== "plain") return [segment];

      const regex = createWordBoundaryRegex(term.text);
      const parts = segment.text.split(regex);

      return parts.map((part) => ({
        text: part,
        type:
          part.toLowerCase() === term.text.toLowerCase() ? matchType : "plain",
        ...(matchType === "glossary" &&
        part.toLowerCase() === term.text.toLowerCase()
          ? { glossaryEntry: term.entry }
          : {}),
      }));
    });
  });
  return result;
};

/**
 * Pre-compute the sorted match term list from raw glossary entries.
 * When `language` matches a key in an entry's `localized` object,
 * the localized term + aliases are used for matching instead of the root ones.
 * The `entry` reference stays the same so the popover shows the correct definition.
 * Meant to be called once and memoized (e.g. via useMemo).
 */
export const prepareGlossaryMatchTerms = (glossaryTerms, language = "en") => {
  if (!glossaryTerms?.length) return [];
  return glossaryTerms
    .flatMap((entry) => {
      const loc = entry.localized?.[language];
      const all = loc
        ? [loc.term, ...(loc.aliases || [])]
        : [entry.term, ...(entry.aliases || [])];
      return all.map((alias) => ({ text: alias.toLowerCase(), entry }));
    })
    .filter((t) => t.text.length >= 2)
    .sort((a, b) => b.text.length - a.text.length);
};

/**
 * Segment step text into typed chunks: "plain", "ingredient", "glossary".
 * Returns pure data — no JSX.
 */
export const segmentStepText = (text, recipe, step, glossaryMatchTerms) => {
  if (!text || !recipe) return [{ text: text || "", type: "plain" }];

  const ingredientNames = (step.uses || [])
    .map((ref) => recipe.ingredients?.find((ing) => ing.id === ref)?.name)
    .filter(Boolean);

  const toolNames = (step.tools || step.requires || []).filter(Boolean);

  const stateNames = (step.uses || []).filter(
    (ref) => !recipe.ingredients?.find((ing) => ing.id === ref)
  );
  if (step.produces) stateNames.push(step.produces);

  const recipeTerms = [...ingredientNames, ...toolNames, ...stateNames]
    .flatMap((term) => term.toLowerCase().split(/\s+/))
    .filter((t) => t.length >= 3)
    .sort((a, b) => b.length - a.length)
    .map((t) => ({ text: t }));

  let segments = [{ text, type: "plain" }];
  segments = segmentByTerms(segments, recipeTerms, "ingredient");

  if (glossaryMatchTerms?.length) {
    segments = segmentByTerms(segments, glossaryMatchTerms, "glossary");
  }

  return segments;
};

/**
 * Segment text for glossary-only matching (no recipe/ingredient context).
 * Returns pure data — no JSX.
 */
export const segmentGlossaryOnly = (text, glossaryMatchTerms) => {
  if (!text || !glossaryMatchTerms?.length)
    return [{ text: text || "", type: "plain" }];

  return segmentByTerms([{ text, type: "plain" }], glossaryMatchTerms, "glossary");
};
