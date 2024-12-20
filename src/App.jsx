import React from "react";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import RecipeViewer from "./components/RecipeViewer";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#2196f3",
    },
    warning: {
      light: "#fff3e0",
      main: "#ff9800",
      dark: "#e65100",
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <RecipeViewer />
    </ThemeProvider>
  );
}

export default App;
