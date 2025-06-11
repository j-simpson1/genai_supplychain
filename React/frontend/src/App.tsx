import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import VehicleForm from './VehicleForm';

// Create a custom theme (optional - you can customize colors, typography, etc.)
const theme = createTheme({
  palette: {
    primary: {
      main: '#3b82f6', // Blue color to match your original design
    },
    secondary: {
      main: '#6366f1',
    },
    background: {
      default: '#f8fafc', // Light gray background
    },
  },
  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  shape: {
    borderRadius: 12, // Rounded corners to match your design
  },
  components: {
    // Optional: Customize MUI components globally
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none', // Disable uppercase transformation
          fontWeight: 600,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      {/* CssBaseline provides consistent CSS baseline across browsers */}
      <CssBaseline />
      <VehicleForm />
    </ThemeProvider>
  );
}

export default App;