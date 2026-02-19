export const highlightMatches = (text, recipe, step) => {
  if (!text || !recipe) return text;

  let ingredientNames = [];
  let toolNames = (step.tools || step.requires || []).filter(Boolean);
  let stateNames = [];

  // uses[] contains ingredient IDs and state IDs
  ingredientNames = (step.uses || [])
    .map((ref) => {
      const ingredient = recipe.ingredients?.find((ing) => ing.id === ref);
      return ingredient?.name;
    })
    .filter(Boolean);

  // States referenced in uses (those not matching ingredients)
  stateNames = (step.uses || [])
    .filter(
      (ref) => !recipe.ingredients?.find((ing) => ing.id === ref)
    );

  // Add produces as state name
  if (step.produces) {
    stateNames.push(step.produces);
  }

  // Combine all terms to match
  const terms = [...ingredientNames, ...toolNames, ...stateNames]
    .map((term) => term.toLowerCase().split(/\s+/))
    .flat()
    .filter((term) => term.length >= 3);

  // Sort terms by length (longest first) to avoid partial matches
  terms.sort((a, b) => b.length - a.length);

  // Split the text into segments and create spans for matches
  let segments = [{ text, isMatch: false }];

  terms.forEach((term) => {
    segments = segments.flatMap((segment) => {
      if (segment.isMatch) return [segment];

      // Escape special regex characters and create a regex that matches the exact term within word boundaries
      const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`\\b(${escapedTerm})\\b`, "gi");
      const parts = segment.text.split(regex);

      // Reconstruct the segments with matches
      return parts.map((part) => ({
        text: part,
        isMatch: part.toLowerCase() === term.toLowerCase(),
      }));
    });
  });

  // Return HTML string with highlighted matches
  return segments.map((segment, index) =>
    segment.isMatch ? (
      <span
        key={index}
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.03)",
          fontWeight: 600,
          borderRadius: "2px",
        }}
      >
        {segment.text}
      </span>
    ) : (
      segment.text
    )
  );
};
