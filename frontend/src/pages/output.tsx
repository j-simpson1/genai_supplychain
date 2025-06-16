import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Header from "../components/Header";
import { MainLayout } from "../layouts/MainLayout";
import {
  Box,
  Typography,
  Paper,
  Container,
  Grid,
  Button,
  CircularProgress,
  Divider,
  Chip,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { styled } from '@mui/material/styles';

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  borderRadius: 12,
  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
}));

const StyledButton = styled(Button)(({ theme }) => ({
  borderRadius: 8,
  padding: theme.spacing(1, 3),
  fontWeight: 600,
  textTransform: 'none'
}));

const OutputPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [simulationResults, setSimulationResults] = useState(null);

  // Extract data passed from model_configuration
  const {
    vehicleDetails,
    partsData,
    categoryData,
    scenarioType,
    country,
    tariffRate,
    manufacturerLocation,
    inflationRate,
    dispatchCost,
    alternativeSupplier1,
    alternativeSupplier1Country
  } = location.state || {};

  useEffect(() => {
    // Simulate loading time for results calculation
    const timer = setTimeout(() => {
      // In a real app, you might fetch results from an API here
      const mockResults = {
        costImpact: parseFloat(tariffRate || '0') * 1.5,
        supplierChanges: alternativeSupplier1 ? 2 : 0,
        affectedParts: Math.floor((partsData?.length || 0) * 0.35),
        totalCostChange: parseFloat(inflationRate || '0') * 2.8 + parseFloat(tariffRate || '0') * 1.5
      };

      setSimulationResults(mockResults);
      setIsLoading(false);
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  const handleBack = () => {
    navigate(-1);
  };

  // Check if data is available
  if (!vehicleDetails) {
    return (
      <MainLayout>
        <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
          <Typography variant="h5" color="error" gutterBottom>
            No simulation data available
          </Typography>
          <Typography variant="body1" color="textSecondary" paragraph>
            Please configure a simulation first.
          </Typography>
          <StyledButton
            variant="contained"
            onClick={() => navigate('/model-configuration')}
            sx={{ mt: 2 }}
          >
            Go to Configuration
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
            Simulation Results
          </Typography>
          <Typography variant="subtitle1" color="textSecondary">
            {scenarioType === 'tariff_adjustment' && 'Tariff Adjustment Scenario'}
            {scenarioType === 'high_inflation' && 'High Inflation Scenario'}
            {scenarioType === 'recession' && 'Recession Scenario'}
          </Typography>
        </Box>

        {/* Loading State */}
        {isLoading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 8 }}>
            <CircularProgress size={60} />
            <Typography variant="h6" sx={{ mt: 3 }}>
              Calculating simulation results...
            </Typography>
          </Box>
        ) : (
          <>
            {/* Summary Card */}
            <StyledPaper>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Simulation Summary
              </Typography>

              <Grid container spacing={3} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="textSecondary">Vehicle</Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {vehicleDetails.manufacturerName} {vehicleDetails.modelName}
                  </Typography>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="textSecondary">Scenario</Typography>
                  <Typography variant="body1" fontWeight="medium">
                    <Chip
                      label={scenarioType?.replace('_', ' ')}
                      size="small"
                      color={
                        scenarioType === 'tariff_adjustment' ? 'primary' :
                        scenarioType === 'high_inflation' ? 'warning' : 'error'
                      }
                    />
                  </Typography>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="textSecondary">Manufacturer Location</Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {manufacturerLocation}
                  </Typography>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    {scenarioType === 'tariff_adjustment' ? 'Tariff Rate' : 'Inflation Rate'}
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {scenarioType === 'tariff_adjustment' ? tariffRate : inflationRate}%
                  </Typography>
                </Grid>
              </Grid>
            </StyledPaper>

            {/* Results Card */}
            <StyledPaper>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Impact Analysis
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Typography variant="h5" color="primary" gutterBottom>
                        Cost Impact
                      </Typography>
                      <Typography variant="h3" fontWeight="bold">
                        {simulationResults.totalCostChange.toFixed(2)}%
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                        Estimated change in total vehicle cost
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Typography variant="h5" color="primary" gutterBottom>
                        Component Impact
                      </Typography>
                      <Typography variant="h3" fontWeight="bold">
                        {simulationResults.affectedParts}
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                        Number of affected parts out of {partsData?.length || 0} total
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <TableContainer sx={{ mt: 4 }}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Category</TableCell>
                      <TableCell>Price Impact</TableCell>
                      <TableCell>Supply Risk</TableCell>
                      <TableCell>Alternative Solutions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {categoryData?.slice(0, 5).map((category, index) => (
                      <TableRow key={index}>
                        <TableCell>{category?.categoryName || `Category ${index + 1}`}</TableCell>
                        <TableCell>{(Math.random() * 10).toFixed(2)}%</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={index % 3 === 0 ? "High" : index % 3 === 1 ? "Medium" : "Low"}
                            color={index % 3 === 0 ? "error" : index % 3 === 1 ? "warning" : "success"}
                          />
                        </TableCell>
                        <TableCell>{index % 2 === 0 ? "Available" : "Limited"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </StyledPaper>

            {/* Supplier Analysis */}
            {alternativeSupplier1 && (
              <StyledPaper>
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  Alternative Supplier Analysis
                </Typography>
                <Typography variant="body1" paragraph>
                  Switching to {alternativeSupplier1?.replace('_', ' ')} from {alternativeSupplier1Country}
                  could mitigate approximately {(Math.random() * 30).toFixed(1)}% of the cost impact.
                </Typography>
              </StyledPaper>
            )}
          </>
        )}

        {/* Back Button */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4 }}>
          <StyledButton variant="contained" onClick={handleBack}>
            Back to Model Configuration
          </StyledButton>
        </Box>
      </Container>
    </MainLayout>
  );
};

export default OutputPage;