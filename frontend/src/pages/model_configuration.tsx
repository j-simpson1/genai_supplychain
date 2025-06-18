import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Header from "../components/Header";
import { MainLayout } from "../layouts/MainLayout";
import {
  Autocomplete,
  Box,
  Typography,
  Paper,
  Container,
  Tabs,
  Tab,
  Button,
  Divider,
  Grid,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { getNames } from 'country-list';

const countryNames = getNames();

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  borderRadius: 12,
  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
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

const StyledTextField = styled(TextField)(({ theme }) => ({
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
  borderRadius: 8,
  padding: theme.spacing(1, 3),
  fontWeight: 600,
  textTransform: 'none'
}));

const ModelConfiguration = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { vehicleDetails, partsData, categoryData } = location.state || {};
  const [tabValue, setTabValue] = useState(0);
  const [scenarioType, setScenarioType] = useState('');
  const [country, setCountry] = useState('');
  const [tariffRate, setTariffRate] = useState('');
  const [manufacturerLocation, setManufacturerLocation] = useState('');
  const [inflationRate, setInflationRate] = useState('3');
  const [dispatchCost, setDispatchCost] = useState('');
  const [alternativeSupplier1, setAlternativeSupplier1] = useState('');
  const [alternativeSupplier1Country, setAlternativeSupplier1Country] = useState('');

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleScenarioTypeChange = (event) => {
    const newScenarioType = event.target.value;
    setScenarioType(newScenarioType);

    // Clear country and tariff rate when scenario type changes
    if (newScenarioType !== 'tariff_adjustment') {
      setCountry('');
      setTariffRate('');
    }
  };

  const handleCountryChange = (event) => {
    setCountry(event.target.value);
  };

  const handleTariffRateChange = (event) => {
    const value = event.target.value;
    // Only allow numbers and decimal point
    if (/^\d*\.?\d*$/.test(value) || value === '') {
      setTariffRate(value);
    }
  };

  const handleManufacturerLocationChange = (event) => {
    setManufacturerLocation(event.target.value);
  };

  const handleInflationRateChange = (event) => {
    const value = event.target.value;
    // Only allow numbers and decimal point
    if (/^\d*\.?\d*$/.test(value) || value === '') {
      setInflationRate(value);
    }
  };

  const handleDispatchCostChange = (event) => {
    const value = event.target.value;
    // Only allow numbers and decimal point
    if (/^\d*\.?\d*$/.test(value) || value === '') {
      setDispatchCost(value);
    }
  };

  const handleAlternativeSupplier1Change = (event) => {
    setAlternativeSupplier1(event.target.value);
  };

  const handleAlternativeSupplier1CountryChange = (event) => {
    setAlternativeSupplier1Country(event.target.value);
  };

  const handleBack = () => {
    navigate(-1);
  };

  const handleRunSimulation = () => {
  navigate('/output', {
    state: {
      vehicleDetails,
      partsData,
      categoryData,
      scenarioType,
      country: country.toLowerCase(),
      tariffRate,
      manufacturerLocation,
      inflationRate,
      dispatchCost,
      alternativeSupplier1,
      alternativeSupplier1Country
    }
  });
};

  // Check if data is available
  if (!vehicleDetails) {
    return (
      <MainLayout>
        <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
          <Typography variant="h5" color="error" gutterBottom>
            No vehicle data available
          </Typography>
          <Typography variant="body1" color="textSecondary" paragraph>
            Please select a vehicle in the previous page first.
          </Typography>
          <StyledButton
            variant="contained"
            onClick={handleBack}
            sx={{ mt: 2 }}
          >
            Go Back
          </StyledButton>
        </Container>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        {/* Page Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" component="h1" fontWeight="bold">
            Model Configuration
          </Typography>
        </Box>

        {/* Vehicle Details Card */}
        <StyledPaper>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            Vehicle Information
          </Typography>

          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6} md={4}>
              <Typography variant="body2" color="textSecondary">Manufacturer</Typography>
              <Typography variant="body1" fontWeight="medium">{vehicleDetails.manufacturerName}</Typography>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Typography variant="body2" color="textSecondary">Model</Typography>
              <Typography variant="body1" fontWeight="medium">{vehicleDetails.modelName}</Typography>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Typography variant="body2" color="textSecondary">Vehicle ID</Typography>
              <Typography variant="body1" fontWeight="medium">{vehicleDetails.vehicleId}</Typography>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Typography variant="body2" color="textSecondary">Engine Type</Typography>
              <Typography variant="body1" fontWeight="medium">{vehicleDetails.typeEngineName}</Typography>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Typography variant="body2" color="textSecondary">Fuel Type</Typography>
              <Typography variant="body1" fontWeight="medium">
                <Chip
                  label={vehicleDetails.fuelType}
                  size="small"
                  color={vehicleDetails.fuelType?.toLowerCase() === 'electric' ? 'success' : 'primary'}
                />
              </Typography>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Typography variant="body2" color="textSecondary">Body Type</Typography>
              <Typography variant="body1" fontWeight="medium">{vehicleDetails.bodyType}</Typography>
            </Grid>
          </Grid>
        </StyledPaper>

        {/* Configuration Tabs */}
        <StyledPaper>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="Parts Summary" />
              <Tab label="Configuration Options" />
            </Tabs>
          </Box>

          {/* Tab Content */}
          <Box sx={{ py: 3 }}>
            {tabValue === 0 && (
              <Box>
                <Typography variant="h6" gutterBottom>Parts Summary</Typography>
                <Typography variant="body1" paragraph>
                  This vehicle has {partsData?.length || 0} compatible parts across {categoryData?.length || 0} categories.
                </Typography>

                <Grid container spacing={2}>
                  {partsData?.slice(0, 6).map((part) => (
                    <Grid item xs={12} sm={6} md={4} key={part.categoryId}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2" color="primary" gutterBottom>
                            {part.categoryName}
                          </Typography>
                          <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.8rem' }}>
                            {part.fullPath}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>

                {partsData?.length > 6 && (
                  <Box sx={{ mt: 2, textAlign: 'center' }}>
                    <Typography variant="body2" color="textSecondary">
                      + {partsData.length - 6} more parts
                    </Typography>
                  </Box>
                )}
              </Box>
            )}

            {tabValue === 1 && (
              <Box>
                <Typography variant="h6" gutterBottom>Configuration Options</Typography>
                <Typography variant="body1">
                  Configure model options and parameters for this vehicle.
                </Typography>

                <Box sx={{ mt: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="textSecondary">
                    Configuration features will be implemented soon.
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        </StyledPaper>

        {/* Scenario Configurator Card */}
        <StyledPaper>
          <Typography variant="h6" gutterBottom fontWeight="bold" sx={{ mb: 3 }}>
            Scenario Configurator
          </Typography>

          {/* Scenario Type Dropdown */}
          <Box sx={{ mb: 0 }}>
            <StyledFormControl sx={{ width: 350 }}>
              <InputLabel id="scenario-type-label">Scenario Type</InputLabel>
              <Select
                labelId="scenario-type-label"
                id="scenario-type-select"
                value={scenarioType}
                label="Scenario Type"
                onChange={handleScenarioTypeChange}
              >
                <MenuItem value="tariff_adjustment">Tariff Adjustment</MenuItem>
                <MenuItem value="high_inflation">High Inflation</MenuItem>
                <MenuItem value="recession">Recession</MenuItem>
              </Select>
            </StyledFormControl>
          </Box>

          {/* Conditionally render Country Impacted and Tariff Rate fields */}
          {scenarioType === 'tariff_adjustment' && (
            <>
              {/* Country Impacted Dropdown */}
              <Box sx={{ mb: 0 }}>
                <Autocomplete
                  id="country-impacted-autocomplete"
                  options={countryNames}
                  value={country}
                  onChange={(event, newValue) => setCountry(newValue || '')}
                  renderInput={(params) => (
                    <StyledTextField
                      {...params}
                      label="Country Impacted"
                      placeholder="Select or type a country"
                    />
                  )}
                  sx={{ width: 350 }}
                />
              </Box>

              {/* Tariff Rate Text Field */}
              <Box sx={{ mb: 0 }}>
                <StyledTextField
                  id="tariff-rate"
                  label="Tariff Rate (%)"
                  value={tariffRate}
                  onChange={handleTariffRateChange}
                  sx={{ width: 350 }}
                  placeholder="Enter tariff rate"
                  inputProps={{
                    inputMode: 'decimal',
                    pattern: '[0-9]*[.]?[0-9]*'
                  }}
                />
              </Box>
            </>
          )}
        </StyledPaper>

        {/* Model Parameter Card */}
        <StyledPaper>
          <Typography variant="h6" gutterBottom fontWeight="bold" sx={{ mb: 3 }}>
            Model Parameters
          </Typography>

          {/* Global Inflation Rate Text Field */}
          <Box sx={{ mb: 0 }}>
            <StyledTextField
              id="global-inflation-rate"
              label="Global Inflation Rate (%)"
              value={inflationRate}
              onChange={handleInflationRateChange}
              sx={{ width: 350 }}
              placeholder="Enter global inflation rate"
              inputProps={{
                inputMode: 'decimal',
                pattern: '[0-9]*[.]?[0-9]*'
              }}
            />
          </Box>

          {/* Dispatch Cost Text Field */}
          <Box sx={{ mb: 0 }}>
            <StyledTextField
              id="dispatch-cost"
              label="Dispatch Cost (optional)"
              value={dispatchCost}
              onChange={handleDispatchCostChange}
              sx={{ width: 350 }}
              placeholder="Enter dispatch cost"
              inputProps={{
                inputMode: 'decimal',
                pattern: '[0-9]*[.]?[0-9]*'
              }}
            />
          </Box>
        </StyledPaper>

        {/* Alternative Suppliers Card */}
        <StyledPaper>
          <Typography variant="h6" gutterBottom fontWeight="bold" sx={{ mb: 3 }}>
            Alternative Suppliers
          </Typography>

          {/* Alternative Supplier 1 Dropdown */}
          <Box sx={{ mb: 0 }}>
            <StyledFormControl sx={{ width: 350 }}>
              <InputLabel id="alternative-supplier-1-label">Alternative Supplier 1</InputLabel>
              <Select
                labelId="alternative-supplier-1-label"
                id="alternative-supplier-1-select"
                value={alternativeSupplier1}
                label="Alternative Supplier 1"
                onChange={handleAlternativeSupplier1Change}
              >
                <MenuItem value="bosch">Bosch</MenuItem>
                <MenuItem value="denso">Denso</MenuItem>
                <MenuItem value="zf_friedrichshafen">ZF Friedrichshafen</MenuItem>
                <MenuItem value="continental">Continental</MenuItem>
                <MenuItem value="magna">Magna International</MenuItem>
              </Select>
            </StyledFormControl>
          </Box>

          {/* Alternative Supplier 1 Country Dropdown */}
          <Box sx={{ mb: 0 }}>
            <StyledFormControl sx={{ width: 350 }}>
              <InputLabel id="alternative-supplier-1-country-label">Alternative Supplier 1 Country</InputLabel>
              <Select
                labelId="alternative-supplier-1-country-label"
                id="alternative-supplier-1-country-select"
                value={alternativeSupplier1Country}
                label="Alternative Supplier 1 Country"
                onChange={handleAlternativeSupplier1CountryChange}
              >
                <MenuItem value="uk">United Kingdom</MenuItem>
                <MenuItem value="usa">United States</MenuItem>
                <MenuItem value="france">France</MenuItem>
                <MenuItem value="germany">Germany</MenuItem>
                <MenuItem value="japan">Japan</MenuItem>
                <MenuItem value="china">China</MenuItem>
              </Select>
            </StyledFormControl>
          </Box>
        </StyledPaper>

        {/* Next/Back Buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4, gap: 2 }}>
          <StyledButton variant="outlined" onClick={handleBack}>
            Back
          </StyledButton>
          <StyledButton variant="contained" onClick={handleRunSimulation}>
            Run Simulation
          </StyledButton>
        </Box>
      </Container>
    </MainLayout>
  );
};

export default ModelConfiguration;