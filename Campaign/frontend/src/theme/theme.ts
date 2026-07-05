import { createTheme } from '@mui/material/styles';

// Mobile-responsive MUI theme.
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1976d2' },
    secondary: { main: '#9c27b0' },
    background: { default: '#f4f6f8' },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: 'Inter, Roboto, system-ui, sans-serif' },
  components: {
    MuiCard: { defaultProps: { elevation: 0 }, styleOverrides: { root: { border: '1px solid #e0e0e0' } } },
    MuiButton: { defaultProps: { disableElevation: true } },
  },
});
