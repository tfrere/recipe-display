import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001';

const RecipeListContext = createContext();

export const useRecipeList = () => {
  const context = useContext(RecipeListContext);
  if (!context) {
    throw new Error('useRecipeList must be used within a RecipeListProvider');
  }
  return context;
};

export const RecipeListProvider = ({ children }) => {
  const [allRecipes, setAllRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDiet, setSelectedDiet] = useState(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [isQuickOnly, setIsQuickOnly] = useState(false);

  // Charger toutes les recettes au montage du composant
  useEffect(() => {
    const fetchRecipes = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/recipes`);
        if (!response.ok) {
          throw new Error('Failed to fetch recipes');
        }
        const data = await response.json();
        setAllRecipes(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRecipes();
  }, []);

  // Calculer les stats pour chaque type de filtre
  const stats = useMemo(() => {
    const dietStats = new Map();
    const difficultyStats = new Map();
    const seasonStats = new Map();
    let quickCount = 0;
    let totalCount = 0;
    
    allRecipes.forEach(recipe => {
      totalCount++;
      
      // Stats pour les régimes
      const diet = recipe.metadata.diet || 'normal';
      dietStats.set(diet, (dietStats.get(diet) || 0) + 1);
      
      // Stats pour les difficultés
      const difficulty = recipe.metadata.difficulty || 'medium';
      difficultyStats.set(difficulty, (difficultyStats.get(difficulty) || 0) + 1);
      
      // Stats pour les saisons
      const season = recipe.metadata.season || 'all';
      if (season === 'all') {
        // Si c'est 'all', ajouter à toutes les saisons
        ['spring', 'summer', 'autumn', 'winter'].forEach(s => {
          seasonStats.set(s, (seasonStats.get(s) || 0) + 1);
        });
      } else {
        seasonStats.set(season, (seasonStats.get(season) || 0) + 1);
      }
      
      // Compteur pour les recettes rapides
      if (recipe.metadata.quick) {
        quickCount++;
      }
    });

    const mapToSortedArray = (map) => 
      Array.from(map.entries())
        .map(([key, count]) => ({ key, count }))
        .sort((a, b) => b.count - a.count);

    return {
      diet: mapToSortedArray(dietStats),
      difficulty: mapToSortedArray(difficultyStats),
      season: mapToSortedArray(seasonStats),
      quick: { count: quickCount, total: totalCount }
    };
  }, [allRecipes]);

  // Déterminer la saison actuelle
  const getCurrentSeason = () => {
    const month = new Date().getMonth();
    if (month >= 2 && month <= 4) return 'spring';
    if (month >= 5 && month <= 7) return 'summer';
    if (month >= 8 && month <= 10) return 'autumn';
    return 'winter';
  };

  // Déterminer le type de résultats (random seasonal ou filtered)
  const resultsType = useMemo(() => {
    if (!searchQuery && !selectedDiet && !selectedDifficulty && !selectedSeason && !isQuickOnly) {
      return 'random_seasonal';
    }
    return 'filtered';
  }, [searchQuery, selectedDiet, selectedDifficulty, selectedSeason, isQuickOnly]);

  // Filtrer les recettes
  const filteredRecipes = useMemo(() => {
    let filtered = allRecipes;

    // Filtrer par diet si sélectionné
    if (selectedDiet) {
      filtered = filtered.filter(recipe => 
        (recipe.metadata.diet || 'normal') === selectedDiet
      );
    }

    // Filtrer par difficulté si sélectionnée
    if (selectedDifficulty) {
      filtered = filtered.filter(recipe => 
        (recipe.metadata.difficulty || 'medium') === selectedDifficulty
      );
    }

    // Filtrer par saison si sélectionnée
    if (selectedSeason) {
      filtered = filtered.filter(recipe => 
        recipe.metadata.season === selectedSeason || recipe.metadata.season === 'all'
      );
    }

    // Filtrer les recettes rapides si activé
    if (isQuickOnly) {
      filtered = filtered.filter(recipe => recipe.metadata.quick);
    }

    // Filtrer par recherche si présente
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(recipe => 
        recipe.ingredients.some(ingredient => 
          ingredient.toLowerCase().includes(query)
        )
      );
    }

    // Si aucun filtre n'est actif, retourner 25 recettes aléatoires de la saison actuelle
    if (!searchQuery && !selectedDiet && !selectedDifficulty && !selectedSeason && !isQuickOnly) {
      const currentSeason = getCurrentSeason();
      const seasonalRecipes = allRecipes.filter(recipe => 
        recipe.metadata.season === currentSeason || recipe.metadata.season === 'all'
      );
      const shuffled = [...seasonalRecipes].sort(() => 0.5 - Math.random());
      return shuffled.slice(0, 25);
    }

    // Limiter à 25 résultats
    return filtered.slice(0, 25);
  }, [allRecipes, searchQuery, selectedDiet, selectedDifficulty, selectedSeason, isQuickOnly]);

  const value = {
    allRecipes,
    filteredRecipes,
    loading,
    error,
    searchQuery,
    setSearchQuery,
    selectedDiet,
    setSelectedDiet,
    selectedDifficulty,
    setSelectedDifficulty,
    selectedSeason,
    setSelectedSeason,
    isQuickOnly,
    setIsQuickOnly,
    stats,
    resultsType,
    getCurrentSeason,
  };

  return (
    <RecipeListContext.Provider value={value}>
      {children}
    </RecipeListContext.Provider>
  );
};
