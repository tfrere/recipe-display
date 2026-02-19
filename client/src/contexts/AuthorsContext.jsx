import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import useLongPress from "../hooks/useLongPress";
import { getAuthors } from "../services/authorService";

const AuthorsContext = createContext();

export const useAuthors = () => {
  const context = useContext(AuthorsContext);
  if (!context) {
    throw new Error("useAuthors must be used within a AuthorsProvider");
  }
  return context;
};

export const AuthorsProvider = ({ children }) => {
  const [authors, setAuthors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { hasPrivateAccess, onPrivateAccessChange } = useLongPress();

  const fetchAuthors = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAuthors(hasPrivateAccess);
      setAuthors(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [hasPrivateAccess]);

  // Écouter les changements d'état d'accès privé
  useEffect(() => {
    const unsubscribe = onPrivateAccessChange((newValue) => {
      fetchAuthors();
    });

    return () => {
      unsubscribe();
    };
  }, [onPrivateAccessChange, fetchAuthors]);

  useEffect(() => {
    fetchAuthors();
  }, [fetchAuthors]);

  return (
    <AuthorsContext.Provider
      value={{ authors, loading, error, hasPrivateAccess }}
    >
      {children}
    </AuthorsContext.Provider>
  );
};
