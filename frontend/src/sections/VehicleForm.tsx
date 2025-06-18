import React, { useEffect, useState, useCallback, useMemo } from 'react';
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

// Types
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

interface FormData {
  vehicle: string;
  vehicleId: string;
  model: string;
  modelId: string;
  type: string;
  categoryFilter: string;
  manufacturingOrigin: string;
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

// Constants
const API_BASE_URL = 'http://127.0.0.1:8000';

// Default fallback origins if API fails
const DEFAULT_MANUFACTURING_ORIGINS = [
  { id: 'all', name: 'All Origins' },
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
  { id: 'turkey', name: 'Turkey' },
  { id: 'poland', name: 'Poland' },
  { id: 'czech_republic', name: 'Czech Republic' },
  { id: 'thailand', name: 'Thailand' },
  { id: 'other', name: 'Other' }
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

// Utility functions
const extractParts = (categories: any, parentPath = ''): PartItem[] => {
  const parts: PartItem[] = [];

  Object.entries(categories).forEach(([id, category]: [string, any]) => {
    const currentPath = parentPath ? `${parentPath} > ${category.text}` : category.text;
    const hasChildren = Object.keys(category.children || {}).length > 0;

    if (!hasChildren) {
      parts.push({
        categoryId: id,
        categoryName: category.text,
        fullPath: currentPath,
        level: parentPath.split(' > ').filter(Boolean).length
      });
    } else {
      parts.push(...extractParts(category.children, currentPath));
    }
  });

  return parts;
};

const processCategories = (categories: any, parentPath = ''): any[] => {
  const treeData: any[] = [];

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
      children: hasChildren ? processCategories(category.children, currentPath) : []
    };

    treeData.push(categoryItem);
  });

  return treeData;
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
    const response = await fetch(`${API_BASE_URL}/countries`);
    const data = await response.json();

    // Transform the API response to match our expected format (without "All Origins")
    const transformedCountries = data.countries.map((country: any) => ({
      id: country.couCode.toLowerCase(),
      name: country.countryName
    }));

    return transformedCountries;
  } catch (error) {
    console.error('Error fetching countries:', error);
    // Return default countries without "All Origins"
    return DEFAULT_MANUFACTURING_ORIGINS.slice(1);
  }
};

const processWithAI = async (billOfMaterialsData: any) => {
  const response = await fetch(`${API_BASE_URL}/ai/process-bill-of-materials`, {
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

  return response.json();
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
    manufacturingOrigin: '',
  });

  // Data state
  const [models, setModels] = useState<{ modelId: number, modelName: string }[]>([]);
  const [engineOptions, setEngineOptions] = useState<EngineOption[]>([]);
  const [availableCategories, setAvailableCategories] = useState<CategoryOption[]>([]);
  const [manufacturingOrigins, setManufacturingOrigins] = useState<{ id: string, name: string }[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [partsData, setPartsData] = useState<PartItem[]>([]);
  const [allCategoryData, setAllCategoryData] = useState<any[]>([]);
  const [allPartsData, setAllPartsData] = useState<PartItem[]>([]);
  const [selectedVehicleDetails, setSelectedVehicleDetails] = useState<EngineOption | null>(null);

  // Loading state
  const [loading, setLoading] = useState({
    models: false,
    engines: false,
    categories: false,
    countries: false,
    ai: false
  });

  // Error state
  const [errors, setErrors] = useState({
    models: null as string | null,
    engines: null as string | null,
    ai: null as string | null
  });

  // UI state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [tabValue, setTabValue] = useState(0);
  const [aiProcessingResult, setAiProcessingResult] = useState<any>(null);
  const [showAiSnackbar, setShowAiSnackbar] = useState(false);

  // Computed values
  const filteredPartsData = useMemo(() => {
    return partsData;
  }, [partsData]);

  const paginatedParts = useMemo(
    () => filteredPartsData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [filteredPartsData, page, rowsPerPage]
  );

  const isBillOfMaterialsPopulated = selectedVehicleDetails && (categoryData.length > 0 || partsData.length > 0);

  const selectedEngine = useMemo(
    () => engineOptions.find(engine => engine.typeEngineName === formData.type),
    [engineOptions, formData.type]
  );

  const filterMessage = useMemo(() => {
    const categoryMsg = formData.categoryFilter === 'all' ? 'all categories' :
      availableCategories.find(cat => cat.id === formData.categoryFilter)?.name || 'selected category';

    const originMsg = !formData.manufacturingOrigin ? 'any origin' :
      manufacturingOrigins.find(origin => origin.id === formData.manufacturingOrigin)?.name || 'selected origin';

    return `${categoryMsg}, ${originMsg}`;
  }, [formData.categoryFilter, formData.manufacturingOrigin, availableCategories, manufacturingOrigins]);

  // Load countries on component mount
  useEffect(() => {
    const loadCountries = async () => {
      setLoading(prev => ({ ...prev, countries: true }));
      try {
        const countries = await fetchCountries();
        setManufacturingOrigins(countries);
        // Set default to first country if none selected
        if (!formData.manufacturingOrigin && countries.length > 0) {
          setFormData(prev => ({ ...prev, manufacturingOrigin: countries[0].id }));
        }
      } catch (error) {
        console.error('Error loading countries:', error);
        const fallbackCountries = DEFAULT_MANUFACTURING_ORIGINS.slice(1);
        setManufacturingOrigins(fallbackCountries);
        // Set default to first country if none selected
        if (!formData.manufacturingOrigin && fallbackCountries.length > 0) {
          setFormData(prev => ({ ...prev, manufacturingOrigin: fallbackCountries[0].id }));
        }
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
    if (!formData.vehicleId || !formData.type || selectedVehicleDetails || !selectedEngine) return;

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
  }, [formData.vehicleId, formData.type, selectedEngine, selectedVehicleDetails]);

  // Reset page when filters change
  useEffect(() => {
    setPage(0);
  }, [formData.categoryFilter, formData.manufacturingOrigin]);

  // Handlers
  const handleInputChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleCategoryFilterChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const newCategoryFilter = event.target.value;
    setFormData(prev => ({ ...prev, categoryFilter: newCategoryFilter }));

    if (selectedVehicleDetails && allCategoryData.length > 0) {
      if (newCategoryFilter === 'all') {
        setCategoryData(allCategoryData);
        setPartsData(allPartsData);
      } else {
        const filteredTreeData = allCategoryData.filter(category => category.categoryId === newCategoryFilter);
        const filteredParts = allPartsData.filter(part =>
          part.fullPath.startsWith(availableCategories.find(cat => cat.id === newCategoryFilter)?.name || '')
        );
        setCategoryData(filteredTreeData);
        setPartsData(filteredParts);
      }
      setPage(0);
    }
  }, [selectedVehicleDetails, allCategoryData, allPartsData, availableCategories]);

  const handleProcessWithAI = useCallback(async () => {
    if (!selectedVehicleDetails || partsData.length === 0) {
      setErrors(prev => ({ ...prev, ai: 'No bill of materials data available to process' }));
      setShowAiSnackbar(true);
      return;
    }

    setLoading(prev => ({ ...prev, ai: true }));
    setErrors(prev => ({ ...prev, ai: null }));
    setAiProcessingResult(null);

    try {
      const billOfMaterialsData = {
        vehicleDetails: {
          vehicleId: selectedVehicleDetails.vehicleId,
          manufacturerId: formData.vehicleId,
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
          manufacturingOriginFilter: formData.manufacturingOrigin,
          filterDescription: filterMessage,
          processedAt: new Date().toISOString()
        }
      };

      const result = await processWithAI(billOfMaterialsData);
      setAiProcessingResult(result);
      setShowAiSnackbar(true);
    } catch (error: any) {
      setErrors(prev => ({ ...prev, ai: error.message || 'Failed to process bill of materials with AI' }));
      setShowAiSnackbar(true);
    } finally {
      setLoading(prev => ({ ...prev, ai: false }));
    }
  }, [selectedVehicleDetails, partsData, categoryData, formData, filterMessage]);

  const handleSubmit = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();

    if (selectedVehicleDetails) {
      alert('Only one vehicle can be added. Please clear the existing vehicle first.');
      return;
    }

    if (!selectedEngine) {
      throw new Error('Selected engine details not found');
    }

    setLoading(prev => ({ ...prev, categories: true }));

    try {
      setSelectedVehicleDetails(selectedEngine);

      const allCategories = await fetchCategories(selectedEngine.vehicleId, formData.vehicleId);

      const filterCategoriesBySelection = (categories: any, categoryFilter: string) => {
        if (categoryFilter === 'all') return categories;

        const targetCategory = Object.entries(categories).find(([id]) => id === categoryFilter);
        if (targetCategory) {
          const [id, category] = targetCategory;
          return { [id]: category };
        }
        return {};
      };

      const filteredCategories = filterCategoriesBySelection(allCategories, formData.categoryFilter);

      const allTreeData = processCategories(allCategories);
      const allParts = extractParts(allCategories);
      setAllCategoryData(allTreeData);
      setAllPartsData(allParts);

      const filteredTreeData = processCategories(filteredCategories);
      const filteredParts = extractParts(filteredCategories);
      setCategoryData(filteredTreeData);
      setPartsData(filteredParts);

      alert(`Vehicle added with bill of materials for ${filterMessage}`);
    } catch (error) {
      console.error('Error fetching data:', error);
      alert('Failed to fetch vehicle or bill of materials data. Please try again.');
    } finally {
      setLoading(prev => ({ ...prev, categories: false }));
    }
  }, [selectedVehicleDetails, selectedEngine, formData, filterMessage]);

  const handleReset = useCallback(() => {
    setFormData({
      vehicle: '',
      vehicleId: '',
      model: '',
      modelId: '',
      type: '',
      categoryFilter: 'all',
      manufacturingOrigin: 'all'
    });
    setModels([]);
    setEngineOptions([]);
    setAvailableCategories([]);
  }, []);

  const handleClearTable = useCallback(() => {
    // Reset form data
    setFormData({
      vehicle: '',
      vehicleId: '',
      model: '',
      modelId: '',
      type: '',
      categoryFilter: 'all',
      manufacturingOrigin: ''
    });

    // Clear dependent data
    setModels([]);
    setEngineOptions([]);
    setAvailableCategories([]);

    // Clear bill of materials data
    setSelectedVehicleDetails(null);
    setCategoryData([]);
    setPartsData([]);
    setAllCategoryData([]);
    setAllPartsData([]);
    setPage(0);
    setAiProcessingResult(null);
    setErrors(prev => ({ ...prev, ai: null }));
  }, []);

  const handleNext = useCallback(() => {
    navigate('/model_configuration', {
      state: {
        vehicleDetails: selectedVehicleDetails,
        partsData: filteredPartsData,
        categoryData: categoryData,
        allPartsData: allPartsData,
        allCategoryData: allCategoryData,
        selectedCategoryFilter: formData.categoryFilter,
        selectedManufacturingOrigin: formData.manufacturingOrigin,
        aiProcessingResult: aiProcessingResult
      }
    });
  }, [navigate, selectedVehicleDetails, filteredPartsData, categoryData, allPartsData, allCategoryData, formData.categoryFilter, formData.manufacturingOrigin, aiProcessingResult]);

  // Render functions
  const renderTreeItems = useCallback((items: any[]) => {
    return items.map((item) => (
      <StyledTreeItem
        key={item.categoryId}
        itemId={item.categoryId}
        label={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5 }}>
            <Typography
              variant="body2"
              sx={{ fontWeight: item.hasChildren ? 600 : 400, flexGrow: 1 }}
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

  return (
    <Container maxWidth="lg">
      {/* Vehicle Selection Form */}
      <StyledPaper elevation={3}>
        <Typography variant="h5" component="h3" gutterBottom sx={{ fontWeight: 700, color: '#1f2937', textAlign: 'center', mb: 4, fontSize: '1.75rem' }}>
          Select Vehicle & Origin
        </Typography>

        <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 400, mx: 'auto' }}>
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
                  categoryFilter: 'all',
                  manufacturingOrigin: ''
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
                  manufacturingOrigin: 'all'
                }));
                setAvailableCategories([]);
              }}
              disabled={!formData.vehicleId || loading.models}
              loading={loading.models}
              disableClearable
              renderOption={(props, option) => (
                <li {...props} key={option.modelId}>{option.modelName}</li>
              )}
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
                !formData.vehicleId ? 'Select a brand to load models' :
                loading.models ? 'Loading models...' :
                errors.models ? errors.models :
                'No models found'
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
                  manufacturingOrigin: ''
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

          <StyledFormControl fullWidth required disabled={!formData.type || selectedVehicleDetails !== null}>
            <InputLabel id="category-filter-label">Parts Category</InputLabel>
            <Select
              labelId="category-filter-label"
              id="category-filter-select"
              name="categoryFilter"
              value={formData.categoryFilter}
              label="Parts Category"
              onChange={handleCategoryFilterChange}
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

          <StyledFormControl fullWidth required>
            <Autocomplete
              options={manufacturingOrigins}
              getOptionLabel={(option) => option.name}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              value={manufacturingOrigins.find(origin => origin.id === formData.manufacturingOrigin) || null}
              onChange={(event, newValue) => {
                setFormData(prev => ({
                  ...prev,
                  manufacturingOrigin: newValue?.id || ''
                }));
              }}
              disabled={!formData.type || selectedVehicleDetails !== null}
              loading={loading.countries}
              disableClearable
              renderOption={(props, option) => (
                <li {...props} key={option.id}>
                  <Typography sx={{ flexGrow: 1 }}>
                    {option.name}
                  </Typography>
                </li>
              )}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Manufacturing Origin"
                  required
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {loading.countries ? <CircularProgress color="inherit" size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
              noOptionsText={loading.countries ? 'Loading countries...' : 'No countries found'}
            />
          </StyledFormControl>

          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
            <StyledButton
              type="submit"
              variant="contained"
              size="medium"
              disabled={loading.categories || selectedVehicleDetails !== null}
            >
              {loading.categories ? 'Loading Bill of Materials...' : selectedVehicleDetails ? 'Vehicle Already Added' : 'Add Vehicle'}
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
              <Box sx={{ ml: 1.5, mt: 0.5 }}>
                {formData.categoryFilter !== 'all' && (
                  <Typography variant="body2" sx={{ color: '#6b7280' }}>
                    Category: {availableCategories.find(cat => cat.id === formData.categoryFilter)?.name || 'Selected Category'}
                  </Typography>
                )}
                {formData.manufacturingOrigin && (
                  <Typography variant="body2" sx={{ color: '#6b7280' }}>
                    Origin: {manufacturingOrigins.find(origin => origin.id === formData.manufacturingOrigin)?.name || 'Selected Origin'}
                  </Typography>
                )}
                <Typography variant="body2" sx={{ color: '#6b7280', mt: 0.5 }}>
                  Showing {filteredPartsData.length} of {partsData.length} parts
                </Typography>
              </Box>
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <AIButton
                variant="contained"
                onClick={handleProcessWithAI}
                disabled={loading.ai || !isBillOfMaterialsPopulated}
                startIcon={
                  loading.ai ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <SmartToyIcon />
                  )
                }
                sx={{ minWidth: 200 }}
              >
                {loading.ai ? 'Processing with AI...' : 'Process Parts with AI'}
              </AIButton>

              <StyledButton onClick={handleClearTable} variant="outlined" color="error" size="small">
                Reset Form & Clear Data
              </StyledButton>
            </Box>
          </Box>

          {/* AI Processing Results */}
          {aiProcessingResult && (
            <Box sx={{
              backgroundColor: '#ecfdf5',
              borderRadius: 2,
              p: 2,
              mt: 3,
              mb: 3,
              border: '1px solid #6ee7b7',
            }}>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#065f46' }}>
                    AI Analysis Summary
                  </Typography>
                  <Typography variant="body2">
                    Parts Analyzed: {aiProcessingResult.vehicle_analysis.total_parts_analyzed}
                  </Typography>
                  <Typography variant="body2">
                    Processing Time: {aiProcessingResult.processing_duration_ms}ms
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#065f46' }}>
                    Recommendations
                  </Typography>
                  <ul style={{ margin: 0, paddingLeft: '1rem' }}>
                    {aiProcessingResult.ai_recommendations.map((rec, idx) => (
                      <li key={idx}><Typography variant="body2">{rec}</Typography></li>
                    ))}
                  </ul>
                </Grid>
              </Grid>
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
            {[
              { label: 'Vehicle ID', value: selectedVehicleDetails.vehicleId },
              { label: 'Manufacturer', value: selectedVehicleDetails.manufacturerName },
              { label: 'Model', value: selectedVehicleDetails.modelName },
              { label: 'Engine Type', value: selectedVehicleDetails.typeEngineName },
              { label: 'Fuel Type', value: selectedVehicleDetails.fuelType }
            ].map((item, index) => (
              <Box key={index} sx={{ mb: index < 4 ? 1 : 0 }}>
                <Typography component="span" sx={{ fontWeight: 600, color: '#374151' }}>
                  {item.label}:
                </Typography>
                <Typography component="span" sx={{ ml: 1, color: '#1f2937' }}>
                  {item.value}
                </Typography>
              </Box>
            ))}
          </Box>

          {/* Tabs for Parts Table and Tree View */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)} aria-label="bill of materials view">
              <Tab label={`Parts Table (${filteredPartsData.length} parts)`} />
              <Tab label={`Tree View (${getTotalItemCount(categoryData)} total items)`} />
            </Tabs>
          </Box>

          {/* Tab Content */}
          {tabValue === 0 && (
            // Parts Table
            filteredPartsData.length > 0 ? (
              <>
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 600 }}>
                  <Table stickyHeader>
                    <StyledTableHead>
                      <TableRow>
                        <TableCell>Part ID</TableCell>
                        <TableCell>Part Name</TableCell>
                        <TableCell>Article No.</TableCell>
                        <TableCell>Supplier</TableCell>
                        <TableCell>Price (GBP)</TableCell>
                        <TableCell>Origin</TableCell>
                      </TableRow>
                    </StyledTableHead>
                    <TableBody>
                      {/* If AI results are available, use the processed parts data */}
                      {aiProcessingResult ? (
                        aiProcessingResult.parts_data
                          .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                          .map((part) => (
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
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                                  {part.fullPath}
                                </Typography>
                              </TableCell>
                              <TableCell>{part.articleNo || 'N/A'}</TableCell>
                              <TableCell>
                                <Chip
                                  label={part.supplierName || 'Unknown'}
                                  size="small"
                                  color={part.supplierTier === 'first_choice' ? 'success' :
                                         part.supplierTier === 'second_choice' ? 'primary' : 'default'}
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell>£{part.estimatedPriceGBP?.toFixed(2) || 'N/A'}</TableCell>
                              <TableCell>
                                {part.likelyManufacturingOrigin ? (
                                  <Chip
                                    label={part.likelyManufacturingOrigin}
                                    size="small"
                                    variant="outlined"
                                    color="info"
                                    sx={{ fontSize: '0.75rem' }}
                                  />
                                ) : 'Unknown'}
                              </TableCell>
                            </TableRow>
                          ))
                      ) : (
                        paginatedParts.map((part) => (
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
                              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                                {part.fullPath}
                              </Typography>
                            </TableCell>
                            <TableCell>-</TableCell>
                            <TableCell>-</TableCell>
                            <TableCell>-</TableCell>
                            <TableCell>-</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>

                <TablePagination
                  rowsPerPageOptions={[5, 10, 25, 50]}
                  component="div"
                  count={aiProcessingResult ? aiProcessingResult.parts_data.length : filteredPartsData.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={(e, newPage) => setPage(newPage)}
                  onRowsPerPageChange={(e) => {
                    setRowsPerPage(parseInt(e.target.value, 10));
                    setPage(0);
                  }}
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

      {/* Next Button */}
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
          severity={errors.ai ? 'error' : 'success'}
          sx={{ width: '100%' }}
        >
          {errors.ai || 'Bill of Materials processed successfully with AI!'}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default VehicleForm;