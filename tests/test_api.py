import pytest
from unittest.mock import patch, AsyncMock
from io import BytesIO
import json


class TestFindCountriesEndpoint:
    """Tests for /find_countries endpoint"""

    def test_find_countries_success(self, client, sample_parts_csv, sample_articles_csv):
        """Test successful country extraction from valid CSV files"""
        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "countries" in data
        assert "counts" in data
        assert isinstance(data["countries"], list)
        assert len(data["countries"]) > 0
        assert "Japan" in data["countries"]
        assert "Germany" in data["countries"]

    def test_find_countries_invalid_parts_file(self, client, invalid_parts_csv, sample_articles_csv):
        """Test error handling for invalid parts CSV"""
        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.csv", invalid_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()

    def test_find_countries_invalid_articles_file(self, client, sample_parts_csv, invalid_articles_csv):
        """Test error handling for invalid articles CSV"""
        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", invalid_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()

    def test_find_countries_non_csv_file(self, client, sample_parts_csv):
        """Test error handling for non-CSV file"""
        txt_file = BytesIO(b"This is a text file")

        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.txt", txt_file, "text/plain"),
                "articles_data_file": ("articles.csv", sample_parts_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "must be a CSV" in response.json()["detail"]

    def test_find_countries_row_counts(self, client, sample_parts_csv, sample_articles_csv):
        """Test that row counts are correctly returned"""
        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["counts"]["parts_rows"] == 5
        assert data["counts"]["articles_rows"] == 5


class TestRunReportGeneratorEndpoint:
    """Tests for /run_report_generator endpoint"""

    @patch('FastAPI.routes.api.run_agent', new_callable=AsyncMock)
    def test_run_report_generator_success(self, mock_run_agent, client, sample_parts_csv,
                                                sample_articles_csv, sample_tariff_csv):
        """Test successful report generation"""
        # Mock the agent response
        mock_run_agent.return_value = {
            "report_path": "/path/to/report.pdf",
            "charts": ["chart1.png", "chart2.png"]
        }

        vehicle_details = {
            "manufacturerName": "Toyota",
            "modelName": "Camry",
            "typeEngineName": "2.5L I4",
            "powerPs": 203,
            "fuelType": "Gasoline",
            "bodyType": "Sedan",
            "vehicleId": "12345"
        }

        response = client.post(
            "/run_report_generator",
            data={
                "vehicle_details": json.dumps(vehicle_details),
                "category_filter": "1",
                "category_name": "Engine",
                "manufacturing_location": "JP",
                "manufacturing_location_name": "Japan",
                "tariff_shock_country": "US",
                "tariff_shock_country_name": "United States",
                "tariff_rate_1": "10.0",
                "tariff_rate_2": "20.0",
                "tariff_rate_3": "30.0",
                "vat_rate": "20.0"
            },
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv"),
                "tariff_data_file": ("tariff.csv", sample_tariff_csv, "text/csv")
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "validation_info" in data

    def test_run_report_generator_invalid_json(self, client, sample_parts_csv, sample_articles_csv):
        """Test error handling for invalid vehicle details JSON"""
        response = client.post(
            "/run_report_generator",
            data={
                "vehicle_details": "invalid json{",
                "category_filter": "1",
                "category_name": "Engine",
                "manufacturing_location": "JP",
                "manufacturing_location_name": "Japan",
                "tariff_shock_country": "US",
                "tariff_shock_country_name": "United States",
                "tariff_rate_1": "10.0",
                "tariff_rate_2": "20.0",
                "tariff_rate_3": "30.0",
                "vat_rate": "20.0"
            },
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "Invalid vehicle_details JSON" in response.json()["detail"]

    def test_run_report_generator_invalid_tariff_rate(self, client, sample_parts_csv, sample_articles_csv):
        """Test error handling for invalid tariff rate"""
        vehicle_details = {"manufacturerName": "Toyota", "modelName": "Camry"}

        response = client.post(
            "/run_report_generator",
            data={
                "vehicle_details": json.dumps(vehicle_details),
                "category_filter": "1",
                "category_name": "Engine",
                "manufacturing_location": "JP",
                "manufacturing_location_name": "Japan",
                "tariff_shock_country": "US",
                "tariff_shock_country_name": "United States",
                "tariff_rate_1": "invalid",
                "tariff_rate_2": "20.0",
                "tariff_rate_3": "30.0",
                "vat_rate": "20.0"
            },
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "must be a valid number" in response.json()["detail"]

    def test_run_report_generator_negative_tariff_rate(self, client, sample_parts_csv, sample_articles_csv):
        """Test error handling for negative tariff rate"""
        vehicle_details = {"manufacturerName": "Toyota", "modelName": "Camry"}

        response = client.post(
            "/run_report_generator",
            data={
                "vehicle_details": json.dumps(vehicle_details),
                "category_filter": "1",
                "category_name": "Engine",
                "manufacturing_location": "JP",
                "manufacturing_location_name": "Japan",
                "tariff_shock_country": "US",
                "tariff_shock_country_name": "United States",
                "tariff_rate_1": "-10.0",
                "tariff_rate_2": "20.0",
                "tariff_rate_3": "30.0",
                "vat_rate": "20.0"
            },
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "cannot be negative" in response.json()["detail"]

    def test_run_report_generator_invalid_vat_rate(self, client, sample_parts_csv, sample_articles_csv):
        """Test error handling for invalid VAT rate"""
        vehicle_details = {"manufacturerName": "Toyota", "modelName": "Camry"}

        response = client.post(
            "/run_report_generator",
            data={
                "vehicle_details": json.dumps(vehicle_details),
                "category_filter": "1",
                "category_name": "Engine",
                "manufacturing_location": "JP",
                "manufacturing_location_name": "Japan",
                "tariff_shock_country": "US",
                "tariff_shock_country_name": "United States",
                "tariff_rate_1": "10.0",
                "tariff_rate_2": "20.0",
                "tariff_rate_3": "30.0",
                "vat_rate": "150.0"
            },
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "vat_rate cannot exceed 100%" in response.json()["detail"]

    def test_run_report_generator_non_csv_parts(self, client, sample_articles_csv):
        """Test error handling for non-CSV parts file"""
        vehicle_details = {"manufacturerName": "Toyota", "modelName": "Camry"}
        txt_file = BytesIO(b"This is a text file")

        response = client.post(
            "/run_report_generator",
            data={
                "vehicle_details": json.dumps(vehicle_details),
                "category_filter": "1",
                "category_name": "Engine",
                "manufacturing_location": "JP",
                "manufacturing_location_name": "Japan",
                "tariff_shock_country": "US",
                "tariff_shock_country_name": "United States",
                "tariff_rate_1": "10.0",
                "tariff_rate_2": "20.0",
                "tariff_rate_3": "30.0",
                "vat_rate": "20.0"
            },
            files={
                "parts_data_file": ("parts.txt", txt_file, "text/plain"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
        assert "must be a CSV file" in response.json()["detail"]


class TestDataValidation:
    """Tests for data validation functions"""

    def test_csv_validation_success(self, client, sample_parts_csv, sample_articles_csv):
        """Test that valid CSVs pass validation"""
        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.csv", sample_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 200

    def test_csv_validation_missing_columns(self, client, invalid_parts_csv, sample_articles_csv):
        """Test that CSVs with missing columns fail validation"""
        response = client.post(
            "/find_countries",
            files={
                "parts_data_file": ("parts.csv", invalid_parts_csv, "text/csv"),
                "articles_data_file": ("articles.csv", sample_articles_csv, "text/csv")
            }
        )

        assert response.status_code == 400
