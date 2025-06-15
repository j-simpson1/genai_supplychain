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
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Tabs,
  Tab
} from '@mui/material';
import { SimpleTreeView } from '@mui/x-tree-view/SimpleTreeView';
import { TreeItem } from '@mui/x-tree-view/TreeItem';
import { styled } from '@mui/material/styles';

// Custom styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(7, 5),
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

const StyledTreeView = styled(SimpleTreeView)(({ theme }) => ({
  flexGrow: 1,
  maxWidth: '100%',
  padding: theme.spacing(1),
}));

const StyledTreeItem = styled(TreeItem)(({ theme }) => ({
  '& .MuiTreeItem-content': {
    padding: theme.spacing(0.5, 1),
    margin: theme.spacing(0.2, 0),
    borderRadius: theme.spacing(1),
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
    '&.Mui-selected': {
      backgroundColor: theme.palette.primary.light,
      '&:hover': {
        backgroundColor: theme.palette.primary.light,
      },
    },
  },
  '& .MuiTreeItem-label': {
    fontSize: '0.875rem',
    fontWeight: 500,
  },
}));

const StyledTableHead = styled(TableHead)(({ theme }) => ({
  '& .MuiTableCell-head': {
    backgroundColor: theme.palette.grey[50],
    fontWeight: 600,
    fontSize: '0.875rem',
    borderBottom: `2px solid ${theme.palette.divider}`,
  },
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

interface PartItem {
  categoryId: string;
  categoryName: string;
  fullPath: string;
  level: number;
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
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [partsData, setPartsData] = useState<PartItem[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [selectedVehicleDetails, setSelectedVehicleDetails] = useState<any>(null);

  // Table pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Tab state
  const [tabValue, setTabValue] = useState(0);

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

  // Extract parts (leaf nodes) from hierarchical data
  const extractParts = (categories, parentPath = '') => {
    const parts = [];

    Object.entries(categories).forEach(([id, category]: [string, any]) => {
      const currentPath = parentPath ? `${parentPath} > ${category.text}` : category.text;
      const hasChildren = Object.keys(category.children || {}).length > 0;

      if (!hasChildren) {
        // This is a leaf node (part)
        parts.push({
          categoryId: id,
          categoryName: category.text,
          fullPath: currentPath,
          level: parentPath.split(' > ').filter(Boolean).length
        });
      } else {
        // Recursively process children
        parts.push(...extractParts(category.children, currentPath));
      }
    });

    return parts;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Check if a vehicle has already been added
    if (selectedVehicleDetails) {
      alert('Only one vehicle can be added. Please clear the existing vehicle first.');
      return;
    }

    setLoadingCategories(true);

    try {
      // Find the selected engine details from the engineOptions
      const selectedEngine = engineOptions.find(engine => engine.typeEngineName === formData.type);

      if (!selectedEngine) {
        throw new Error('Selected engine details not found');
      }

      // Set the selected vehicle details from the engine data
      setSelectedVehicleDetails(selectedEngine);

      // Fetch category data using the vehicleId from the selected engine
      const categoryResponse = await fetch(
        `http://127.0.0.1:8000/manufacturers/models/engine_type/category_v3?vehicleId=${selectedEngine.vehicleId}&manufacturerId=${formData.vehicleId}`
      );

      if (!categoryResponse.ok) {
        throw new Error('Failed to fetch category data');
      }

      const categoryResult = await categoryResponse.json();

      // Process the hierarchical category data for TreeView
      const processCategories = (categories, parentPath = '') => {
        const treeData = [];

        Object.entries(categories).forEach(([id, category]: [string, any]) => {
          const currentPath = parentPath ? `${parentPath} > ${category.text}` : category.text;
          const hasChildren = Object.keys(category.children || {}).length > 0;

          const categoryItem = {
            id: id,
            categoryId: id,
            categoryName: category.text,
            fullPath: currentPath,
            level: parentPath.split(' > ').length,
            hasChildren: hasChildren,
            children: hasChildren ? processCategories(category.children, currentPath) : [],
            vehicleBrand: formData.vehicle,
            vehicleModel: formData.model,
            engineType: formData.type
          };

          treeData.push(categoryItem);
        });

        return treeData;
      };

      const treeData = processCategories(categoryResult.categories || categoryResult);
      setCategoryData(treeData);

      // Extract parts for the table
      const parts = extractParts(categoryResult.categories || categoryResult);
      setPartsData(parts);

      console.log('Form submitted:', formData);
      console.log('Vehicle details:', selectedEngine);
      console.log('Categories fetched:', treeData.length);
      console.log('Parts extracted:', parts.length);
      alert(`Vehicle added with bill of materials tree structure`);

    } catch (error) {
      console.error('Error fetching data:', error);
      alert('Failed to fetch vehicle or bill of materials data. Please try again.');
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
    setSelectedVehicleDetails(null);
    setCategoryData([]);
    setPartsData([]);
    setPage(0);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
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

  const renderTreeItems = (items: any[]) => {
    return items.map((item) => (
      <StyledTreeItem
        key={item.categoryId}
        itemId={item.categoryId}
        label={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5 }}>
            <Typography
              variant="body2"
              sx={{
                fontWeight: item.hasChildren ? 600 : 400,
                flexGrow: 1
              }}
            >
              {item.categoryName}
            </Typography>

            <Chip
              label={item.hasChildren ? 'Category' : 'Part'}
              size="small"
              variant="outlined"
              color={item.hasChildren ? 'info' : 'success'}
              sx={{ fontSize: '0.75rem', height: '24px' }}
            />

            <Chip
              label={item.categoryId}
              size="small"
              variant="filled"
              color="default"
              sx={{ fontSize: '0.7rem', height: '20px' }}
            />
          </Box>
        }
      >
        {item.children && item.children.length > 0 && renderTreeItems(item.children)}
      </StyledTreeItem>
    ));
  };

  const getTotalItemCount = (items: any[]): number => {
    let count = items.length;
    items.forEach(item => {
      if (item.children && item.children.length > 0) {
        count += getTotalItemCount(item.children);
      }
    });
    return count;
  };

  // Get paginated parts data
  const paginatedParts = partsData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Box sx={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#f8fafc', padding: 2.5, overflow: 'auto', zIndex: 1000 }}>
      <Container maxWidth="lg">
        {/* Vehicle Selection Form */}
        <StyledPaper elevation={3}>
          <Typography variant="h4" component="h2" gutterBottom sx={{ fontWeight: 700, color: '#1f2937', textAlign: 'center', mb: 4 }}>
            Select Vehicle
          </Typography>

          <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 400, mx: 'auto' }}>
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
                disabled={loadingCategories || selectedVehicleDetails !== null}
              >
                {loadingCategories ? 'Loading Bill of Materials...' : selectedVehicleDetails ? 'Vehicle Already Added' : 'Add Vehicle'}
              </StyledButton>
              <StyledButton onClick={handleReset} variant="outlined" size="medium">
                Reset Form
              </StyledButton>
            </Box>
          </Box>
        </StyledPaper>

        {/* Bill of Materials - Combined Section */}
        {selectedVehicleDetails && (
          <StyledTablePaper elevation={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
              <Typography variant="h5" component="h3" sx={{ fontWeight: 700, color: '#1f2937', mt: 1.0 }}>
                Bill of Materials
              </Typography>
              <StyledButton onClick={handleClearTable} variant="outlined" color="error" size="small">
                Clear Bill of Materials
              </StyledButton>
            </Box>

            {/* Vehicle Information */}
            <Box sx={{
              backgroundColor: '#f8fafc',
              borderRadius: 2,
              p: 3,
              mb: 3,
              border: '1px solid #e2e8f0',
              fontFamily: 'monospace',
              fontSize: '14px',
              lineHeight: 1.6
            }}>
              <Box sx={{ mb: 1 }}>
                <Typography component="span" sx={{ fontWeight: 600, color: '#374151' }}>
                  Vehicle ID:
                </Typography>
                <Typography component="span" sx={{ ml: 1, color: '#1f2937' }}>
                  {selectedVehicleDetails.vehicleId}
                </Typography>
              </Box>

              <Box sx={{ mb: 1 }}>
                <Typography component="span" sx={{ fontWeight: 600, color: '#374151' }}>
                  Manufacturer:
                </Typography>
                <Typography component="span" sx={{ ml: 1, color: '#1f2937' }}>
                  {selectedVehicleDetails.manufacturerName}
                </Typography>
              </Box>

              <Box sx={{ mb: 1 }}>
                <Typography component="span" sx={{ fontWeight: 600, color: '#374151' }}>
                  Model:
                </Typography>
                <Typography component="span" sx={{ ml: 1, color: '#1f2937' }}>
                  {selectedVehicleDetails.modelName}
                </Typography>
              </Box>

              <Box sx={{ mb: 1 }}>
                <Typography component="span" sx={{ fontWeight: 600, color: '#374151' }}>
                  Engine Type:
                </Typography>
                <Typography component="span" sx={{ ml: 1, color: '#1f2937' }}>
                  {selectedVehicleDetails.typeEngineName}
                </Typography>
              </Box>

              <Box sx={{ mb: 0 }}>
                <Typography component="span" sx={{ fontWeight: 600, color: '#374151' }}>
                  Fuel Type:
                </Typography>
                <Typography component="span" sx={{ ml: 1, color: '#1f2937' }}>
                  {selectedVehicleDetails.fuelType}
                </Typography>
              </Box>
            </Box>

            {/* Tabs for Parts Table and Tree View */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
              <Tabs value={tabValue} onChange={handleTabChange} aria-label="bill of materials view">
                <Tab label={`Parts Table (${partsData.length} parts)`} />
                <Tab label={`Tree View (${getTotalItemCount(categoryData)} total items)`} />
              </Tabs>
            </Box>

            {/* Tab Content */}
            {tabValue === 0 && (
              // Parts Table
              partsData.length > 0 ? (
                <>
                  <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 600 }}>
                    <Table stickyHeader>
                      <StyledTableHead>
                        <TableRow>
                          <TableCell>Part ID</TableCell>
                          <TableCell>Part Name</TableCell>
                          <TableCell>Category</TableCell>
                        </TableRow>
                      </StyledTableHead>
                      <TableBody>
                        {paginatedParts.map((part) => (
                          <TableRow key={part.categoryId} hover>
                            <TableCell>
                              <Chip
                                label={part.categoryId}
                                size="small"
                                variant="filled"
                                color="default"
                                sx={{ fontSize: '0.75rem' }}
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {part.categoryName}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                                {part.fullPath}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  <TablePagination
                    rowsPerPageOptions={[5, 10, 25, 50]}
                    component="div"
                    count={partsData.length}
                    rowsPerPage={rowsPerPage}
                    page={page}
                    onPageChange={handleChangePage}
                    onRowsPerPageChange={handleChangeRowsPerPage}
                    sx={{ mt: 2 }}
                  />
                </>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body1" color="text.secondary">
                    Loading parts data...
                  </Typography>
                </Box>
              )
            )}

            {tabValue === 1 && (
              // Tree View
              categoryData.length > 0 ? (
                <Box sx={{
                  border: '1px solid #e2e8f0',
                  borderRadius: 2,
                  backgroundColor: '#fafafa',
                  maxHeight: '600px',
                  overflow: 'auto'
                }}>
                  <StyledTreeView
                    defaultExpandedItems={categoryData.slice(0, 3).map(item => item.categoryId)}
                  >
                    {renderTreeItems(categoryData)}
                  </StyledTreeView>
                </Box>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body1" color="text.secondary">
                    Loading bill of materials components...
                  </Typography>
                </Box>
              )
            )}
          </StyledTablePaper>
        )}
      </Container>
    </Box>
  );
}

export default VehicleForm;