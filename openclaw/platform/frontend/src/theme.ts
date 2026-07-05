import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#6366F1" },
    secondary: { main: "#0EA5E9" },
    background: { default: "#f5f6fa" },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: "Inter, system-ui, sans-serif" },
});
