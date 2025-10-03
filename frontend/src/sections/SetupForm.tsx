import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Divider,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Container,
  Autocomplete,
  TextField,
  CircularProgress,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { DataGrid, GridToolbar } from '@mui/x-data-grid';
import { styled } from '@mui/material/styles';
import { getCodes, getNames } from 'country-list';

// Types
interface VehicleFormProps {
  vehicleBrands: { label: string; id: number }[];
}

interface FormData {
  vehicle: string;
  vehicleId: string;
  model: string;
  modelId: string;
  type: string;
  categoryFilter: string;
  manufacturingLocation: string;
  tariffShockCountry: string;
  tariffRate1: string;
  tariffRate2: string;
  tariffRate3: string;
  vatRate: string; // New VAT rate field
}

interface EngineOption {
  vehicleId: string;
  typeEngineName: string;
  powerPs: string;
  fuelType: string;
  bodyType: string;
  manufacturerName: string;
  modelName: string;
}

interface CategoryOption {
  id: string;
  name: string;
}

// Constants
const API_BASE_URL = 'http://127.0.0.1:8000';

// Default fallback locations if API fails
const DEFAULT_MANUFACTURING_LOCATIONS = [
  { id: 'germany', name: 'Germany' },
  { id: 'japan', name: 'Japan' },
  { id: 'china', name: 'China' },
  { id: 'south_korea', name: 'South Korea' },
  { id: 'usa', name: 'United States' },
  { id: 'italy', name: 'Italy' },
  { id: 'france', name: 'France' },
  { id: 'uk', name: 'United Kingdom' },
  { id: 'india', name: 'India' },
  { id: 'mexico', name: 'Mexico' },
];

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(6, 5),
  marginTop: theme.spacing(0),
  marginBottom: theme.spacing(3),
  marginLeft: 'auto',
  marginRight: 'auto',
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

// API functions
const fetchModels = async (vehicleId: string) => {
  const response = await fetch(`${API_BASE_URL}/manufacturers/models?id=${vehicleId}`);
  const data = await response.json();
  return data.models || [];
};

const fetchEngineTypes = async (vehicleId: string, modelId: string) => {
  const response = await fetch(
    `${API_BASE_URL}/manufacturers/models/engine_type?manufacturerId=${vehicleId}&modelSeriesId=${modelId}`
  );
  const data = await response.json();
  return data.modelTypes || [];
};

const fetchCategories = async (vehicleId: string, manufacturerId: string) => {
  const response = await fetch(
    `${API_BASE_URL}/manufacturers/models/engine_type/category_v3?vehicleId=${vehicleId}&manufacturerId=${manufacturerId}`
  );
  const data = await response.json();
  return data.categories || data;
};

const fetchCountries = async () => {
  try {
    // Get all country names and codes from country-list
    const countryCodes = getCodes();
    const countryNames = getNames();

    // Transform into our required format
    const transformedCountries = countryCodes.map((code, index) => ({
      id: code.toLowerCase(),
      name: countryNames[index]
    }));

    // Sort alphabetically by name
    transformedCountries.sort((a, b) => a.name.localeCompare(b.name));

    return transformedCountries;
  } catch (error) {
    console.error('Error creating countries list:', error);
    return DEFAULT_MANUFACTURING_LOCATIONS;
  }
};

// Main component
function VehicleForm({ vehicleBrands }: VehicleFormProps) {
  const navigate = useNavigate();

  // Form state
  const [formData, setFormData] = useState<FormData>({
    vehicle: '',
    vehicleId: '',
    model: '',
    modelId: '',
    type: '',
    categoryFilter: 'all',
    manufacturingLocation: '',
    tariffShockCountry: '',
    tariffRate1: '',
    tariffRate2: '',
    tariffRate3: '',
    vatRate: '', // Initialize VAT rate
  });

  // Data state
  const [models, setModels] = useState<{ modelId: number, modelName: string }[]>([]);
  const [engineOptions, setEngineOptions] = useState<EngineOption[]>([]);
  const [availableCategories, setAvailableCategories] = useState<CategoryOption[]>([]);
  const [manufacturingLocations, setManufacturingLocations] = useState<{ id: string, name: string }[]>([]);
  const [partsDataFile, setPartsDataFile] = useState<File | null>(null);
  const [articlesDataFile, setArticlesDataFile] = useState<File | null>(null);
  const [showProcessingDialog, setShowProcessingDialog] = useState(false);

  // Spreadsheet popup state
  const [openTariffGrid, setOpenTariffGrid] = useState(false);

  // Rows for the spreadsheet popup (seed with your countries if you like)
  type TariffRow = { id: string; countryName: string; tariffRate: number | '' };
  const [tariffRows, setTariffRows] = useState<TariffRow[]>([]);

  // Loading state
  const [loading, setLoading] = useState({
    models: false,
    engines: false,
    categories: false,
    countries: false,
    simulation: false,
  });

  // Error state
  const [errors, setErrors] = useState({
    models: null as string | null,
    engines: null as string | null,
  });

  // Load countries on component mount
  useEffect(() => {
    const loadCountries = async () => {
      setLoading(prev => ({ ...prev, countries: true }));
      try {
        const countries = await fetchCountries();
        setManufacturingLocations(countries);
      } catch (error) {
        console.error('Error loading countries:', error);
        const fallbackCountries = DEFAULT_MANUFACTURING_LOCATIONS;
        setManufacturingLocations(fallbackCountries);
      } finally {
        setLoading(prev => ({ ...prev, countries: false }));
      }
    };

    loadCountries();
  }, []);

  // Load models when vehicle changes
  useEffect(() => {
    if (!formData.vehicleId) return;

    const loadModels = async () => {
      setLoading(prev => ({ ...prev, models: true }));
      setErrors(prev => ({ ...prev, models: null }));
      setModels([]);

      try {
        const data = await fetchModels(formData.vehicleId);
        setModels(data);
        if (data.length === 0) {
          setErrors(prev => ({ ...prev, models: "No models found." }));
        }
      } catch (error) {
        setErrors(prev => ({ ...prev, models: "Failed to load models." }));
      } finally {
        setLoading(prev => ({ ...prev, models: false }));
      }
    };

    loadModels();
  }, [formData.vehicleId]);

  // Load engine types when model changes
  useEffect(() => {
    if (!formData.vehicleId || !formData.modelId) return;

    const loadEngines = async () => {
      setLoading(prev => ({ ...prev, engines: true }));
      setErrors(prev => ({ ...prev, engines: null }));
      setEngineOptions([]);

      try {
        const data = await fetchEngineTypes(formData.vehicleId, formData.modelId);
        setEngineOptions(data);
        if (data.length === 0) {
          setErrors(prev => ({ ...prev, engines: "No engine types found." }));
        }
      } catch (error) {
        setErrors(prev => ({ ...prev, engines: "Failed to load engine types." }));
      } finally {
        setLoading(prev => ({ ...prev, engines: false }));
      }
    };

    loadEngines();
  }, [formData.vehicleId, formData.modelId]);

  // Load categories when engine type is selected
  useEffect(() => {
    if (!formData.vehicleId || !formData.type) return;

    const selectedEngine = engineOptions.find(engine => engine.typeEngineName === formData.type);
    if (!selectedEngine) return;

    const loadCategories = async () => {
      setLoading(prev => ({ ...prev, categories: true }));

      try {
        const categories = await fetchCategories(selectedEngine.vehicleId, formData.vehicleId);
        const level1Categories: CategoryOption[] = Object.entries(categories).map(([id, category]: [string, any]) => ({
          id: id,
          name: category.text
        }));
        setAvailableCategories(level1Categories);
      } catch (error) {
        console.error('Error fetching categories:', error);
        setAvailableCategories([]);
      } finally {
        setLoading(prev => ({ ...prev, categories: false }));
      }
    };

    loadCategories();
  }, [formData.vehicleId, formData.type, engineOptions]);

  // Handlers
  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>, fileType: 'parts' | 'articles') => {
    const file = event.target.files?.[0];
    if (file && file.type === 'text/csv') {
      if (fileType === 'parts') {
        setPartsDataFile(file);
      } else {
        setArticlesDataFile(file);
      }
    } else if (file) {
      event.target.value = ''; // Reset the input
    }
  }, []);

  // Function to check if the form is ready for submission
  const isFormValid = useCallback(() => {
    return !!(
      formData.type &&
      formData.manufacturingLocation &&
      formData.tariffShockCountry &&
      formData.categoryFilter &&
      formData.tariffRate1 &&
      formData.tariffRate2 &&
      formData.tariffRate3 &&
      formData.vatRate &&
      partsDataFile &&
      articlesDataFile
    );
  }, [formData, partsDataFile, articlesDataFile]);

  const handleSubmit = useCallback(async (event?: React.FormEvent) => {
    if (event) event.preventDefault();

    const selectedEngine = engineOptions.find(engine => engine.typeEngineName === formData.type);
    if (!selectedEngine) {
      return;
    }

    if (!partsDataFile) {
      return;
    }

    if (!articlesDataFile) {
      return;
    }

    // Show immediate popup when user clicks Run Simulation
    setShowProcessingDialog(true);

    try {
      // Set simulation loading state
      setLoading(prev => ({ ...prev, simulation: true }));

      // Create FormData for file upload
      const formDataToSend = new FormData();

      // Add vehicle details
      formDataToSend.append('vehicle_details', JSON.stringify(selectedEngine));
      formDataToSend.append('category_filter', formData.categoryFilter);

      // Get category name
      const categoryName = formData.categoryFilter === 'all'
        ? 'Complete Vehicle'
        : availableCategories.find(cat => cat.id === formData.categoryFilter)?.name || 'Unknown Category';
      formDataToSend.append('category_name', categoryName);

      formDataToSend.append('manufacturing_location', formData.manufacturingLocation);
      formDataToSend.append('manufacturing_location_name', formData.manufacturingLocation);

      formDataToSend.append('tariff_shock_country', formData.tariffShockCountry);
      formDataToSend.append('tariff_shock_country_name', formData.tariffShockCountry);
      formDataToSend.append('tariff_rate_1', formData.tariffRate1);
      formDataToSend.append('tariff_rate_2', formData.tariffRate2);
      formDataToSend.append('tariff_rate_3', formData.tariffRate3);
      formDataToSend.append('vat_rate', formData.vatRate); // Add VAT rate to form data

      // Add files
      formDataToSend.append('parts_data_file', partsDataFile);
      formDataToSend.append('articles_data_file', articlesDataFile);

      // Add tariff data file if available
      if (tariffDataFile) {
        formDataToSend.append('tariff_data_file', tariffDataFile);
      }

      // Make POST request to run_report_generator endpoint
      const response = await fetch(`${API_BASE_URL}/run_report_generator`, {
        method: 'POST',
        body: formDataToSend,
      });

      // Process the response
      if (response.ok) {
        // Continue processing the response
        const result = await response.json();
        console.log('Simulation completed:', result);
        console.log('Form data submitted:', {
          vehicleDetails: selectedEngine,
          categoryFilter: formData.categoryFilter,
          manufacturingLocation: formData.manufacturingLocation,
          tariffShockCountry: formData.tariffShockCountry,
          tariffRate1: formData.tariffRate1,
          tariffRate2: formData.tariffRate2,
          tariffRate3: formData.tariffRate3,
          vatRate: formData.vatRate, // Log VAT rate
          partsDataFile: partsDataFile?.name,
          articlesDataFile: articlesDataFile?.name,
          tariffDataFile: tariffDataFile?.name
        });

        // You can navigate to results page or handle the response as needed
        // navigate('/simulation_results', { state: { results: result } });
      } else {
        const errorData = await response.json();
        console.error('Simulation failed:', errorData);
        alert(`Simulation failed: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error running simulation:', error);
      alert('Failed to run simulation. Please try again.');
    } finally {
      // Re-enable the button once the process is complete (success or failure)
      setLoading(prev => ({ ...prev, simulation: false }));
    }
  }, [engineOptions, formData, partsDataFile, articlesDataFile]);

  const handleReset = useCallback(() => {
    setFormData({
      vehicle: '',
      vehicleId: '',
      model: '',
      modelId: '',
      type: '',
      categoryFilter: 'all',
      manufacturingLocation: '',
      tariffShockCountry: '',
      tariffRate1: '',
      tariffRate2: '',
      tariffRate3: '',
      vatRate: '', // Reset VAT rate
    });
    setModels([]);
    setEngineOptions([]);
    setAvailableCategories([]);
    setPartsDataFile(null);
    setArticlesDataFile(null);
    // Reset file inputs if they exist
    const partsInput = document.getElementById('parts-data-upload') as HTMLInputElement;
    if (partsInput) partsInput.value = '';
    const articlesInput = document.getElementById('articles-data-upload') as HTMLInputElement;
    if (articlesInput) articlesInput.value = '';
  }, []);

  const renderSelectMenuItems = useCallback((
    loading: boolean,
    error: string | null,
    items: any[],
    emptyMessage: string,
    renderItem: (item: any, index: number) => React.ReactNode
  ) => {
    if (loading) return <MenuItem value="" disabled>Loading...</MenuItem>;
    if (error) return <MenuItem value="" disabled>{error}</MenuItem>;
    if (items.length === 0) return <MenuItem value="" disabled>{emptyMessage}</MenuItem>;
    return items.map(renderItem);
  }, []);

  const handleTariffRateChange = (field: 'tariffRate1' | 'tariffRate2' | 'tariffRate3') => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.value;
    // Allow empty string or valid numbers (including decimals)
    if (value === '' || /^\d*\.?\d*$/.test(value)) {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  // Handler for VAT rate change
  const handleVatRateChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    // Allow empty string or valid numbers (including decimals)
    if (value === '' || /^\d*\.?\d*$/.test(value)) {
      setFormData(prev => ({
        ...prev,
        vatRate: value
      }));
    }
  };

  // Columns (component scope, NOT inside JSX)

  const tariffColumns: import('@mui/x-data-grid').GridColDef[] = [
    {
      field: 'countryName',
      headerName: 'Country',
      editable: false,
      headerAlign: 'center',
      align: 'center',
      flex: 1,          // takes more space
      minWidth: 150,    // never shrink below this
    },
    {
      field: 'tariffRate',
      headerName: 'Tariff Rate (%)',
      type: 'number',
      editable: true,
      headerAlign: 'center',
      align: 'center',
      flex: 1,        // smaller proportion
      minWidth: 150,
    },
  ];

  // Row update handler (component scope)
  const handleProcessRowUpdate = (
    newRow: import('@mui/x-data-grid').GridRowModel,
    _oldRow: import('@mui/x-data-grid').GridRowModel
  ) => {
    if (
      newRow.tariffRate !== '' &&
      (Number.isNaN(Number(newRow.tariffRate)) || Number(newRow.tariffRate) < 0)
    ) {
      throw new Error('Tariff rate must be a non-negative number or blank.');
    }
    // Update the tariffRows state with the new row
    setTariffRows(prevRows =>
      prevRows.map(row => row.id === newRow.id ? newRow as TariffRow : row)
    );
    return newRow;
  };

  const handleRowUpdateError = (err: unknown) => {
    console.error(err);
    alert((err as Error).message);
  };

  // add a loader + temp id state
  const [loadingFindCountries, setLoadingFindCountries] = useState(false);
  const [countriesTempId, setCountriesTempId] = useState<string | null>(null);
  const [tariffDataFile, setTariffDataFile] = useState<File | null>(null);

  // Function to convert tariff data to CSV file
  const createTariffCsvFile = (tariffData: TariffRow[]): File => {
    // Create CSV content
    const headers = ['countryName', 'tariffRate'];
    const csvRows = [
      headers.join(','), // Header row
      ...tariffData.map(row => [
        `"${row.countryName}"`, // Wrap in quotes to handle country names with commas
        row.tariffRate === '' ? '' : row.tariffRate.toString()
      ].join(','))
    ];

    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    return new File([blob], 'tariff_data.csv', { type: 'text/csv' });
  };

  // call backend and populate rows
  const loadTariffRowsFromFindCountries = async () => {
    if (!partsDataFile || !articlesDataFile) {
      alert("Please upload both Parts and Articles CSVs first.");
      return;
    }

    const fd = new FormData();
    fd.append("parts_data_file", partsDataFile);
    fd.append("articles_data_file", articlesDataFile);

    try {
      setLoadingFindCountries(true);
      const res = await fetch(`${API_BASE_URL}/find_countries`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "find_countries failed");
      }
      const data: { temp_id: string; countries: string[] } = await res.json();

      // turn country names into DataGrid rows; leave tariffRate empty initially
      const rows = data.countries.map((name) => ({
        id: name.toLowerCase().replace(/\s+/g, "_"),
        countryName: name,
        tariffRate: "" as number | "",
      }));

      setCountriesTempId(data.temp_id);
      setTariffRows(rows);
      setOpenTariffGrid(true); // open the dialog after loading
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Could not load countries");
    } finally {
      setLoadingFindCountries(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <StyledPaper elevation={3}>
        <Typography variant="h5" component="h3" gutterBottom sx={{ fontWeight: 700, color: '#1f2937', textAlign: 'center', mb: 4, fontSize: '1.75rem' }}>
          Select Vehicle & Configure Report
        </Typography>

      <Box sx={{ mx: -5 }}>
        <Divider sx={{ mt: 4.0, mb: 6 }} />
      </Box>

    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{ maxWidth: 880, mx: 'auto' }}   // optional: widen the form
    >
      <Box
        sx={{
          display: 'grid',
          rowGap: 0,
          columnGap: 2,
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          mb: 2,
        }}
      >
        {/* Vehicle Selection */}
        <Box sx={{ gridColumn: '1 / -1', mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Vehicle Selection
          </Typography>
        </Box>

          {/* Vehicle Brand */}
          <StyledFormControl fullWidth required>
            <Autocomplete
              options={vehicleBrands}
              getOptionLabel={(option) => option.label}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              value={vehicleBrands.find(b => b.id === parseInt(formData.vehicleId)) || null}
              onChange={(event, newValue) => {
                setFormData(prev => ({
                  ...prev,
                  vehicleId: newValue?.id.toString() || '',
                  vehicle: newValue?.label || '',
                  model: '',
                  modelId: '',
                  type: '',
                }));
              }}
              disableClearable
              renderOption={(props, option) => <li {...props} key={option.id}>{option.label}</li>}
              renderInput={(params) => <TextField {...params} label="Vehicle Brand" required />}
            />
          </StyledFormControl>

          {/* Model */}
          <StyledFormControl fullWidth required>
            <Autocomplete
              options={models}
              getOptionLabel={(option) => option.modelName}
              isOptionEqualToValue={(option, value) => option.modelId === value.modelId}
              value={models.find(m => m.modelName === formData.model) || null}
              onChange={(event, newValue) => {
                setFormData(prev => ({
                  ...prev,
                  model: newValue?.modelName || '',
                  modelId: newValue?.modelId.toString() || '',
                  type: '',
                  categoryFilter: 'all',
                }));
              }}
              disabled={!formData.vehicleId || loading.models}
              loading={loading.models}
              disableClearable
              renderOption={(props, option) => <li {...props} key={option.modelId}>{option.modelName}</li>}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Model"
                  required
                  error={!!errors.models}
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {loading.models ? <CircularProgress color="inherit" size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
              noOptionsText={
                !formData.vehicleId ? 'Select a brand to load models'
                : loading.models ? 'Loading models...'
                : errors.models ? errors.models
                : 'No models found'
              }
            />
          </StyledFormControl>

          <StyledFormControl fullWidth required disabled={!formData.modelId || loading.engines}>
            <InputLabel id="engine-type-label">Engine Type</InputLabel>
            <Select
              labelId="engine-type-label"
              id="engine-type-select"
              name="type"
              value={formData.type}
              label="Engine Type"
              onChange={(e) => {
                setFormData(prev => ({
                  ...prev,
                  type: e.target.value,
                  categoryFilter: 'all',
                }));
                setAvailableCategories([]);
              }}
            >
              {renderSelectMenuItems(
                loading.engines,
                errors.engines,
                engineOptions,
                'Select a model to load engine types',
                (engine, index) => (
                  <MenuItem key={index} value={engine.typeEngineName}>
                    {engine.typeEngineName} — {engine.powerPs} PS, {engine.fuelType}, {engine.bodyType}
                  </MenuItem>
                )
              )}
            </Select>
          </StyledFormControl>

          <StyledFormControl fullWidth required disabled={!formData.type}>
            <InputLabel id="category-filter-label">Parts Category</InputLabel>
            <Select
              labelId="category-filter-label"
              id="category-filter-select"
              name="categoryFilter"
              value={formData.categoryFilter}
              label="Parts Category"
              onChange={(e) => setFormData(prev => ({ ...prev, categoryFilter: e.target.value }))}
              required
            >
              <MenuItem value="all">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography sx={{ fontWeight: 600 }}>Complete Vehicle</Typography>
                  <Chip label="All Parts" size="small" color="primary" variant="outlined" />
                </Box>
              </MenuItem>
              {loading.categories ? (
                <MenuItem value="" disabled>Loading categories...</MenuItem>
              ) : availableCategories.length === 0 ? (
                <MenuItem value="" disabled>Select an engine type to load categories</MenuItem>
              ) : (
                availableCategories.map((category) => (
                  <MenuItem key={category.id} value={category.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography>{category.name}</Typography>
                      <Chip
                        label={category.id}
                        size="small"
                        variant="filled"
                        color="default"
                        sx={{ fontSize: '0.7rem', height: '20px' }}
                      />
                    </Box>
                  </MenuItem>
                ))
              )}
            </Select>
          </StyledFormControl>
        </Box>

        {/* --- Manufacturing Location & VAT rate section --- */}
        <Box sx={{ gridColumn: '1 / -1', mt: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 3 }}>
            Manufacturing Location & VAT rate
          </Typography>

          <Box
            sx={{
              display: 'grid',
              gap: 2,
              gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
            }}
          >
            {/* Manufacturing Location */}
            <StyledFormControl fullWidth required>
              <TextField
                label="Manufacturing Location"
                value={formData.manufacturingLocation}
                onChange={(e) => {
                  setFormData((prev) => ({
                    ...prev,
                    manufacturingLocation: e.target.value,
                  }));
                }}
                required
                placeholder="e.g. United Kingdom"
                type="text"
              />
            </StyledFormControl>

            {/* VAT Rate */}
            <StyledFormControl fullWidth required>
              <TextField
                label="VAT Rate (%)"
                value={formData.vatRate}
                onChange={handleVatRateChange}
                required
                placeholder="e.g. 20"
                type="text"
                inputProps={{
                  pattern: '^\\d*\\.?\\d*$',
                  inputMode: 'decimal',
                }}
              />
              {/* If you prefer a % prefix:
              InputProps={{ startAdornment: <InputAdornment position="start">%</InputAdornment> }}
              */}
            </StyledFormControl>
          </Box>
        </Box>

        {/* --- Tariff Shock configuration --- */}
        <Box
          sx={{
            display: 'grid',
            rowGap: 0,
            columnGap: 2,
            gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
            mb: 2,
          }}
        >
          {/* Subheading spanning both columns */}
          <Box sx={{ gridColumn: '1 / -1', mt: 2, mb: 3  }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              Tariff Simulation Configuration
            </Typography>
          </Box>

            <StyledFormControl fullWidth required>
              <TextField
                label="Tariff Shock Simulation: Country"
                value={formData.tariffShockCountry}
                onChange={(e) => {
                  setFormData((prev) => ({
                    ...prev,
                    tariffShockCountry: e.target.value,
                  }));
                }}
                required
                placeholder="e.g. Japan"
                type="text"
              />
            </StyledFormControl>

            <StyledFormControl fullWidth required>
              <TextField
                label="Tariff Shock Simulation: Rate 1 (%)"
                value={formData.tariffRate1}
                onChange={handleTariffRateChange('tariffRate1')}
                required
                placeholder="e.g. 25"
                type="text"
                inputProps={{
                  pattern: '^\\d*\\.?\\d*$',
                  inputMode: 'decimal'
                }}
              />
            </StyledFormControl>

            <StyledFormControl fullWidth required>
              <TextField
                label="Tariff Shock Simulation: Rate 2 (%)"
                value={formData.tariffRate2}
                onChange={handleTariffRateChange('tariffRate2')}
                required
                placeholder="e.g. 50"
                type="text"
                inputProps={{
                  pattern: '^\\d*\\.?\\d*$',
                  inputMode: 'decimal'
                }}
              />
            </StyledFormControl>

            <StyledFormControl fullWidth required>
              <TextField
                label="Tariff Shock Simulation: Rate 3 (%)"
                value={formData.tariffRate3}
                onChange={handleTariffRateChange('tariffRate3')}
                required
                placeholder="e.g. 75"
                type="text"
                inputProps={{
                  pattern: '^\\d*\\.?\\d*$',
                  inputMode: 'decimal'
                }}
              />
            </StyledFormControl>
        </Box>

        {/* --- Upload Data --- */}
        <Box sx={{ gridColumn: '1 / -1', mt: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 3 }}>
            Upload Data
          </Typography>

            {/* Upload Parts */}
            <StyledFormControl fullWidth required>
              <Box sx={{
                border: '2px dashed #e5e7eb',
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                backgroundColor: '#f9fafb',
                transition: 'all 0.2s ease',
                '&:hover': { borderColor: '#d1d5db', backgroundColor: '#f3f4f6' }
              }}>
                <input
                  accept=".csv"
                  id="parts-data-upload"
                  type="file"
                  onChange={(e) => handleFileUpload(e, 'parts')}
                  style={{ display: 'none' }}
                  required
                />
                <label htmlFor="parts-data-upload">
                  <Button variant="outlined" component="span" sx={{ textTransform: 'none' }}>
                    Upload Parts Data (CSV) *
                  </Button>
                </label>

                {partsDataFile && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" sx={{ color: '#059669', fontWeight: 500 }}>
                      ✓ {partsDataFile.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      {(partsDataFile.size / 1024).toFixed(2)} KB
                    </Typography>
                  </Box>
                )}

                <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#9ca3af' }}>
                  Required: Upload CSV file with parts data
                </Typography>
              </Box>
            </StyledFormControl>

            {/* Upload Articles */}
            <StyledFormControl fullWidth required>
              <Box sx={{
                border: '2px dashed #e5e7eb',
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                backgroundColor: '#f9fafb',
                transition: 'all 0.2s ease',
                '&:hover': { borderColor: '#d1d5db', backgroundColor: '#f3f4f6' }
              }}>
                <input
                  accept=".csv"
                  id="articles-data-upload"
                  type="file"
                  onChange={(e) => handleFileUpload(e, 'articles')}
                  style={{ display: 'none' }}
                  required
                />
                <label htmlFor="articles-data-upload">
                  <Button variant="outlined" component="span" sx={{ textTransform: 'none' }}>
                    Upload Articles Data (CSV) *
                  </Button>
                </label>

                {articlesDataFile && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" sx={{ color: '#059669', fontWeight: 500 }}>
                      ✓ {articlesDataFile.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      {(articlesDataFile.size / 1024).toFixed(2)} KB
                    </Typography>
                  </Box>
                )}

                <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#9ca3af' }}>
                  Required: Upload CSV file with articles data
                </Typography>
              </Box>
            </StyledFormControl>
        </Box>

          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
            <StyledButton
              onClick={handleReset}
              variant="outlined"
              size="medium"
            >
              Reset
            </StyledButton>
            <StyledButton
              variant="contained"
              size="medium"
              onClick={loadTariffRowsFromFindCountries}
              disabled={loadingFindCountries || loading.simulation || !isFormValid()}
            >
              {loadingFindCountries ? "Loading..." : loading.simulation ? "Processing..." : "Configure Tariff Rates & Generate Report"}
            </StyledButton>
          </Box>
        </Box>

        <Dialog
          open={openTariffGrid}
          onClose={() => setOpenTariffGrid(false)}
          PaperProps={{
            sx: {
              width: '50vw',
              height: '70vh',
              maxWidth: 'none',
              display: 'flex',
              flexDirection: 'column',
            },
          }}
        >
          <DialogTitle sx={{ textAlign: 'center', px: 3 }}>Add Tariff Rates</DialogTitle>
          <DialogContent dividers sx={{ height: 520 }}>
          <DataGrid
            rows={tariffRows}
            columns={tariffColumns}
            // Demo-style UX niceties
            disableRowSelectionOnClick

            // Pagination like the demo
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            pageSizeOptions={[5, 10, 25, 50]}

            // Keep your existing toolbar + edit handlers
            slots={{ toolbar: GridToolbar }}
            processRowUpdate={handleProcessRowUpdate}
            onProcessRowUpdateError={handleRowUpdateError}

            // Nice compact look + subtle header background
            density="compact"
            sx={{
              border: 0,
              '& .MuiDataGrid-columnHeaders': {
                backgroundColor: 'rgba(0,0,0,0.04)',
                fontWeight: 600,
              },
              '& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within': {
                outline: 'none',
              },
              '& .MuiDataGrid-row:hover': {
                backgroundColor: 'rgba(0,0,0,0.02)',
              },
            }}
          />
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setOpenTariffGrid(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={
                !isFormValid() ||
                loading.simulation ||
                tariffRows.length === 0 ||
                tariffRows.some(row => row.tariffRate === '' || row.tariffRate === null || row.tariffRate === undefined)
              }
              onClick={async () => {
                // Convert tariff data to CSV file
                if (tariffRows.length > 0) {
                  const csvFile = createTariffCsvFile(tariffRows);
                  setTariffDataFile(csvFile);
                }
                setOpenTariffGrid(false);

                // Trigger the full simulation
                await handleSubmit();
              }}
            >
              {loading.simulation ? (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={20} color="inherit" />
                  Processing...
                </Box>
              ) : (
                'Generate Report'
              )}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Processing Dialog */}
        <Dialog
          open={showProcessingDialog}
          onClose={() => setShowProcessingDialog(false)}
          maxWidth="sm"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: 3,
              p: 1
            }
          }}
        >
          <DialogTitle sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            pb: 2,
            fontSize: '1.5rem',
            fontWeight: 600
          }}>
            <Box sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              color: '#1976d2'
            }}>
              <CircularProgress size={28} thickness={4} />
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#1976d2' }}>
                Report Being Generated
              </Typography>
            </Box>
          </DialogTitle>

          <DialogContent sx={{ pb: 3 }}>
            <Typography variant="body1" sx={{ mb: 2, fontSize: '1.1rem', lineHeight: 1.6 }}>
              Your simulation has been initiated and is now processing in the background.
            </Typography>

            <Box sx={{
              backgroundColor: '#f8f9fa',
              border: '1px solid #e9ecef',
              borderRadius: 2,
              p: 2.5,
              mb: 2
            }}>
              <Typography variant="body2" sx={{
                fontWeight: 600,
                color: '#495057',
                mb: 1,
                fontSize: '0.95rem'
              }}>
                Next Steps:
              </Typography>
              <Typography variant="body2" sx={{
                color: '#6c757d',
                lineHeight: 1.5,
                fontSize: '0.9rem'
              }}>
                • Please return to your <strong>terminal/console</strong> to monitor progress<br/>
                • The process will take approximately <strong>20 minutes</strong> to complete<br/>
                • You can close this dialog and the processing will continue
              </Typography>
            </Box>

            <Typography variant="body2" sx={{
              color: '#6c757d',
              fontStyle: 'italic',
              textAlign: 'center'
            }}>
              The "Generate Report" button will be re-enabled once processing is finished.
            </Typography>
          </DialogContent>

          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setShowProcessingDialog(false)}
              variant="contained"
              sx={{
                borderRadius: 2,
                px: 4,
                py: 1,
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '0.95rem'
              }}
            >
              Got it
            </Button>
          </DialogActions>
        </Dialog>
      </StyledPaper>
    </Container>
  );
}

export default VehicleForm;