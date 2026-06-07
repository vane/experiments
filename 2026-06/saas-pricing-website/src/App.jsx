// src/App.jsx
import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import PricingPage from './components/PricingPage';

// Minimal flat theme customization
const theme = createTheme({
  palette: {
    primary: {
      main: '#2563eb', // Soft blue primary color (customize as needed)
    },
  },
  shadows: {
    1: '0 1px 3px rgba(0,0,0,0.08)',
    3: '0 4px 6px rgba(0,0,0,0.08)',
    6: '0 10px 15px rgba(0,0,0,0.08)',
    10: '0 20px 25px rgba(0,0,0,0.08)',
  },
  shape: {
    borderRadius: 8, // Soft rounded corners
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PricingPage />
    </ThemeProvider>
  );
}

export default App;

