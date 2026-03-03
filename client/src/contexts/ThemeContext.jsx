import React, { createContext, useContext, useState, useEffect, useMemo } from "react";
import { ThemeProvider as MuiThemeProvider, createTheme } from "@mui/material";

const STORAGE_KEY = "theme-mode";

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};

function getSystemPreference() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolveInitialMode() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored === "dark";
  return getSystemPreference();
}

export const ThemeProvider = ({ children }) => {
  const [themeMode, setThemeModeState] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  });
  const [darkMode, setDarkMode] = useState(resolveInitialMode);

  useEffect(() => {
    if (themeMode !== "system") {
      setDarkMode(themeMode === "dark");
      return;
    }

    setDarkMode(getSystemPreference());
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e) => setDarkMode(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [themeMode]);

  const setThemeMode = (mode) => {
    setThemeModeState(mode);
    if (mode === "system") {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, mode);
    }
  };

  const toggleDarkMode = () => {
    setThemeMode(darkMode ? "light" : "dark");
  };

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: darkMode ? "dark" : "light",
          background: {
            default: darkMode ? "#252525" : "#f5f5f5",
            paper: darkMode ? "#1a1a1a" : "#ffffff",
          },
          text: {
            primary: darkMode ? "#e8e8e8" : "rgba(0, 0, 0, 0.87)",
            secondary: darkMode ? "#a0a0a0" : "rgba(0, 0, 0, 0.6)",
          },
          divider: darkMode ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.12)",
        },
        shape: {
          borderRadius: 6,
        },
        components: {
          MuiPaper: {
            defaultProps: {
              elevation: 0,
            },
            styleOverrides: {
              root: {
                borderRadius: 6,
              },
            },
          },
          MuiCard: {
            styleOverrides: {
              root: {
                borderRadius: 6,
              },
            },
          },
          MuiButton: {
            defaultProps: {
              disableElevation: true,
            },
            styleOverrides: {
              root: {
                borderRadius: 6,
                textTransform: "none",
              },
            },
          },
          MuiIconButton: {
            defaultProps: {
              size: "small",
            },
            styleOverrides: {
              root: {
                padding: 8,
                borderRadius: 6,
                "&.MuiIconButton-sizeMedium": {
                  padding: 8,
                  borderRadius: 6,
                },
                "&.MuiIconButton-sizeSmall": {
                  padding: 6,
                  borderRadius: 6,
                },
              },
              sizeSmall: {
                padding: 6,
                borderRadius: 6,
              },
              sizeMedium: {
                padding: 8,
                borderRadius: 6,
              },
            },
          },
          MuiChip: {
            styleOverrides: {
              root: {
                borderRadius: 4,
              },
            },
          },
          MuiTextField: {
            styleOverrides: {
              root: {
                "& .MuiOutlinedInput-root": {
                  borderRadius: 6,
                },
              },
            },
          },
          MuiAutocomplete: {
            styleOverrides: {
              root: {
                "& .MuiOutlinedInput-root": {
                  borderRadius: 6,
                },
              },
              popper: {
                "& .MuiPaper-root": {
                  borderRadius: 6,
                },
              },
            },
          },
          MuiDialog: {
            styleOverrides: {
              paper: {
                borderRadius: 6,
              },
            },
          },
          MuiAlert: {
            styleOverrides: {
              root: {
                borderRadius: 6,
              },
            },
          },
          MuiInputBase: {
            styleOverrides: {
              root: {
                backgroundColor: darkMode ? "#1a1a1a" : "#ffffff",
              },
            },
          },
        },
      }),
    [darkMode]
  );

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode, themeMode, setThemeMode }}>
      <MuiThemeProvider theme={theme}>{children}</MuiThemeProvider>
    </ThemeContext.Provider>
  );
};
