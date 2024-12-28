import React, { createContext, useContext, useState } from 'react';
import useLocalStorage from '../hooks/useLocalStorage';

const LayoutContext = createContext();

export const LAYOUT_MODES = {
  SINGLE_COLUMN: 'single_column',
  TWO_COLUMN: 'two_column'
};

export const LayoutProvider = ({ children }) => {
  const [layoutMode, setLayoutMode] = useLocalStorage('layoutMode', LAYOUT_MODES.SINGLE_COLUMN);

  const toggleLayout = () => {
    setLayoutMode(prevMode => 
      prevMode === LAYOUT_MODES.SINGLE_COLUMN 
        ? LAYOUT_MODES.TWO_COLUMN 
        : LAYOUT_MODES.SINGLE_COLUMN
    );
  };

  return (
    <LayoutContext.Provider value={{ layoutMode, toggleLayout }}>
      {children}
    </LayoutContext.Provider>
  );
};

export const useLayout = () => {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error('useLayout must be used within a LayoutProvider');
  }
  return context;
};

export default LayoutContext;
