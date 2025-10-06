import pytest
from fastapi.testclient import TestClient
from FastAPI.main import app
from io import BytesIO


@pytest.fixture
def client():
    """Test client fixture for API testing"""
    return TestClient(app)


@pytest.fixture
def sample_parts_csv():
    """Sample parts CSV data for testing"""
    csv_content = """productId,partDescription,quantity,taxable
1,Engine Oil Filter,10,True
2,Brake Pad Set,5,True
3,Air Filter,15,True
4,Spark Plugs,20,True
5,Wiper Blades,8,True"""
    return BytesIO(csv_content.encode('utf-8'))


@pytest.fixture
def sample_articles_csv():
    """Sample articles CSV data for testing"""
    csv_content = """productId,articleNo,price,countryOfOrigin,supplierId,supplierName
1,ART001,25.99,Japan,101,Japan Parts Co
2,ART002,89.99,Germany,102,German Auto GmbH
3,ART003,15.50,United States,103,USA Parts Inc
4,ART004,45.00,Japan,101,Japan Parts Co
5,ART005,12.99,China,104,China Manufacturing Ltd"""
    return BytesIO(csv_content.encode('utf-8'))


@pytest.fixture
def sample_tariff_csv():
    """Sample tariff CSV data for testing"""
    csv_content = """countryName,tariffRate
Japan,2.5
Germany,3.0
United States,2.0
China,5.0"""
    return BytesIO(csv_content.encode('utf-8'))


@pytest.fixture
def invalid_parts_csv():
    """Invalid parts CSV missing required columns"""
    csv_content = """productId,description
1,Some Part
2,Another Part"""
    return BytesIO(csv_content.encode('utf-8'))


@pytest.fixture
def invalid_articles_csv():
    """Invalid articles CSV missing required columns"""
    csv_content = """productId,articleNo
1,ART001
2,ART002"""
    return BytesIO(csv_content.encode('utf-8'))
