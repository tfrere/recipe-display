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
    console.log("[AuthorsContext] Setting up privateAccess change listener");
    // S'abonner aux changements d'état d'accès privé
    const unsubscribe = onPrivateAccessChange((newValue) => {
      console.log(
        `[AuthorsContext] Private access changed to: ${newValue}, reloading authors`
      );
      // Recharger les auteurs lorsque l'état d'accès privé change
      fetchAuthors();
    });

    // Se désabonner lorsque le composant est démonté
    return () => {
      console.log("[AuthorsContext] Cleaning up privateAccess change listener");
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
