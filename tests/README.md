# API Tests

## Quick Start

### Run all tests
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=FastAPI --cov-report=html --cov-report=term
```

### View coverage report
```bash
open htmlcov/index.html
```

## Test Files

- `conftest.py` - Shared fixtures and test configuration
- `test_api.py` - API endpoint tests (13 tests)

## Test Data

All test fixtures use valid CSV data matching the validation requirements:

**Parts CSV requires**: productId, partDescription, quantity, taxable
**Articles CSV requires**: productId, articleNo, price, countryOfOrigin, supplierId, supplierName

## Coverage Results

- **API Routes**: 84%
- **Data Validation**: 78%
- **Overall Project**: 30%
