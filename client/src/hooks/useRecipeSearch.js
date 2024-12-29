import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

export const useRecipeSearch = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const searchRecipes = async () => {
      if (!searchTerm.trim()) {
        setSearchResults([]);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/recipes/search?q=${encodeURIComponent(searchTerm)}`);
        if (!response.ok) {
          throw new Error('Search failed');
        }

        const results = await response.json();
        // Transformer les résultats pour s'assurer que chaque recette a un slug valide
        const processedResults = (results || []).map(recipe => ({
          ...recipe,
          // Si le slug n'est pas défini, utiliser l'ID ou une valeur par défaut
          slug: recipe.slug || recipe.id || 'unknown'
        })).filter(recipe => recipe.slug !== 'search'); // Exclure les résultats avec le slug 'search'

        setSearchResults(processedResults);
      } catch (err) {
        console.error('Search error:', err);
        setError(err.message);
        setSearchResults([]);
      } finally {
        setIsLoading(false);
      }
    };

    const debounceTimeout = setTimeout(searchRecipes, 300);
    return () => clearTimeout(debounceTimeout);
  }, [searchTerm]);

  return {
    searchTerm,
    setSearchTerm,
    searchResults,
    isLoading,
    error
  };
};
