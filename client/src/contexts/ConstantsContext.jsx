import React, { createContext, useContext, useState, useEffect } from "react";

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || "http://localhost:3001";
const ConstantsContext = createContext(null);

export const ConstantsProvider = ({ children }) => {
  const [constants, setConstants] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchConstants = async () => {
      console.log("Fetching constants...");
      try {
        const response = await fetch(`${API_BASE_URL}/api/constants`);
        if (!response.ok) {
          throw new Error("Failed to fetch constants");
        }
        const data = await response.json();
        console.log("Constants fetched:", data);
        setConstants(data);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error("Error fetching constants:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchConstants();
  }, []);

  console.log("ConstantsProvider state:", { loading, error, constants });

  if (loading) {
    console.log("Constants still loading...");
    return null; // ou un composant de chargement si nécessaire
  }

  if (error) {
    console.error("Error in ConstantsContext:", error);
    return null; // ou un composant d'erreur si nécessaire
  }

  return (
    <ConstantsContext.Provider value={{ constants }}>
      {children}
    </ConstantsContext.Provider>
  );
};

export const useConstants = () => {
  const context = useContext(ConstantsContext);
  if (context === null) {
    throw new Error("useConstants must be used within a ConstantsProvider");
  }
  return context;
};
