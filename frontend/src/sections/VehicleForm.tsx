import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Tab,
  CircularProgress,
  Alert,
  Snackbar
} from '@mui/material';
import { SimpleTreeView } from '@mui/x-tree-view/SimpleTreeView';
import { TreeItem } from '@mui/x-tree-view/TreeItem';
import { styled } from '@mui/material/styles';
import SmartToyIcon from '@mui/icons-material/SmartToy';

// Custom styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(6, 5),
  marginTop: theme.spacing(0),
  marginBottom: theme.spacing(3),
  marginLeft: 'auto',
  marginRight: 'auto',
  borderRadius: 16,
  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
}));

const StyledTablePaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginTop: theme.spacing(2),
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

const AIButton = styled(Button)(({ theme }) => ({
  borderRadius: 12,
  padding: theme.spacing(2, 4),
  fontSize: '16px',
  fontWeight: 600,
  textTransform: 'none',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
  boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
  '&:hover': {
    background: 'linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%)',
    transform: 'translateY(-2px)',
    boxShadow: '0 8px 20px rgba(102, 126, 234, 0.6)',
  },
  '&:disabled': {
    background: '#e5e7eb',
    color: '#9ca3af',
    boxShadow: 'none',
    transform: 'none',
  },
  transition: 'all 0.3s ease',
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

const NextButtonContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  paddingTop: theme.spacing(4),
  paddingBottom: theme.spacing(4),
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

interface CategoryOption {
  id: string;
  name: string;
}

function VehicleForm({ vehicleBrands }: VehicleFormProps) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    vehicle: '',
    vehicleId: '',
    model: '',
    modelId: '',
    type: '',
    categoryFilter: 'all', // New field for category filter
  });

  const [models, setModels] = useState<{ modelId: number, modelName: string }[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  const [engineOptions, setEngineOptions] = useState<any[]>([]);
  const [loadingEngines, setLoadingEngines] = useState(false);
  const [engineError, setEngineError] = useState<string | null>(null);

  // New state for available categories
  const [availableCategories, setAvailableCategories] = useState<CategoryOption[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);

  // Table state
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [partsData, setPartsData] = useState<PartItem[]>([]);
  const [allCategoryData, setAllCategoryData] = useState<any[]>([]); // Store all categories
  const [allPartsData, setAllPartsData] = useState<PartItem[]>([]); // Store all parts
  const [selectedVehicleDetails, setSelectedVehicleDetails] = useState<any>(null);

  // Table pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Tab state
  const [tabValue, setTabValue] = useState(0);

  // AI Processing state
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [aiProcessingResult, setAiProcessingResult] = useState<any>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [showAiSnackbar, setShowAiSnackbar] = useState(false);

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

  // New effect to load available categories when engine type is selected
  useEffect(() => {
    if (formData.vehicleId && formData.type && !selectedVehicleDetails) {
      const selectedEngine = engineOptions.find(engine => engine.typeEngineName === formData.type);
      if (selectedEngine) {
        setLoadingCategories(true);

        fetch(`http://127.0.0.1:8000/manufacturers/models/engine_type/category_v3?vehicleId=${selectedEngine.vehicleId}&manufacturerId=${formData.vehicleId}`)
          .then(res => res.json())
          .then(data => {
            const categories = data.categories || data;
            const level1Categories: CategoryOption[] = Object.entries(categories).map(([id, category]: [string, any]) => ({
              id: id,
              name: category.text
            }));
            setAvailableCategories(level1Categories);
          })
          .catch(error => {
            console.error('Error fetching categories:', error);
            setAvailableCategories([]);
          })
          .finally(() => setLoadingCategories(false));
      }
    }
  }, [formData.vehicleId, formData.type, engineOptions, selectedVehicleDetails]);

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

  // Filter categories based on selected category filter
  const filterCategoriesBySelection = (categories, categoryFilter) => {
    if (categoryFilter === 'all') {
      return categories;
    }

    // Find the specific category
    const targetCategory = Object.entries(categories).find(([id, category]: [string, any]) => id === categoryFilter);
    if (targetCategory) {
      const [id, category] = targetCategory;
      return { [id]: category };
    }

    return {};
  };

  // NEW: AI Processing function
  const handleProcessWithAI = async () => {
    if (!selectedVehicleDetails || partsData.length === 0) {
      setAiError('No bill of materials data available to process');
      setShowAiSnackbar(true);
      return;
    }

    setIsProcessingAI(true);
    setAiError(null);
    setAiProcessingResult(null);

    try {
      // Prepare the data to send to the backend
        const billOfMaterialsData = {
          vehicleDetails: {
            vehicleId: selectedVehicleDetails.vehicleId,
            manufacturerId: formData.vehicleId, // Add this line
            manufacturerName: selectedVehicleDetails.manufacturerName,
            modelName: selectedVehicleDetails.modelName,
            typeEngineName: selectedVehicleDetails.typeEngineName,
            powerPs: selectedVehicleDetails.powerPs,
            fuelType: selectedVehicleDetails.fuelType,
            bodyType: selectedVehicleDetails.bodyType
          },
          parts: partsData.map(part => ({
            categoryId: part.categoryId,
            categoryName: part.categoryName,
            fullPath: part.fullPath,
            level: part.level
          })),
          categories: categoryData.map(category => ({
            categoryId: category.categoryId,
            categoryName: category.categoryName,
            fullPath: category.fullPath,
            level: category.level,
            hasChildren: category.hasChildren
          })),
          metadata: {
            manufacturerId: formData.vehicleId,
            totalParts: partsData.length,
            totalCategories: categoryData.length,
            categoryFilter: formData.categoryFilter,
            filterDescription: formData.categoryFilter === 'all'
              ? 'Complete Vehicle'
              : availableCategories.find(cat => cat.id === formData.categoryFilter)?.name || 'Selected Category',
            processedAt: new Date().toISOString()
          }
        };

      console.log('Sending to AI backend:', billOfMaterialsData);

      // Send POST request to FastAPI backend
      const response = await fetch('http://127.0.0.1:8000/ai/process-bill-of-materials', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(billOfMaterialsData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('AI Processing Result:', result);

      setAiProcessingResult(result);
      setShowAiSnackbar(true);

      // You can also navigate to a results page or update the UI to show the results
      // navigate('/ai-results', { state: { result, originalData: billOfMaterialsData } });

    } catch (error) {
      console.error('Error processing with AI:', error);
      setAiError(error.message || 'Failed to process bill of materials with AI');
      setShowAiSnackbar(true);
    } finally {
      setIsProcessingAI(false);
    }
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
      const allCategories = categoryResult.categories || categoryResult;

      // Filter categories based on selection
      const filteredCategories = filterCategoriesBySelection(allCategories, formData.categoryFilter);

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

      // Store all data for reference
      const allTreeData = processCategories(allCategories);
      const allParts = extractParts(allCategories);
      setAllCategoryData(allTreeData);
      setAllPartsData(allParts);

      // Set filtered data for display
      const filteredTreeData = processCategories(filteredCategories);
      const filteredParts = extractParts(filteredCategories);
      setCategoryData(filteredTreeData);
      setPartsData(filteredParts);

      console.log('Form submitted:', formData);
      console.log('Vehicle details:', selectedEngine);
      console.log('All categories fetched:', allTreeData.length);
      console.log('Filtered categories:', filteredTreeData.length);
      console.log('All parts extracted:', allParts.length);
      console.log('Filtered parts:', filteredParts.length);

      const filterMessage = formData.categoryFilter === 'all'
        ? 'all categories'
        : availableCategories.find(cat => cat.id === formData.categoryFilter)?.name || 'selected category';

      alert(`Vehicle added with bill of materials for ${filterMessage}`);

    } catch (error) {
      console.error('Error fetching data:', error);
      alert('Failed to fetch vehicle or bill of materials data. Please try again.');
    } finally {
      setLoadingCategories(false);
    }
  };

  // Handle category filter change
  const handleCategoryFilterChange = (event) => {
    const newCategoryFilter = event.target.value;
    setFormData(prev => ({
      ...prev,
      categoryFilter: newCategoryFilter
    }));

    // If vehicle is already loaded, update the displayed data
    if (selectedVehicleDetails && allCategoryData.length > 0) {
      if (newCategoryFilter === 'all') {
        setCategoryData(allCategoryData);
        setPartsData(allPartsData);
      } else {
        // Filter the stored data
        const filteredTreeData = allCategoryData.filter(category => category.categoryId === newCategoryFilter);
        const filteredParts = allPartsData.filter(part =>
          part.fullPath.startsWith(availableCategories.find(cat => cat.id === newCategoryFilter)?.name || '')
        );
        setCategoryData(filteredTreeData);
        setPartsData(filteredParts);
      }
      setPage(0); // Reset pagination
    }
  };

  const handleReset = () => {
    setFormData({
      vehicle: '',
      vehicleId: '',
      model: '',
      modelId: '',
      type: '',
      categoryFilter: 'all'
    });
    setModels([]);
    setEngineOptions([]);
    setAvailableCategories([]);
  };

  const handleClearTable = () => {
    setSelectedVehicleDetails(null);
    setCategoryData([]);
    setPartsData([]);
    setAllCategoryData([]);
    setAllPartsData([]);
    setPage(0);
    // Clear AI results when clearing table
    setAiProcessingResult(null);
    setAiError(null);
  };

  const handleNext = () => {
    // Navigate to the next page - replace '/next-page' with your actual route
    navigate('/model_configuration', {
      state: {
        vehicleDetails: selectedVehicleDetails,
        partsData: partsData,
        categoryData: categoryData,
        allPartsData: allPartsData,
        allCategoryData: allCategoryData,
        selectedCategoryFilter: formData.categoryFilter,
        aiProcessingResult: aiProcessingResult // Include AI results in navigation
      }
    });
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

  // Check if Bill of Materials data is populated
  const isBillOfMaterialsPopulated = selectedVehicleDetails && (categoryData.length > 0 || partsData.length > 0);

  return (
    <Container maxWidth="lg">
      {/* Vehicle Selection Form */}
      <StyledPaper elevation={3}>
        <Typography variant="h5" component="h3" gutterBottom sx={{ fontWeight: 700, color: '#1f2937', textAlign: 'center', mb: 4, fontSize: '1.75rem' }}>
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
                  model: '',
                  categoryFilter: 'all'
                }));
                setAvailableCategories([]);
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
                    modelId: selectedModel?.modelId || '',
                    categoryFilter: 'all'
                  }));
                  setAvailableCategories([]);
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
              onChange={(e) => {
                setFormData(prev => ({
                  ...prev,
                  type: e.target.value,
                  categoryFilter: 'all'
                }));
                setAvailableCategories([]);
              }}
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

          {/* New Category Filter Dropdown */}
          <StyledFormControl fullWidth disabled={!formData.type || selectedVehicleDetails !== null}>
            <InputLabel id="category-filter-label">Parts Category</InputLabel>
            <Select
              labelId="category-filter-label"
              id="category-filter-select"
              name="categoryFilter"
              value={formData.categoryFilter}
              label="Parts Category"
              onChange={handleCategoryFilterChange}
            >
              <MenuItem value="all">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography sx={{ fontWeight: 600 }}>Complete Vehicle</Typography>
                  <Chip label="All Parts" size="small" color="primary" variant="outlined" />
                </Box>
              </MenuItem>
              {loadingCategories ? (
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
            <Box>
              <Typography variant="h5" component="h3" sx={{ fontWeight: 700, color: '#1f2937', mt: 1.5, ml: 1.5, fontSize: '1.75rem' }}>
                Bill of Materials
              </Typography>
              {formData.categoryFilter !== 'all' && (
                <Typography variant="body2" sx={{ ml: 1.5, mt: 0.5, color: '#6b7280' }}>
                  Filtered by: {availableCategories.find(cat => cat.id === formData.categoryFilter)?.name || 'Selected Category'}
                </Typography>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              {/* AI Processing Button */}
              <AIButton
                variant="contained"
                onClick={handleProcessWithAI}
                disabled={isProcessingAI || !isBillOfMaterialsPopulated}
                startIcon={
                  isProcessingAI ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <SmartToyIcon />
                  )
                }
                sx={{ minWidth: 200 }}
              >
                {isProcessingAI ? 'Processing with AI...' : 'Process Parts with AI'}
              </AIButton>

              <StyledButton onClick={handleClearTable} variant="outlined" color="error" size="small">
                Clear Bill of Materials
              </StyledButton>
            </Box>
          </Box>

          {/* AI Processing Results */}
          {aiProcessingResult && (
            <Box sx={{
              backgroundColor: '#f0f9ff',
              borderRadius: 2,
              p: 3,
              mb: 3,
              border: '1px solid #0ea5e9',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#0369a1', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <SmartToyIcon color="primary" />
                AI Processing Results
              </Typography>
              <Box sx={{
                backgroundColor: 'white',
                borderRadius: 1,
                p: 2,
                fontFamily: 'monospace',
                fontSize: '14px',
                maxHeight: '200px',
                overflow: 'auto'
              }}>
                <pre>{JSON.stringify(aiProcessingResult, null, 2)}</pre>
              </Box>
            </Box>
          )}

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

          {/* Next Button - Bottom right of Bill of Materials card */}
          {isBillOfMaterialsPopulated && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3, pr: 2 }}>
              <StyledButton
                variant="contained"
                size="large"
                onClick={handleNext}
                sx={{
                  minWidth: 120,
                  fontSize: '18px',
                  py: 1.5,
                  px: 4,
                }}
              >
                Next
              </StyledButton>
            </Box>
          )}

      {/* Snackbar for AI Processing notifications */}
      <Snackbar
        open={showAiSnackbar}
        autoHideDuration={6000}
        onClose={() => setShowAiSnackbar(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setShowAiSnackbar(false)}
          severity={aiError ? 'error' : 'success'}
          sx={{ width: '100%' }}
        >
          {aiError || 'Bill of Materials processed successfully with AI!'}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default VehicleForm;