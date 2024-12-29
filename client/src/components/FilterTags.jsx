import React from 'react';
import { Box, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useRecipeList } from '../contexts/RecipeListContext';
import FilterTag from './common/FilterTag';

const FilterSection = ({ title, items, selectedValue, onSelect, translatePrefix }) => {
  const { t } = useTranslation();

  if (items.length === 0) return null;

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
        {title}
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {items.map(({ key, count }) => (
          <FilterTag
            key={key}
            label={t(`${translatePrefix}.${key.toLowerCase()}`)}
            count={count}
            checked={selectedValue === key}
            onChange={() => onSelect(selectedValue === key ? null : key)}
            showCheckbox={true}
          />
        ))}
      </Box>
    </Box>
  );
};

const FilterTags = () => {
  const { t } = useTranslation();
  const { 
    selectedDiet,
    setSelectedDiet,
    selectedDifficulty,
    setSelectedDifficulty,
    selectedSeason,
    setSelectedSeason,
    isQuickOnly,
    setIsQuickOnly,
    stats,
  } = useRecipeList();

  return (
    <Box sx={{ mt: 2 }}>
      <FilterSection
        title={t('filters.diet')}
        items={stats.diet}
        selectedValue={selectedDiet}
        onSelect={setSelectedDiet}
        translatePrefix="diet"
      />
      <FilterSection
        title={t('filters.difficulty')}
        items={stats.difficulty}
        selectedValue={selectedDifficulty}
        onSelect={setSelectedDifficulty}
        translatePrefix="difficulty"
      />
      <FilterSection
        title={t('filters.season')}
        items={stats.season}
        selectedValue={selectedSeason}
        onSelect={setSelectedSeason}
        translatePrefix="season"
      />
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
          {t('filters.quick')}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <FilterTag
            label={t('filters.quickRecipes')}
            count={stats.quick.count}
            checked={isQuickOnly}
            onChange={() => setIsQuickOnly(!isQuickOnly)}
            showCheckbox={true}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default FilterTags;
