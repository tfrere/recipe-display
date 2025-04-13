import React, { createContext, useContext, useEffect, useState } from "react";
import { getAuthors } from "../services/authorService";
import useCheatCode from "../hooks/useCheatCode";

const AuthorsContext = createContext();

export const useAuthors = () => {
  const context = useContext(AuthorsContext);
  if (!context) {
    throw new Error("useAuthors must be used within an AuthorsProvider");
  }
  return context;
};

export const AuthorsProvider = ({ children }) => {
  const [privateAuthors, setPrivateAuthors] = useState([]);
  const { hasPrivateAccess } = useCheatCode();

  useEffect(() => {
    const fetchAuthors = async () => {
      try {
        const authorsList = await getAuthors(hasPrivateAccess);
        setPrivateAuthors(authorsList);
      } catch (error) {
        console.error("Error fetching authors:", error);
      }
    };

    fetchAuthors();
  }, [hasPrivateAccess]);

  return (
    <AuthorsContext.Provider value={{ privateAuthors }}>
      {children}
    </AuthorsContext.Provider>
  );
};
