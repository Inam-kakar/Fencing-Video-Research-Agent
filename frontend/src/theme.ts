import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1f4f46",
      dark: "#173b35",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#8a5a2b",
    },
    background: {
      default: "#f6f7f5",
      paper: "#ffffff",
    },
    success: {
      main: "#2f7d4f",
    },
    warning: {
      main: "#a56a1f",
    },
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: "2.25rem",
      fontWeight: 700,
    },
    h2: {
      fontSize: "1.35rem",
      fontWeight: 700,
    },
    button: {
      textTransform: "none",
      fontWeight: 700,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(31, 79, 70, 0.12)",
          boxShadow: "0 8px 24px rgba(31, 79, 70, 0.08)",
        },
      },
    },
  },
});
