import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Toolbar, Box } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import VehicleForm from '../sections/SetupForm';
import Header from "../components/Header";
import { MainLayout } from "../layouts/MainLayout"

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


function GetManufacturers() {
  const [manufacturers, setManufacturers] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/manufacturers") // you can use localhost or 127.0.0.1
      .then((res) => res.json())
      .then((data) => {
        console.log("Fetched data:", data); // for debugging
        if (data.manufacturers) {
          setManufacturers(data.manufacturers);
        } else {
          setError("Unexpected response format");
        }
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        setError("Error fetching manufacturers");
      });
  }, []);

  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!manufacturers.length) return <p>Loading manufacturers...</p>;

  return (
    <div>
      <h2>Top Manufacturers</h2>
      <ul>
        {manufacturers.slice(0, 10).map((m) => (
          <li key={m.manufacturerId}>
            {m.brand} (ID: {m.manufacturerId})
          </li>
        ))}
      </ul>
    </div>
  );
}


function ReportSetup() {
  const [brands, setBrands] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/manufacturers")
      .then((res) => res.json())
      .then((data) => {
        if (data.manufacturers) {
            setBrands(data.manufacturers.map((m: any) => ({
              label: m.brand,
              id: m.manufacturerId
            })));
        } else {
          setError("Unexpected response format");
        }
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        setError("Error fetching manufacturers");
      });
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <MainLayout>
        {error ? (
          <p style={{ color: "red" }}>{error}</p>
        ) : brands.length === 0 ? (
          <p>Loading vehicle brands...</p>
        ) : (
          <VehicleForm vehicleBrands={brands} />
        )}
      </MainLayout>
    </ThemeProvider>
  );
}

export default ReportSetup;