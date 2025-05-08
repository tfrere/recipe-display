import React, { createContext, useContext, useState, useEffect } from "react";
import { ThemeProvider as MuiThemeProvider, createTheme } from "@mui/material";

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const prefersDarkMode = window.matchMedia("(prefers-color-scheme: dark)");
  const [darkMode, setDarkMode] = useState(prefersDarkMode.matches);

  useEffect(() => {
    const handleChange = (e) => {
      setDarkMode(e.matches);
    };

    if (prefersDarkMode.addEventListener) {
      prefersDarkMode.addEventListener("change", handleChange);
    } else {
      prefersDarkMode.addListener(handleChange);
    }

    return () => {
      if (prefersDarkMode.removeEventListener) {
        prefersDarkMode.removeEventListener("change", handleChange);
      } else {
        prefersDarkMode.removeListener(handleChange);
      }
    };
  }, []);

  const theme = createTheme({
    palette: {
      mode: darkMode ? "dark" : "light",
      background: {
        default: darkMode ? "#333" : "#f5f5f5",
        paper: darkMode ? "#444" : "#ffffff",
      },
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
            backgroundColor: darkMode ? "#333" : "#ffffff",
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
            backgroundColor: darkMode ? "#333" : "#ffffff",
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
            backgroundColor: darkMode ? "#333" : "#ffffff",
          },
        },
      },
    },
  });

  const toggleDarkMode = () => {
    console.warn(
      "toggleDarkMode is deprecated. Theme is now based on system preferences."
    );
  };

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
      <MuiThemeProvider theme={theme}>{children}</MuiThemeProvider>
    </ThemeContext.Provider>
  );
};
