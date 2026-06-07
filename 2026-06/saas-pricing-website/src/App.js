// src/App.js
import React from 'react';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import PricingSection from './PricingSection';

// Create a minimal, clean theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#2563eb', // Modern blue
      light: '#60a5fa',
    },
    secondary: {
      main: '#10b981', // Emerald green for success/checks
    },
    background: {
      default: '#f9f9f9',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h6: { fontWeight: 600 },
  },
  shape: {
    borderRadius: 12, // Softer corners
  },
});

function App() {
  return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <PricingSection />
      </ThemeProvider>
  );
}

export default App;
