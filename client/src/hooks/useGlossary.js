import { useMemo } from "react";
import { useConstants } from "../contexts/ConstantsContext";
import { prepareGlossaryMatchTerms } from "../utils/textUtils";

export const useGlossary = (language = "en") => {
  const { constants } = useConstants();
  const glossaryData = constants?.glossary;

  const matchTerms = useMemo(
    () => prepareGlossaryMatchTerms(glossaryData?.terms, language),
    [glossaryData?.terms, language]
  );

  const categoryMap = useMemo(() => {
    if (!glossaryData?.categories) return {};
    return Object.fromEntries(
      glossaryData.categories.map((c) => [
        c.id,
        c.localized?.[language]?.label || c.label,
      ])
    );
  }, [glossaryData?.categories, language]);

  return {
    matchTerms,
    terms: glossaryData?.terms || [],
    categoryMap,
    language,
  };
};
