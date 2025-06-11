import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Container,
  Grid
} from '@mui/material';
import { styled } from '@mui/material/styles';

// Custom styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(5),
  maxWidth: 450,
  margin: '40px auto',
  borderRadius: 16,
  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
}));

const StyledFormControl = styled(FormControl)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  '& .MuiOutlinedInput-root': {
    borderRadius: 12,
    '&:hover .MuiOutlinedInput-notchedOutline': {
      borderColor: theme.palette.primary.main,
    },
    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
      borderWidth: 2,
    },
  },
}));

const StyledButton = styled(Button)(({ theme }) => ({
  borderRadius: 12,
  padding: theme.spacing(2, 3),
  fontSize: '16px',
  fontWeight: 600,
  textTransform: 'none',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 8px 12px -1px rgba(0, 0, 0, 0.15)',
  },
  transition: 'all 0.2s ease',
}));

function VehicleForm() {
  const [formData, setFormData] = useState({
    vehicle: '',
    model: '',
    type: ''
  });

  const vehicleBrands = [
    'Toyota', 'Honda', 'Ford', 'Chevrolet', 'BMW', 'Mercedes-Benz', 'Audi',
    'Volkswagen', 'Nissan', 'Hyundai', 'Kia', 'Mazda', 'Subaru', 'Lexus',
    'Acura', 'Infiniti', 'Cadillac', 'Lincoln', 'Buick', 'GMC', 'Jeep',
    'Ram', 'Dodge', 'Chrysler', 'Volvo', 'Jaguar', 'Land Rover', 'Porsche',
    'Tesla', 'Genesis', 'Alfa Romeo', 'Maserati', 'Ferrari', 'Lamborghini'
  ];

  const modelsByBrand = {
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Prius', 'Tacoma', 'Tundra', '4Runner', 'Sienna', 'Avalon'],
    'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'HR-V', 'Passport', 'Ridgeline', 'Insight', 'Odyssey', 'Fit'],
    'Ford': ['F-150', 'Mustang', 'Explorer', 'Escape', 'Edge', 'Expedition', 'Ranger', 'Bronco', 'Focus', 'Fusion'],
    'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Traverse', 'Tahoe', 'Suburban', 'Colorado', 'Camaro', 'Corvette', 'Cruze'],
    'BMW': ['3 Series', '5 Series', '7 Series', 'X1', 'X3', 'X5', 'X7', 'i3', 'i8', 'Z4'],
    'Mercedes-Benz': ['C-Class', 'E-Class', 'S-Class', 'GLA', 'GLC', 'GLE', 'GLS', 'A-Class', 'CLA', 'SL'],
    'Audi': ['A3', 'A4', 'A6', 'A8', 'Q3', 'Q5', 'Q7', 'Q8', 'TT', 'R8'],
    'Volkswagen': ['Golf', 'Jetta', 'Passat', 'Tiguan', 'Atlas', 'Arteon', 'ID.4'],
    'Nissan': ['Altima', 'Sentra', 'Rogue', 'Pathfinder', 'Murano', 'Frontier', 'Titan', 'Leaf'],
    'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Palisade', 'Kona', 'Ioniq'],
    'Kia': ['Forte', 'Optima', 'Sorento', 'Sportage', 'Telluride', 'Soul', 'Stinger'],
    'Mazda': ['Mazda3', 'Mazda6', 'CX-30', 'CX-5', 'CX-9', 'MX-5 Miata'],
    'Subaru': ['Impreza', 'Legacy', 'Outback', 'Forester', 'Ascent', 'WRX', 'BRZ'],
    'Lexus': ['ES', 'IS', 'GS', 'LS', 'NX', 'RX', 'GX', 'LX'],
    'Acura': ['ILX', 'TLX', 'RDX', 'MDX', 'NSX'],
    'Infiniti': ['Q50', 'Q60', 'QX50', 'QX60', 'QX80'],
    'Cadillac': ['CT4', 'CT5', 'XT4', 'XT5', 'XT6', 'Escalade'],
    'Lincoln': ['Corsair', 'Nautilus', 'Aviator', 'Navigator'],
    'Buick': ['Encore', 'Envision', 'Enclave'],
    'GMC': ['Terrain', 'Acadia', 'Yukon', 'Sierra'],
    'Jeep': ['Compass', 'Cherokee', 'Grand Cherokee', 'Wrangler', 'Gladiator'],
    'Ram': ['1500', '2500', '3500', 'ProMaster'],
    'Dodge': ['Charger', 'Challenger', 'Durango'],
    'Chrysler': ['300', 'Pacifica'],
    'Volvo': ['S60', 'S90', 'XC40', 'XC60', 'XC90'],
    'Jaguar': ['XE', 'XF', 'F-PACE', 'E-PACE', 'I-PACE'],
    'Land Rover': ['Range Rover Evoque', 'Range Rover Velar', 'Range Rover Sport', 'Range Rover', 'Discovery'],
    'Porsche': ['911', 'Cayenne', 'Macan', 'Panamera', 'Taycan'],
    'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck'],
    'Genesis': ['G70', 'G80', 'G90', 'GV70', 'GV80'],
    'Alfa Romeo': ['Giulia', 'Stelvio'],
    'Maserati': ['Ghibli', 'Quattroporte', 'Levante'],
    'Ferrari': ['488', 'F8', 'Roma', 'Portofino', 'SF90'],
    'Lamborghini': ['Huracán', 'Aventador', 'Urus']
  };

  const vehicleTypes = [
    { value: 'sedan', label: 'Sedan' },
    { value: 'suv', label: 'SUV' },
    { value: 'hatchback', label: 'Hatchback' },
    { value: 'coupe', label: 'Coupe' },
    { value: 'convertible', label: 'Convertible' },
    { value: 'pickup', label: 'Pickup Truck' },
    { value: 'van', label: 'Van' },
    { value: 'motorcycle', label: 'Motorcycle' }
  ];

  const availableModels = formData.vehicle ? (modelsByBrand[formData.vehicle] || []) : [];

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
      // Reset model when vehicle brand changes
      ...(name === 'vehicle' && { model: '' })
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    console.log('Form submitted:', formData);
    alert(`Vehicle: ${formData.vehicle}, Model: ${formData.model}, Type: ${formData.type}`);
  };

  const handleReset = () => {
    setFormData({
      vehicle: '',
      model: '',
      type: ''
    });
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: '#f8fafc',
        padding: 2.5,
        overflow: 'auto',
        zIndex: 1000
      }}
    >
      <Container maxWidth="sm">
        <StyledPaper elevation={3}>
          <Typography
            variant="h4"
            component="h2"
            gutterBottom
            sx={{
              fontWeight: 700,
              color: '#1f2937',
              textAlign: 'center',
              mb: 4,
              letterSpacing: '-0.025em'
            }}
          >
            Select Vehicle
          </Typography>

          <Box component="form" onSubmit={handleSubmit}>
            <StyledFormControl fullWidth required>
              <InputLabel id="vehicle-brand-label">Vehicle Brand</InputLabel>
              <Select
                labelId="vehicle-brand-label"
                id="vehicle-brand-select"
                name="vehicle"
                value={formData.vehicle}
                label="Vehicle Brand"
                onChange={handleInputChange}
              >
                {vehicleBrands.map(brand => (
                  <MenuItem key={brand} value={brand}>
                    {brand}
                  </MenuItem>
                ))}
              </Select>
            </StyledFormControl>

            <StyledFormControl fullWidth required disabled={!formData.vehicle}>
              <InputLabel id="model-label">Model</InputLabel>
              <Select
                labelId="model-label"
                id="model-select"
                name="model"
                value={formData.model}
                label="Model"
                onChange={handleInputChange}
              >
                {!formData.vehicle ? (
                  <MenuItem value="" disabled>
                    Select a brand first
                  </MenuItem>
                ) : (
                  availableModels.map(model => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))
                )}
              </Select>
            </StyledFormControl>

            <StyledFormControl fullWidth required>
              <InputLabel id="vehicle-type-label">Vehicle Type</InputLabel>
              <Select
                labelId="vehicle-type-label"
                id="vehicle-type-select"
                name="type"
                value={formData.type}
                label="Vehicle Type"
                onChange={handleInputChange}
              >
                {vehicleTypes.map(type => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </StyledFormControl>

            <Box sx={{ display: 'flex', justifyContent: 'center'}}>
              <StyledButton
                type="submit"
                variant="contained"
                size="medium"
              >
                Submit
              </StyledButton>
            </Box>
          </Box>
        </StyledPaper>
      </Container>
    </Box>
  );
}

export default VehicleForm;