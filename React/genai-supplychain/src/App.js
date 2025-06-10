import React, { useState } from 'react';
import './App.css';
import { TextField, Button, Box, Typography, Container, Paper, FormControl, InputLabel, Select, MenuItem } from '@mui/material';

function App() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    manufacturer: '',
    model: '',
    type: ''
  });

  // Sample car data for dropdowns - you can replace with your actual data
  const manufacturers = ['Toyota', 'Honda', 'Ford', 'BMW', 'Mercedes-Benz', 'Audi', 'Chevrolet', 'Nissan'];
  const models = ['Camry', 'Accord', 'F-150', '3 Series', 'C-Class', 'A4', 'Silverado', 'Altima'];
  const types = ['Sedan', 'SUV', 'Truck', 'Hatchback', 'Coupe', 'Convertible', 'Wagon', 'Crossover'];

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert(`Name: ${formData.name}\nEmail: ${formData.email}\nManufacturer: ${formData.manufacturer}\nModel: ${formData.model}\nType: ${formData.type}`);
  };

  return (
    <div className="App">
      <header className="App-header">
        <Container maxWidth="sm">
          <Paper
            elevation={1}
            sx={{
              p: 4,
              backgroundColor: 'background.paper',
              borderRadius: 3
            }}
          >
            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <Typography
                variant="h4"
                component="h1"
                sx={{
                  color: 'text.primary',
                  fontWeight: 600,
                  mb: 1
                }}
              >
                Select Vehicle
              </Typography>

              <Typography
                variant="body2"
                sx={{
                  color: 'text.secondary',
                  mb: 2
                }}
              >
                Please fill out the form below to continue on the app.
              </Typography>

              <FormControl fullWidth variant="outlined">
                <InputLabel sx={{ color: 'text.secondary' }}>Select Manufacturer</InputLabel>
                <Select
                  name="manufacturer"
                  value={formData.manufacturer}
                  onChange={handleChange}
                  label="Select Manufacturer"
                  sx={{
                    '& .MuiSelect-select': {
                      backgroundColor: 'background.default',
                      textAlign: 'left',
                    }
                  }}
                >
                  {manufacturers.map((manufacturer) => (
                    <MenuItem key={manufacturer} value={manufacturer}>
                      {manufacturer}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth variant="outlined">
                <InputLabel sx={{ color: 'text.secondary' }}>Select Model</InputLabel>
                <Select
                  name="model"
                  value={formData.model}
                  onChange={handleChange}
                  label="Select Model"
                  sx={{
                    '& .MuiSelect-select': {
                      backgroundColor: 'background.default',
                      textAlign: 'left',
                    }
                  }}
                >
                  {models.map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth variant="outlined">
                <InputLabel sx={{ color: 'text.secondary' }}>Select Type</InputLabel>
                <Select
                  name="type"
                  value={formData.type}
                  onChange={handleChange}
                  label="Select Type"
                  sx={{
                    '& .MuiSelect-select': {
                      backgroundColor: 'background.default',
                      textAlign: 'left',
                    }
                  }}
                >
                  {types.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                type="submit"
                variant="contained"
                color="primary"
                size="large"
                sx={{
                  mt: 1,
                  py: 1.5,
                  typography: 'button',
                  fontWeight: 600,
                  textTransform: 'none'
                }}
              >
                Submit
              </Button>

              <Typography
                variant="caption"
                sx={{
                  color: 'text.disabled',
                  textAlign: 'center',
                  mt: 1
                }}
              >
                We'll get back to you within 24 hours.
              </Typography>
            </Box>
          </Paper>
        </Container>
      </header>
    </div>
  );
}

export default App;