"use client";

import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0D4A6F", // Deep clinical blue
      light: "#3B7A9E",
      dark: "#083047",
      contrastText: "#FFFFFF",
    },
    secondary: {
      main: "#0F766E", // Teal for life sciences
      light: "#14B8A6",
      dark: "#115E59",
      contrastText: "#FFFFFF",
    },
    background: {
      default: "#F8FAFC", // Slate-50
      paper: "#FFFFFF",
    },
    text: {
      primary: "#0F172A", // Slate-900
      secondary: "#475569", // Slate-600
    },
    success: {
      main: "#15803D",
      light: "#DCFCE7",
    },
    warning: {
      main: "#B45309",
      light: "#FEF3C7",
    },
    error: {
      main: "#B91C1C",
      light: "#FEE2E2",
    },
    info: {
      main: "#0369A1",
      light: "#E0F2FE",
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: "1px solid #E2E8F0",
        },
      },
    },
  },
});

export default theme;
