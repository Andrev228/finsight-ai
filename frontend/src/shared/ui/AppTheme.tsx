"use client";

import DarkModeOutlined from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlined from "@mui/icons-material/LightModeOutlined";
import CssBaseline from "@mui/material/CssBaseline";
import IconButton from "@mui/material/IconButton";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import Tooltip from "@mui/material/Tooltip";
import { useEffect, useMemo, useState } from "react";

type ThemeMode = "light" | "dark";

function createAppTheme(mode: ThemeMode) {
  return createTheme({
    typography: {
      fontFamily:
        'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    },
    palette: {
      mode,
      primary: {
        main: mode === "light" ? "#1769e0" : "#6ea8ff",
        dark: "#0c4fb6",
      },
      background: {
        default: mode === "light" ? "#f3f6fa" : "#0c111b",
        paper: mode === "light" ? "#ffffff" : "#151c29",
      },
    },
    shape: {
      borderRadius: 14,
    },
  });
}

/**
 * Applies the shared Material UI theme and browser CSS reset.
 *
 * @param children - The application UI rendered inside the theme.
 */
export default function AppTheme({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>("light");

  useEffect(() => {
    const savedMode = localStorage.getItem("themeMode");
    if (savedMode === "light" || savedMode === "dark") {
      setMode(savedMode);
      return;
    }
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      setMode("dark");
    }
  }, []);

  const theme = useMemo(() => createAppTheme(mode), [mode]);

  const toggleMode = () => {
    setMode((currentMode) => {
      const nextMode = currentMode === "light" ? "dark" : "light";
      localStorage.setItem("themeMode", nextMode);
      return nextMode;
    });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Tooltip
        title={`Switch to ${mode === "light" ? "dark" : "light"} theme`}
      >
        <IconButton
          onClick={toggleMode}
          aria-label={`Switch to ${mode === "light" ? "dark" : "light"} theme`}
          sx={{
            position: "fixed",
            top: 20,
            right: 20,
            zIndex: (muiTheme) => muiTheme.zIndex.tooltip,
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            boxShadow: 2,
            "&:hover": {
              bgcolor: "action.hover",
            },
          }}
        >
          {mode === "light" ? <DarkModeOutlined /> : <LightModeOutlined />}
        </IconButton>
      </Tooltip>
      {children}
    </ThemeProvider>
  );
}
