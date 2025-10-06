import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Divider,
  Paper,
  Typography,
  FormControl,
  Button,
  Container,
  TextField,
  CircularProgress,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { DataGrid, GridToolbar, useGridApiRef } from '@mui/x-data-grid';
import { styled } from '@mui/material/styles';

// Types
interface VehicleFormProps {}

interface FormData {
  vehicle: string;
  model: string;
  categoryFilter: string;
  manufacturingLocation: string;
  tariffShockCountry: string;
  tariffRate1: string;
  tariffRate2: string;
  tariffRate3: string;
  vatRate: string;
}

// Constants
const API_BASE_URL = 'http://127.0.0.1:8000';

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

// API functions - removed fetchModels, fetchEngineTypes, fetchCategories since we're using text inputs now

// Main component
function VehicleForm({}: VehicleFormProps) {
  const navigate = useNavigate();
  const apiRef = useGridApiRef();

  // Form state
  const [formData, setFormData] = useState<FormData>({
    vehicle: '',
    model: '',
    categoryFilter: '',
    manufacturingLocation: '',
    tariffShockCountry: '',
    tariffRate1: '',
    tariffRate2: '',
    tariffRate3: '',
    vatRate: '',
  });

  // Data state
  const [partsDataFile, setPartsDataFile] = useState<File | null>(null);
  const [articlesDataFile, setArticlesDataFile] = useState<File | null>(null);
  const [tariffDataFile, setTariffDataFile] = useState<File | null>(null);
  const [showProcessingDialog, setShowProcessingDialog] = useState(false);

  // Spreadsheet popup state
  const [openTariffGrid, setOpenTariffGrid] = useState(false);

  // Rows for the spreadsheet popup
  type TariffRow = { id: string; countryName: string; tariffRate: number | '' };
  const [tariffRows, setTariffRows] = useState<TariffRow[]>([]);
  const [availableCountries, setAvailableCountries] = useState<string[]>([]);

  // Loading state
  const [loading, setLoading] = useState({
    simulation: false,
  });

  // Additional state for error handling
  const [loadingFindCountries, setLoadingFindCountries] = useState(false);
  const [countriesTempId, setCountriesTempId] = useState<string | null>(null);
  const [showCountryErrorDialog, setShowCountryErrorDialog] = useState(false);
  const [countryErrorMessage, setCountryErrorMessage] = useState({ enteredCountry: '', availableCountries: [] as string[] });
  const [showProductIdErrorDialog, setShowProductIdErrorDialog] = useState(false);
  const [productIdErrors, setProductIdErrors] = useState<string[]>([]);

  // No need to load data from API anymore - all fields are text inputs

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
      formData.vehicle &&
      formData.model &&
      formData.categoryFilter &&
      formData.manufacturingLocation &&
      formData.tariffShockCountry &&
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

      // Create vehicle details object from text inputs
      const vehicleDetails = {
        manufacturerName: formData.vehicle,
        modelName: formData.model,
      };

      // Add vehicle details
      formDataToSend.append('vehicle_details', JSON.stringify(vehicleDetails));
      formDataToSend.append('category_filter', formData.categoryFilter);

      // Use the category filter text as the category name
      formDataToSend.append('category_name', formData.categoryFilter);

      formDataToSend.append('manufacturing_location', formData.manufacturingLocation);
      formDataToSend.append('manufacturing_location_name', formData.manufacturingLocation);

      formDataToSend.append('tariff_shock_country', formData.tariffShockCountry);
      formDataToSend.append('tariff_shock_country_name', formData.tariffShockCountry);
      formDataToSend.append('tariff_rate_1', formData.tariffRate1);
      formDataToSend.append('tariff_rate_2', formData.tariffRate2);
      formDataToSend.append('tariff_rate_3', formData.tariffRate3);
      formDataToSend.append('vat_rate', formData.vatRate);

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
          vehicleDetails: vehicleDetails,
          categoryFilter: formData.categoryFilter,
          manufacturingLocation: formData.manufacturingLocation,
          tariffShockCountry: formData.tariffShockCountry,
          tariffRate1: formData.tariffRate1,
          tariffRate2: formData.tariffRate2,
          tariffRate3: formData.tariffRate3,
          vatRate: formData.vatRate,
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
  }, [formData, partsDataFile, articlesDataFile, tariffDataFile]);

  const handleReset = useCallback(() => {
    setFormData({
      vehicle: '',
      model: '',
      categoryFilter: '',
      manufacturingLocation: '',
      tariffShockCountry: '',
      tariffRate1: '',
      tariffRate2: '',
      tariffRate3: '',
      vatRate: '',
    });
    setPartsDataFile(null);
    setArticlesDataFile(null);
    // Reset file inputs if they exist
    const partsInput = document.getElementById('parts-data-upload') as HTMLInputElement;
    if (partsInput) partsInput.value = '';
    const articlesInput = document.getElementById('articles-data-upload') as HTMLInputElement;
    if (articlesInput) articlesInput.value = '';
  }, []);

  // Removed renderSelectMenuItems since we're using text inputs now

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

  // Handle Enter key to move to next row
  const handleCellKeyDown = useCallback((
    params: import('@mui/x-data-grid').GridCellParams,
    event: React.KeyboardEvent
  ) => {
    if (event.key === 'Enter' && !event.shiftKey && params.field === 'tariffRate') {
      const currentRowIndex = tariffRows.findIndex(row => row.id === params.id);
      if (currentRowIndex < tariffRows.length - 1) {
        const nextRow = tariffRows[currentRowIndex + 1];
        // Move to next row after a small delay to allow the current edit to commit
        setTimeout(() => {
          if (apiRef.current) {
            apiRef.current.setCellFocus(nextRow.id, 'tariffRate');
            apiRef.current.startCellEditMode({ id: nextRow.id, field: 'tariffRate' });
          }
        }, 100);
      }
    }
  }, [tariffRows, apiRef]);

  // State declarations moved to top of component

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

    if (!formData.tariffShockCountry) {
      alert("Please enter a Tariff Shock Simulation Country first.");
      return;
    }

    // Validate productIds before sending to backend
    try {
      const partsText = await partsDataFile.text();
      const articlesText = await articlesDataFile.text();

      // Parse CSV files
      const partsLines = partsText.split('\n').filter(line => line.trim());
      const articlesLines = articlesText.split('\n').filter(line => line.trim());

      // Get productIds from parts data (skip header)
      const partsProductIds = new Set<string>();
      for (let i = 1; i < partsLines.length; i++) {
        const columns = partsLines[i].split(',');
        if (columns[0]) {
          partsProductIds.add(columns[0].trim());
        }
      }

      // Check all productIds in articles data exist in parts data
      const missingProductIds = new Set<string>();
      for (let i = 1; i < articlesLines.length; i++) {
        const columns = articlesLines[i].split(',');
        const productId = columns[0]?.trim();
        if (productId && !partsProductIds.has(productId)) {
          missingProductIds.add(productId);
        }
      }

      if (missingProductIds.size > 0) {
        setProductIdErrors(Array.from(missingProductIds));
        setShowProductIdErrorDialog(true);
        return;
      }
    } catch (error) {
      console.error('Error validating productIds:', error);
      alert('Failed to validate product IDs. Please check your CSV files.');
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
      setAvailableCountries(data.countries);

      // Validate that the tariff shock country exists in the articles data
      const tariffCountryLower = formData.tariffShockCountry.toLowerCase().trim();
      const countryExists = data.countries.some(
        (country: string) => country.toLowerCase().trim() === tariffCountryLower
      );

      if (!countryExists) {
        setCountryErrorMessage({
          enteredCountry: formData.tariffShockCountry,
          availableCountries: data.countries
        });
        setShowCountryErrorDialog(true);
        return;
      }

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
            <TextField
              label="Vehicle Brand"
              value={formData.vehicle}
              onChange={(e) => {
                setFormData((prev) => ({
                  ...prev,
                  vehicle: e.target.value,
                }));
              }}
              required
              placeholder="e.g. Toyota"
              type="text"
            />
          </StyledFormControl>

          {/* Model */}
          <StyledFormControl fullWidth required>
            <TextField
              label="Model"
              value={formData.model}
              onChange={(e) => {
                setFormData((prev) => ({
                  ...prev,
                  model: e.target.value,
                }));
              }}
              required
              placeholder="e.g. RAV4"
              type="text"
            />
          </StyledFormControl>

          {/* Parts Category */}
          <StyledFormControl fullWidth required>
            <TextField
              label="Parts Category"
              value={formData.categoryFilter}
              onChange={(e) => {
                setFormData((prev) => ({
                  ...prev,
                  categoryFilter: e.target.value,
                }));
              }}
              required
              placeholder="e.g. Braking System or Complete Vehicle"
              type="text"
            />
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
              borderRadius: 3,
              p: 1
            },
          }}
        >
          <DialogTitle sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
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
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#1976d2', fontSize: '1.25rem' }}>
                Add Tariff Rates
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent dividers sx={{ height: 520, pb: 3 }}>
            <DataGrid
              apiRef={apiRef}
              rows={tariffRows}
              columns={tariffColumns}
              disableRowSelectionOnClick
              initialState={{
                pagination: { paginationModel: { pageSize: 10 } },
              }}
              pageSizeOptions={[5, 10, 25, 50]}
              slots={{ toolbar: GridToolbar }}
              processRowUpdate={handleProcessRowUpdate}
              onProcessRowUpdateError={handleRowUpdateError}
              onCellKeyDown={handleCellKeyDown}
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
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setOpenTariffGrid(false)}
              sx={{
                borderRadius: 2,
                px: 3,
                py: 1,
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '0.95rem'
              }}
            >
              Cancel
            </Button>
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
              sx={{
                borderRadius: 2,
                px: 4,
                py: 1,
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '0.95rem'
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

        {/* Country Validation Error Dialog */}
        <Dialog
          open={showCountryErrorDialog}
          onClose={() => setShowCountryErrorDialog(false)}
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
              color: '#d32f2f'
            }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#d32f2f', fontSize: '1.25rem' }}>
                Country Not Found
              </Typography>
            </Box>
          </DialogTitle>

          <DialogContent sx={{ pb: 3 }}>
            <Typography variant="body1" sx={{ mb: 2, fontSize: '1.1rem', lineHeight: 1.6 }}>
              The tariff shock country <strong>"{countryErrorMessage.enteredCountry}"</strong> was not found in the articles data.
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
                Available countries in your data:
              </Typography>
              <Box sx={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                mt: 1.5
              }}>
                {countryErrorMessage.availableCountries.map((country) => (
                  <Chip
                    key={country}
                    label={country}
                    size="small"
                    sx={{
                      backgroundColor: '#e3f2fd',
                      color: '#1976d2',
                      fontWeight: 500
                    }}
                  />
                ))}
              </Box>
            </Box>

            <Typography variant="body2" sx={{
              color: '#6c757d',
              fontStyle: 'italic',
              textAlign: 'center'
            }}>
              Please update the country name to match one from the list above.
            </Typography>
          </DialogContent>

          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setShowCountryErrorDialog(false)}
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

        {/* Product ID Validation Error Dialog */}
        <Dialog
          open={showProductIdErrorDialog}
          onClose={() => setShowProductIdErrorDialog(false)}
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
              color: '#d32f2f'
            }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#d32f2f', fontSize: '1.25rem' }}>
                Product ID Mismatch
              </Typography>
            </Box>
          </DialogTitle>

          <DialogContent sx={{ pb: 3 }}>
            <Typography variant="body1" sx={{ mb: 2, fontSize: '1.1rem', lineHeight: 1.6 }}>
              The following product IDs from the articles data were not found in the parts data:
            </Typography>

            <Box sx={{
              backgroundColor: '#f8f9fa',
              border: '1px solid #e9ecef',
              borderRadius: 2,
              p: 2.5,
              mb: 2,
              maxHeight: '300px',
              overflowY: 'auto'
            }}>
              <Typography variant="body2" sx={{
                fontWeight: 600,
                color: '#495057',
                mb: 1,
                fontSize: '0.95rem'
              }}>
                Missing Product IDs ({productIdErrors.length}):
              </Typography>
              <Box sx={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                mt: 1.5
              }}>
                {productIdErrors.map((productId) => (
                  <Chip
                    key={productId}
                    label={productId}
                    size="small"
                    sx={{
                      backgroundColor: '#ffebee',
                      color: '#c62828',
                      fontWeight: 500
                    }}
                  />
                ))}
              </Box>
            </Box>

            <Typography variant="body2" sx={{
              color: '#6c757d',
              fontStyle: 'italic',
              textAlign: 'center'
            }}>
              Please ensure all product IDs in the articles data exist in the parts data.
            </Typography>
          </DialogContent>

          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setShowProductIdErrorDialog(false)}
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