import React, { useEffect, useState } from 'react';
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
  Grid,
  Autocomplete,
  TextField
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

interface VehicleFormProps {
  vehicleBrands: { label: string; id: number }[];
}

function VehicleForm({ vehicleBrands }: VehicleFormProps) {
  const [formData, setFormData] = useState({
    vehicle: '',
    vehicleId: '',
    model: '',
    modelId: '',
    type: '',
  });

  const [models, setModels] = useState<{ modelId: number, modelName: string }[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  const [engineOptions, setEngineOptions] = useState<any[]>([]);
  const [loadingEngines, setLoadingEngines] = useState(false);
  const [engineError, setEngineError] = useState<string | null>(null);

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

  // Fetch models when vehicleId changes
  useEffect(() => {
    if (formData.vehicleId) {
      setLoadingModels(true);
      setModels([]);
      setModelError(null);

      fetch(`http://127.0.0.1:8000/manufacturers/models?id=${formData.vehicleId}`)
        .then(res => res.json())
        .then(data => {
          if (data.models) {
            setModels(data.models);
          } else {
            setModelError("No models found.");
          }
        })
        .catch(() => {
          setModelError("Failed to load models.");
        })
        .finally(() => setLoadingModels(false));
    }
  }, [formData.vehicleId]);

  useEffect(() => {
  if (formData.vehicleId && formData.modelId) {
    setLoadingEngines(true);
    setEngineOptions([]);
    setEngineError(null);

    fetch(`http://127.0.0.1:8000/manufacturers/models/engine_type?manufacturerId=${formData.vehicleId}&modelSeriesId=${formData.modelId}`)
      .then(res => res.json())
      .then(data => {
        if (data.modelTypes) {
          setEngineOptions(data.modelTypes);
        } else {
          setEngineError("No engine types found.");
        }
      })
      .catch(() => {
        setEngineError("Failed to load engine types.");
      })
      .finally(() => setLoadingEngines(false));
  }
}, [formData.vehicleId, formData.modelId]);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
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
      vehicleId: '',
      model: '',
      modelId: '',
      type: ''
    });
    setModels([]);
    setEngineOptions([]);
  };

  return (
    <Box sx={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#f8fafc', padding: 2.5, overflow: 'auto', zIndex: 1000 }}>
      <Container maxWidth="sm">
        <StyledPaper elevation={3}>
          <Typography variant="h4" component="h2" gutterBottom sx={{ fontWeight: 700, color: '#1f2937', textAlign: 'center', mb: 4 }}>
            Select Vehicle
          </Typography>

          <Box component="form" onSubmit={handleSubmit}>
            <StyledFormControl fullWidth required>
              <Autocomplete
                options={vehicleBrands}
                getOptionLabel={(option) => option.label}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                value={vehicleBrands.find(b => b.id === formData.vehicleId) || null}
                onChange={(event, newValue) => {
                  setFormData(prev => ({
                    ...prev,
                    vehicleId: newValue?.id || '',
                    vehicle: newValue?.label || '',
                    model: ''
                  }));
                }}
                disableClearable
                renderOption={(props, option) => (
                  <li {...props} key={option.id}>{option.label}</li>
                )}
                renderInput={(params) => (
                  <TextField {...params} label="Vehicle Brand" required />
                )}
              />
            </StyledFormControl>

            <StyledFormControl fullWidth required disabled={!formData.vehicleId || loadingModels}>
              <InputLabel id="model-label">Model</InputLabel>
                <Select
                  labelId="model-label"
                  id="model-select"
                  name="model"
                  value={formData.model}
                  label="Model"
                  onChange={(e) => {
                    const selectedModel = models.find((m) => m.modelName === e.target.value);
                    setFormData(prev => ({
                      ...prev,
                      model: selectedModel?.modelName || '',
                      modelId: selectedModel?.modelId || ''
                    }));
                  }}
                >
                  {loadingModels ? (
                    <MenuItem value="" disabled>Loading models...</MenuItem>
                  ) : modelError ? (
                    <MenuItem value="" disabled>{modelError}</MenuItem>
                  ) : models.length === 0 ? (
                    <MenuItem value="" disabled>Select a brand to load models</MenuItem>
                  ) : (
                    models.map((model) => (
                      <MenuItem key={model.modelId} value={model.modelName}>
                        {model.modelName}
                      </MenuItem>
                    ))
                  )}
                </Select>
            </StyledFormControl>

            <StyledFormControl fullWidth required disabled={!formData.modelId || loadingEngines}>
              <InputLabel id="engine-type-label">Engine Type</InputLabel>
              <Select
                labelId="engine-type-label"
                id="engine-type-select"
                name="type"
                value={formData.type}
                label="Engine Type"
                onChange={handleInputChange}
              >
                {loadingEngines ? (
                  <MenuItem value="" disabled>Loading engine types...</MenuItem>
                ) : engineError ? (
                  <MenuItem value="" disabled>{engineError}</MenuItem>
                ) : engineOptions.length === 0 ? (
                  <MenuItem value="" disabled>Select a model to load engine types</MenuItem>
                ) : (
                  engineOptions.map((engine, index) => (
                    <MenuItem key={index} value={engine.typeEngineName}>
                      {engine.typeEngineName} — {engine.powerPs} PS, {engine.fuelType}, {engine.bodyType}
                    </MenuItem>
                  ))
                )}
              </Select>
            </StyledFormControl>

            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <StyledButton type="submit" variant="contained" size="medium">
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