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
- `test_api.py` - 15 automated tests (13 integration + 2 unit)

## Test Data

All test fixtures use valid CSV data matching the validation requirements:

**Parts CSV requires**: productId, partDescription, quantity, taxable
**Articles CSV requires**: productId, articleNo, price, countryOfOrigin, supplierId, supplierName

## Test Breakdown

### Integration Tests (13)
- 5 Find Countries endpoint tests
- 6 Report Generator endpoint tests
- 2 CSV validation integration tests

### Unit Tests (2)
- Empty required columns validation
- Numeric column validation

## Coverage Results

- **API Routes**: 84%
- **Data Validation**: 86%
- **Overall Project**: 31%
- **Total Tests**: 15
- **Pass Rate**: 100%
