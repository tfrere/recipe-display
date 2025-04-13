import React, { createContext, useContext, useState, useEffect } from "react";

const PreferencesContext = createContext();

export const UNIT_SYSTEMS = {
  METRIC: "metric",
  IMPERIAL: "imperial",
};

export const usePreferences = () => {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error("usePreferences must be used within a PreferencesProvider");
  }
  return context;
};

export const PreferencesProvider = ({ children }) => {
  const [unitSystem, setUnitSystem] = useState(() => {
    const savedSystem = localStorage.getItem("unitSystem");
    return savedSystem ? JSON.parse(savedSystem) : UNIT_SYSTEMS.METRIC;
  });

  const [sortByCategory, setSortByCategory] = useState(() => {
    const savedSort = localStorage.getItem("sortByCategory");
    return savedSort ? JSON.parse(savedSort) : false;
  });

  useEffect(() => {
    localStorage.setItem("unitSystem", JSON.stringify(unitSystem));
  }, [unitSystem]);

  useEffect(() => {
    localStorage.setItem("sortByCategory", JSON.stringify(sortByCategory));
  }, [sortByCategory]);

  const toggleUnitSystem = () => {
    setUnitSystem((prev) =>
      prev === UNIT_SYSTEMS.METRIC ? UNIT_SYSTEMS.IMPERIAL : UNIT_SYSTEMS.METRIC
    );
  };

  return (
    <PreferencesContext.Provider
      value={{
        unitSystem,
        toggleUnitSystem,
        sortByCategory,
        setSortByCategory,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
};
