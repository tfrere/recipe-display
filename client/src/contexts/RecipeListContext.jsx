import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePreferences } from './PreferencesContext';
import { useTheme } from './ThemeContext';
import constants from '@shared/constants.json';

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
  const [selectedType, setSelectedType] = useState(null);
  const [selectedDishType, setSelectedDishType] = useState(null);
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

  // Filtrer les recettes
  const filteredRecipes = useMemo(() => {
    let filtered = allRecipes;

    // Filtrer par diet si sélectionné
    if (selectedDiet) {
      filtered = filtered.filter(recipe => 
        (recipe.metadata.diet || 'normal') === selectedDiet
      );
    }

    // Filtrer par saison si sélectionnée
    if (selectedSeason) {
      filtered = filtered.filter(recipe => {
        const recipeSeason = recipe.metadata.season || 'all';
        return recipeSeason === selectedSeason || recipeSeason === 'all';
      });
    }

    // Filtrer par type si sélectionné
    if (selectedType) {
      filtered = filtered.filter(recipe => 
        recipe.metadata.type === selectedType
      );
    }

    // Filtrer par type de plat si sélectionné
    if (selectedDishType) {
      filtered = filtered.filter(recipe => 
        recipe.metadata.recipeType === selectedDishType
      );
    }

    // Filtrer par recherche si présente
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(recipe => 
        recipe.title.toLowerCase().includes(query) ||
        recipe.ingredients.some(ingredient => 
          ingredient.toLowerCase().includes(query)
        )
      );
    }

    // Filtrer les recettes rapides si activé
    if (isQuickOnly) {
      filtered = filtered.filter(recipe => recipe.metadata.quick);
    }

    return filtered;
  }, [allRecipes, selectedDiet, selectedSeason, selectedType, selectedDishType, searchQuery, isQuickOnly]);

  // Calculer le nombre total de recettes pour une saison donnée
  const getSeasonRecipeCount = (season) => {
    return allRecipes.filter(recipe => {
      const recipeSeason = recipe.metadata.season || 'all';
      return recipeSeason === season || recipeSeason === 'all';
    }).length;
  };

  // Calculer les stats pour chaque type de filtre
  const stats = useMemo(() => {
    // Fonction pour filtrer les recettes selon tous les critères sauf celui en cours d'évaluation
    const getFilteredRecipesExcept = (excludeFilter) => {
      let filtered = allRecipes;

      // Filtrer par recherche
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filtered = filtered.filter(recipe => 
          recipe.title.toLowerCase().includes(query) ||
          recipe.ingredients.some(ingredient => 
            ingredient.toLowerCase().includes(query)
          )
        );
      }

      // Appliquer les autres filtres actifs sauf celui exclu
      if (selectedDiet && excludeFilter !== 'diet') {
        filtered = filtered.filter(recipe => 
          (recipe.metadata.diet || 'normal') === selectedDiet
        );
      }

      if (selectedSeason && excludeFilter !== 'season') {
        filtered = filtered.filter(recipe => {
          const recipeSeason = recipe.metadata.season || 'all';
          return recipeSeason === selectedSeason || recipeSeason === 'all';
        });
      }

      if (selectedType && excludeFilter !== 'type') {
        filtered = filtered.filter(recipe => 
          recipe.metadata.type === selectedType
        );
      }

      if (selectedDishType && excludeFilter !== 'dishType') {
        filtered = filtered.filter(recipe => 
          recipe.metadata.recipeType === selectedDishType
        );
      }

      if (isQuickOnly && excludeFilter !== 'quick') {
        filtered = filtered.filter(recipe => recipe.metadata.quick);
      }

      return filtered;
    };

    // Calculer les stats pour chaque catégorie
    const computeStats = (recipes) => {
      const typeStats = new Map();
      const dietStats = new Map();
      const seasonStats = new Map();

      // Initialize maps with all possible values
      const allTypes = constants.recipe_types.map(type => type.id);
      allTypes.forEach(type => typeStats.set(type, 0));

      const allDiets = constants.diets.map(diet => diet.id);
      allDiets.forEach(diet => dietStats.set(diet, 0));

      const allSeasons = constants.seasons.map(season => season.id);
      allSeasons.forEach(season => seasonStats.set(season, 0));

      recipes.forEach(recipe => {
        const type = recipe.metadata.type || 'main';
        typeStats.set(type, (typeStats.get(type) || 0) + 1);

        const diet = recipe.metadata.diet || 'normal';
        dietStats.set(diet, (dietStats.get(diet) || 0) + 1);

        const season = recipe.metadata.season || 'all';
        seasonStats.set(season, (seasonStats.get(season) || 0) + 1);
      });

      const mapToSortedArray = (map, order) => {
        return order.map(key => ({
          key,
          count: map.get(key) || 0
        }));
      };

      return {
        diet: mapToSortedArray(dietStats, allDiets),
        season: mapToSortedArray(seasonStats, allSeasons),
        dishType: mapToSortedArray(typeStats, allTypes),
        quick: { count: recipes.filter(recipe => recipe.metadata.quick).length, total: filteredRecipes.length }
      };
    };

    const dietStats = computeStats(getFilteredRecipesExcept('diet'));
    const seasonStats = computeStats(getFilteredRecipesExcept('season'));
    const dishTypeStats = computeStats(getFilteredRecipesExcept('dishType'));
    const quickCount = getFilteredRecipesExcept('quick').filter(recipe => recipe.metadata.quick).length;

    return {
      diet: dietStats.diet,
      season: seasonStats.season,
      dishType: dishTypeStats.dishType,
      quick: { count: quickCount, total: filteredRecipes.length }
    };
  }, [allRecipes, selectedDiet, selectedSeason, selectedType, selectedDishType, searchQuery, isQuickOnly, filteredRecipes]);

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
    if (!searchQuery && !selectedDiet && !selectedDifficulty && !selectedSeason && !selectedType && !selectedDishType && !isQuickOnly) {
      return 'random_seasonal';
    }
    return 'filtered';
  }, [searchQuery, selectedDiet, selectedDifficulty, selectedSeason, selectedType, selectedDishType, isQuickOnly]);

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
    selectedType,
    setSelectedType,
    selectedDishType,
    setSelectedDishType,
    isQuickOnly,
    setIsQuickOnly,
    stats,
    resultsType,
    getCurrentSeason,
    resetFilters: () => {
      setSearchQuery('');
      setSelectedDiet(null);
      setSelectedSeason(null);
      setSelectedType(null);
      setSelectedDishType(null);
      setIsQuickOnly(false);
    }
  };

  return (
    <RecipeListContext.Provider value={value}>
      {children}
    </RecipeListContext.Provider>
  );
};
