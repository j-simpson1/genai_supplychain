import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Header from "../components/Header";
import { MainLayout } from "../layouts/MainLayout";
import {
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

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
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

  const handleBack = () => {
    navigate(-1);
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1" fontWeight="bold">
            Model Configuration
          </Typography>

          <StyledButton
            variant="outlined"
            onClick={handleBack}
          >
            Back
          </StyledButton>
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
              <Typography variant="body2" color="textSecondary">Fuel Type</Typography>
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
                <StyledFormControl sx={{ width: 350 }}>
                  <InputLabel id="country-impacted-label">Country Impacted</InputLabel>
                  <Select
                    labelId="country-impacted-label"
                    id="country-impacted-select"
                    value={country}
                    label="Country Impacted"
                    onChange={handleCountryChange}
                  >
                    <MenuItem value="usa">United States</MenuItem>
                    <MenuItem value="uk">United Kingdom</MenuItem>
                    <MenuItem value="france">France</MenuItem>
                  </Select>
                </StyledFormControl>
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

        {/* Next/Save Buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4, gap: 2 }}>
          <StyledButton variant="outlined">
            Save Configuration
          </StyledButton>
          <StyledButton variant="contained">
            Continue
          </StyledButton>
        </Box>
      </Container>
    </MainLayout>
  );
};

export default ModelConfiguration;