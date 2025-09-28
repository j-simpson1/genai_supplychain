from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers, fetch_models, fetch_engine_types, fetch_categories_data, get_article_list, fetch_countries
from FastAPI.utils.data_validation import validate_uploaded_csvs

from FastAPI.core.document_generator import auto_supplychain_prompt_template, run_agent

from fastapi import UploadFile, File, Form, APIRouter, HTTPException
from io import StringIO
import logging
import pandas as pd
import datetime
import os
from typing import Optional
from pathlib import Path
import openai
from dotenv import load_dotenv
import json
import traceback
import re
import tempfile
import shutil
from contextlib import contextmanager


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@contextmanager
def temporary_csv_files(*dataframes_with_names):
    """
    Context manager for temporary CSV files with automatic cleanup.
    Args: tuples of (dataframe, filename) or just dataframes
    """
    temp_files = []
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="genai_supply_"))

        for i, item in enumerate(dataframes_with_names):
            if item is None:  # Skip None entries
                temp_files.append(None)
                continue

            if isinstance(item, tuple):
                df, name = item
            else:
                df, name = item, f"data_{i}.csv"

            temp_path = temp_dir / name
            df.to_csv(temp_path, index=False)
            temp_files.append(str(temp_path))

        yield temp_files
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)

@router.get("/manufacturers")
def retrieve_manufacturers():
    return fetch_manufacturers()

@router.get("/manufacturers/models")
def retrieve_models(id: int):
    return fetch_models(id)

@router.get("/manufacturers/models/engine_type")
def retrieve_engine_types(manufacturerId: int, modelSeriesId: int):
    return fetch_engine_types(manufacturerId, modelSeriesId)

@router.get("/manufacturers/models/engine_type/category_v3")
def retrieve_category_v3(vehicleId: int, manufacturerId: int):
    return fetch_categories_data(vehicleId, manufacturerId)

@router.get("/manufacturers/models/engine_type/category_v3/article_list")
def retrieve_article_list(manufacturerId: int, vehicleId: int, productGroupId: int):
    return get_article_list(manufacturerId, vehicleId, productGroupId)


@router.get("/countries")
def retrieve_countries():
    return fetch_countries()



@router.post("/find_countries")
async def find_countries(
    parts_data_file: UploadFile = File(..., description="CSV file with parts data"),
    articles_data_file: UploadFile = File(..., description="CSV file with articles data"),
):
    try:
        if not parts_data_file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="parts_data_file must be a CSV")
        if not articles_data_file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="articles_data_file must be a CSV")

        parts_text = (await parts_data_file.read()).decode("utf-8", errors="ignore")
        articles_text = (await articles_data_file.read()).decode("utf-8", errors="ignore")

        csvs_valid, csv_errors = validate_uploaded_csvs(parts_text, articles_text)
        if not csvs_valid:
            raise HTTPException(status_code=400, detail=f"CSV validation failed: {'; '.join(csv_errors)}")

        parts_df = pd.read_csv(StringIO(parts_text))
        articles_df = pd.read_csv(StringIO(articles_text))

        parts_df.columns = parts_df.columns.str.strip()
        articles_df.columns = articles_df.columns.str.strip()

        if "countryOfOrigin" not in articles_df.columns:
            raise HTTPException(status_code=400, detail="Articles CSV missing 'countryOfOrigin' column")

        countries_series = articles_df["countryOfOrigin"].astype(str).str.strip()
        unique_countries = sorted({c for c in countries_series if c})

        return {
            "countries": unique_countries,
            "counts": {
                "parts_rows": int(len(parts_df)),
                "articles_rows": int(len(articles_df)),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/find_countries failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"find_countries failed: {e}")


@router.post("/run_report_generator")
async def run_report_generator(
        vehicle_details: str = Form(..., description="JSON string containing vehicle details"),
        category_filter: str = Form(..., description="Parts category filter"),
        category_name: str = Form(..., description="Parts category name"),
        manufacturing_location: str = Form(..., description="Manufacturing location country code"),
        manufacturing_location_name: str = Form(..., description="Manufacturing location country name"),
        tariff_shock_country: str = Form(..., description="Country code for tariff shock simulation"),
        tariff_shock_country_name: str = Form(..., description="Country name for tariff shock simulation"),
        tariff_rate_1: str = Form(..., description="First tariff rate percentage"),
        tariff_rate_2: str = Form(..., description="Second tariff rate percentage"),
        tariff_rate_3: str = Form(..., description="Third tariff rate percentage"),
        vat_rate: str = Form(..., description="VAT rate percentage"),  # New VAT rate parameter
        parts_data_file: UploadFile = File(..., description="CSV file with parts data"),
        articles_data_file: UploadFile = File(..., description="CSV file with articles data"),
        tariff_data_file: UploadFile = File(None, description="Optional CSV file with tariff rates and dispatch costs data")
):
    """
    Run vehicle simulation with uploaded data and form parameters.

    This endpoint receives:
    - Vehicle details (engine, manufacturer, model info)
    - Category filter for parts
    - Manufacturing location
    - Tariff shock simulation country
    - Three tariff rate percentages for simulation scenarios
    - VAT rate percentage
    - Parts data CSV file
    - Articles data CSV file
    """

    try:
        # Parse vehicle details JSON
        try:
            vehicle_data = json.loads(vehicle_details)
            logger.info(f"Parsed vehicle details: {vehicle_data}")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid vehicle_details JSON: {str(e)}")

        # Parse and validate tariff rates and VAT rate
        try:
            tariff_rates = []
            for rate_str, rate_name in [(tariff_rate_1, "tariff_rate_1"),
                                        (tariff_rate_2, "tariff_rate_2"),
                                        (tariff_rate_3, "tariff_rate_3")]:
                if not rate_str or rate_str.strip() == "":
                    raise HTTPException(status_code=400, detail=f"{rate_name} cannot be empty")

                try:
                    rate_float = float(rate_str)
                    if rate_float < 0:
                        raise HTTPException(status_code=400, detail=f"{rate_name} cannot be negative")
                    if rate_float > 1000:  # Reasonable upper limit
                        raise HTTPException(status_code=400, detail=f"{rate_name} cannot exceed 1000%")
                    tariff_rates.append(rate_float)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid {rate_name}: must be a valid number")

            # Validate VAT rate
            if not vat_rate or vat_rate.strip() == "":
                raise HTTPException(status_code=400, detail="vat_rate cannot be empty")

            try:
                vat_rate_float = float(vat_rate)
                if vat_rate_float < 0:
                    raise HTTPException(status_code=400, detail="vat_rate cannot be negative")
                if vat_rate_float > 100:  # Reasonable upper limit for VAT
                    raise HTTPException(status_code=400, detail="vat_rate cannot exceed 100%")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid vat_rate: must be a valid number")

            logger.info(f"Parsed tariff rates: {tariff_rates}")
            logger.info(f"Parsed VAT rate: {vat_rate_float}")

            # Process tariff data file if provided
            parsed_tariff_data = []
            tariff_content = None
            if tariff_data_file and tariff_data_file.filename:
                try:
                    if not tariff_data_file.filename.endswith('.csv'):
                        logger.warning("Tariff data file is not a CSV, skipping it")
                    else:
                        tariff_content = await tariff_data_file.read()
                        tariff_content_str = tariff_content.decode('utf-8')

                        # Parse CSV content (simple parsing)
                        lines = tariff_content_str.strip().split('\n')
                        if len(lines) > 1:  # Has header + data
                            header = lines[0].split(',')
                            for line in lines[1:]:
                                if line.strip():  # Skip empty lines
                                    values = line.split(',')
                                    if len(values) >= 2:
                                        country_name = values[0].strip('"')
                                        tariff_rate = values[1] if values[1] else None
                                        parsed_tariff_data.append({
                                            'countryName': country_name,
                                            'tariffRate': tariff_rate
                                        })

                        logger.info(f"Parsed tariff data: {len(parsed_tariff_data)} countries with rates")
                except Exception as e:
                    logger.warning(f"Error processing tariff_data_file: {str(e)}")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing rates: {str(e)}")

        # Validate file types
        if not parts_data_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Parts data file must be a CSV file")

        if not articles_data_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Articles data file must be a CSV file")

        # Read CSV files
        try:
            parts_content = await parts_data_file.read()
            articles_content = await articles_data_file.read()

            parts_content_str = parts_content.decode('utf-8')
            articles_content_str = articles_content.decode('utf-8')

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading CSV files: {str(e)}")

        # Validate CSV structure and required columns
        csvs_valid, csv_errors = validate_uploaded_csvs(parts_content_str, articles_content_str)

        if not csvs_valid:
            raise HTTPException(
                status_code=400,
                detail=f"CSV validation failed: {'; '.join(csv_errors)}"
            )

        # Parse validated CSV files
        try:
            parts_df = pd.read_csv(StringIO(parts_content_str))
            articles_df = pd.read_csv(StringIO(articles_content_str))

            import os

            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            streamlit_dir = os.path.join(BASE_DIR, "..", "core", "streamlit_data")
            os.makedirs(streamlit_dir, exist_ok=True)

            parts_streamlit_path = os.path.join(streamlit_dir, "parts.csv")
            articles_streamlit_path = os.path.join(streamlit_dir, "articles.csv")

            parts_df.to_csv(parts_streamlit_path, index=False)
            articles_df.to_csv(articles_streamlit_path, index=False)

            # Strip whitespace from column names
            parts_df.columns = parts_df.columns.str.strip()
            articles_df.columns = articles_df.columns.str.strip()

            logger.info(f"CSV validation passed - Parts: {len(parts_df)} rows, Articles: {len(articles_df)} rows")
            logger.info(f"Parts data columns: {list(parts_df.columns)}")
            logger.info(f"Articles data columns: {list(articles_df.columns)}")

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing validated CSV files: {str(e)}")

        # Determine the category to use based on category_filter
        # We now receive the category_name directly from frontend
        logger.info(f"Using category: {category_name} (ID: {category_filter})")
        logger.info(f"Manufacturing location: {manufacturing_location_name} ({manufacturing_location})")
        logger.info(f"Tariff shock country: {tariff_shock_country_name} ({tariff_shock_country})")
        logger.info(f"VAT rate: {vat_rate_float}%")  # Log VAT rate

        # Log all received form data
        form_data_summary = {
            "vehicle_details": {
                "manufacturer": vehicle_data.get("manufacturerName"),
                "model": vehicle_data.get("modelName"),
                "engine_type": vehicle_data.get("typeEngineName"),
                "power_ps": vehicle_data.get("powerPs"),
                "fuel_type": vehicle_data.get("fuelType"),
                "body_type": vehicle_data.get("bodyType"),
                "vehicle_id": vehicle_data.get("vehicleId")
            },
            "simulation_parameters": {
                "category_filter": category_filter,
                "category_name": category_name,
                "manufacturing_location": {
                    "code": manufacturing_location,
                    "name": manufacturing_location_name
                },
                "tariff_shock_country": {
                    "code": tariff_shock_country,
                    "name": tariff_shock_country_name
                },
                "tariff_rates": tariff_rates,
                "vat_rate": vat_rate_float,  # Include VAT rate in summary
                "custom_tariff_data": len(parsed_tariff_data) if parsed_tariff_data else 0
            },
            "uploaded_files": {
                "parts_data": {
                    "filename": parts_data_file.filename,
                    "size_kb": len(parts_content) / 1024,
                    "rows": len(parts_df),
                    "columns": len(parts_df.columns)
                },
                "articles_data": {
                    "filename": articles_data_file.filename,
                    "size_kb": len(articles_content) / 1024,
                    "rows": len(articles_df),
                    "columns": len(articles_df.columns)
                },
                "tariff_data": {
                    "filename": tariff_data_file.filename if tariff_data_file else None,
                    "size_kb": len(tariff_content) / 1024 if tariff_data_file else 0,
                    "rows": len(parsed_tariff_data)
                } if tariff_data_file else None
            }
        }

        logger.info(f"Form data summary: {json.dumps(form_data_summary, indent=2)}")

        manufacturer = vehicle_data.get("manufacturerName")
        normalized_manufacturer = manufacturer.title()

        model_name = vehicle_data.get("modelName")
        clean_model_name = re.sub(r"\s*\([^)]*\)", "", model_name)

        # Generate prompt with actual received data including VAT rate
        prompt = auto_supplychain_prompt_template(
            manufacturer=normalized_manufacturer,
            model=clean_model_name,
            component=category_name,  # Now using the actual category name from frontend
            manufacturing_country=manufacturing_location_name,
            tariff_shock_country=tariff_shock_country_name,  # Using country name instead of code
            rates=tariff_rates,
            vat_rate=vat_rate_float  # Pass VAT rate to prompt template
        )

        # Prepare temporary files for agent
        temp_data = [
            (parts_df, "parts.csv"),
            (articles_df, "articles.csv")
        ]

        # Add tariff data if provided
        tariff_path = None
        if parsed_tariff_data:
            tariff_df = pd.DataFrame(parsed_tariff_data)
            temp_data.append((tariff_df, "tariff.csv"))
            logger.info(f"Including tariff data with {len(parsed_tariff_data)} entries")

        # Use context manager for temporary files
        with temporary_csv_files(*temp_data) as temp_paths:
            parts_path, articles_path = temp_paths[0], temp_paths[1]
            if len(temp_paths) > 2:
                tariff_path = temp_paths[2]
            result = await run_agent(prompt, parts_path, articles_path, tariff_path)

        # Return successful response with summary
        return {
            "status": "success",
            "message": "Simulation completed successfully",
            "simulation_summary": form_data_summary,
            "validation_info": {
                "parts_rows_processed": len(parts_df),
                "articles_rows_processed": len(articles_df),
                "validation_passed": True
            },
            "result": result
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_report_generator: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openai.api_key = openai_key


