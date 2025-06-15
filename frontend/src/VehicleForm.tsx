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
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip
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

const StyledTablePaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
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

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  fontWeight: 600,
  backgroundColor: theme.palette.grey[50],
  borderBottom: `2px solid ${theme.palette.divider}`,
}));

interface VehicleData {
  id: number;
  brand: string;
  model: string;
  engineType: string;
  powerPs: string;
  fuelType: string;
  bodyType: string;
  dateAdded: string;
}

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

  // Table state
  const [vehicleData, setVehicleData] = useState<VehicleData[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

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

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Check if a vehicle has already been added
    if (vehicleData.length >= 1) {
      alert('Only one vehicle can be added. Please clear the existing vehicle first.');
      return;
    }

    setLoadingCategories(true);

    try {
      // Find the selected engine details
      const selectedEngine = engineOptions.find(engine => engine.typeEngineName === formData.type);

      // Get vehicleId from the selected engine or model data
      const vehicleId = selectedEngine?.vehicleId || formData.modelId; // Adjust based on your API structure

      // Fetch category data
      const categoryResponse = await fetch(
        `http://127.0.0.1:8000/manufacturers/models/engine_type/category_v3?vehicleId=${vehicleId}&manufacturerId=${formData.vehicleId}`
      );

      if (!categoryResponse.ok) {
        throw new Error('Failed to fetch category data');
      }

      const categoryResult = await categoryResponse.json();

      // Process the hierarchical category data into flat structure for table display
      const processCategories = (categories, parentPath = '') => {
        const flatCategories = [];

        Object.entries(categories).forEach(([id, category]: [string, any]) => {
          const currentPath = parentPath ? `${parentPath} > ${category.text}` : category.text;

          // Add main category
          flatCategories.push({
            id: Date.now() + Math.random(), // Unique ID for table
            categoryId: id,
            categoryName: category.text,
            fullPath: currentPath,
            level: parentPath.split(' > ').length,
            hasChildren: Object.keys(category.children || {}).length > 0,
            vehicleBrand: formData.vehicle,
            vehicleModel: formData.model,
            engineType: formData.type
          });

          // Recursively process children
          if (category.children && Object.keys(category.children).length > 0) {
            flatCategories.push(...processCategories(category.children, currentPath));
          }
        });

        return flatCategories;
      };

      const flatCategories = processCategories(categoryResult.categories || categoryResult);
      setCategoryData(flatCategories); // Replace instead of append

      // Create new vehicle entry
      const newVehicle: VehicleData = {
        id: 1, // Always ID 1 since only one vehicle allowed
        brand: formData.vehicle,
        model: formData.model,
        engineType: formData.type,
        powerPs: selectedEngine?.powerPs || '',
        fuelType: selectedEngine?.fuelType || '',
        bodyType: selectedEngine?.bodyType || '',
        dateAdded: new Date().toLocaleDateString()
      };

      // Set vehicle data (only one allowed)
      setVehicleData([newVehicle]);

      console.log('Form submitted:', formData);
      console.log('Categories fetched:', flatCategories.length);
      alert(`Vehicle added with ${flatCategories.length} bill of materials items: ${formData.vehicle} ${formData.model}`);

    } catch (error) {
      console.error('Error fetching categories:', error);
      alert('Failed to fetch bill of materials data. Please try again.');
    } finally {
      setLoadingCategories(false);
    }
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

  const handleClearTable = () => {
    setVehicleData([]);
    setCategoryData([]);
    setPage(0);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getFuelTypeColor = (fuelType: string) => {
    switch (fuelType?.toLowerCase()) {
      case 'petrol':
      case 'gasoline':
        return 'primary';
      case 'diesel':
        return 'secondary';
      case 'electric':
        return 'success';
      case 'hybrid':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#f8fafc', padding: 2.5, overflow: 'auto', zIndex: 1000 }}>
      <Container maxWidth="lg">
        {/* Vehicle Selection Form */}
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

            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
              <StyledButton
                type="submit"
                variant="contained"
                size="medium"
                disabled={loadingCategories || vehicleData.length >= 1}
              >
                {loadingCategories ? 'Loading Bill of Materials...' : vehicleData.length >= 1 ? 'Vehicle Already Added' : 'Add Vehicle'}
              </StyledButton>
              <StyledButton onClick={handleReset} variant="outlined" size="medium">
                Reset Form
              </StyledButton>
            </Box>
          </Box>
        </StyledPaper>

        {/* Vehicle Data Table */}
        <StyledTablePaper elevation={3}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h5" component="h3" sx={{ fontWeight: 700, color: '#1f2937' }}>
              Selected Vehicle {vehicleData.length > 0 && `(1/1)`}
            </Typography>
            {vehicleData.length > 0 && (
              <StyledButton onClick={handleClearTable} variant="outlined" color="error" size="small">
                Clear Vehicle & Bill of Materials
              </StyledButton>
            )}
          </Box>

          {vehicleData.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No vehicle selected yet. Use the form above to add your vehicle.
              </Typography>
            </Box>
          ) : (
            <>
              <TableContainer>
                <Table sx={{ minWidth: 650 }} aria-label="vehicle data table">
                  <TableHead>
                    <TableRow>
                      <StyledTableCell>Brand</StyledTableCell>
                      <StyledTableCell>Model</StyledTableCell>
                      <StyledTableCell>Engine Type</StyledTableCell>
                      <StyledTableCell>Power (PS)</StyledTableCell>
                      <StyledTableCell>Fuel Type</StyledTableCell>
                      <StyledTableCell>Body Type</StyledTableCell>
                      <StyledTableCell>Date Added</StyledTableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {vehicleData.map((vehicle) => (
                      <TableRow key={vehicle.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                        <TableCell sx={{ fontWeight: 600 }}>{vehicle.brand}</TableCell>
                        <TableCell sx={{ fontWeight: 500 }}>{vehicle.model}</TableCell>
                        <TableCell>{vehicle.engineType}</TableCell>
                        <TableCell>{vehicle.powerPs}</TableCell>
                        <TableCell>
                          <Chip
                            label={vehicle.fuelType}
                            color={getFuelTypeColor(vehicle.fuelType)}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>{vehicle.bodyType}</TableCell>
                        <TableCell>{vehicle.dateAdded}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </StyledTablePaper>

        {/* Bill of Materials Table */}
        {categoryData.length > 0 && (
          <StyledTablePaper elevation={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h5" component="h3" sx={{ fontWeight: 700, color: '#1f2937' }}>
                Bill of Materials ({categoryData.length} items)
              </Typography>
            </Box>

            <TableContainer>
              <Table sx={{ minWidth: 650 }} aria-label="bill of materials table">
                <TableHead>
                  <TableRow>
                    <StyledTableCell>Item ID</StyledTableCell>
                    <StyledTableCell>Item Name</StyledTableCell>
                    <StyledTableCell>Full Path</StyledTableCell>
                    <StyledTableCell>Level</StyledTableCell>
                    <StyledTableCell>Has Children</StyledTableCell>
                    <StyledTableCell>Vehicle</StyledTableCell>
                    <StyledTableCell>Engine Type</StyledTableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {categoryData
                    .slice(0, 50) // Limit display to first 50 for performance
                    .map((category) => (
                      <TableRow key={category.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                        <TableCell component="th" scope="row" sx={{ fontWeight: 600 }}>
                          {category.categoryId}
                        </TableCell>
                        <TableCell sx={{
                          paddingLeft: `${category.level * 20 + 16}px`,
                          fontWeight: category.level === 0 ? 600 : 400
                        }}>
                          {category.categoryName}
                        </TableCell>
                        <TableCell sx={{ fontSize: '0.875rem', color: 'text.secondary' }}>
                          {category.fullPath}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={`Level ${category.level}`}
                            color={category.level === 0 ? 'primary' : category.level === 1 ? 'secondary' : 'default'}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={category.hasChildren ? 'Yes' : 'No'}
                            color={category.hasChildren ? 'success' : 'default'}
                            size="small"
                            variant="filled"
                          />
                        </TableCell>
                        <TableCell>{category.vehicleBrand} {category.vehicleModel}</TableCell>
                        <TableCell>{category.engineType}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>

            {categoryData.length > 50 && (
              <Box sx={{ mt: 2, p: 2, backgroundColor: 'info.light', borderRadius: 1 }}>
                <Typography variant="body2" color="info.contrastText">
                  Showing first 50 of {categoryData.length} bill of materials items.
                  Consider implementing pagination for better performance.
                </Typography>
              </Box>
            )}
          </StyledTablePaper>
        )}
      </Container>
    </Box>
  );
}

export default VehicleForm;