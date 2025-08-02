from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers, fetch_models, fetch_engine_types, fetch_categories_data, get_article_list, fetch_suppliers, fetch_countries
from FastAPI.data.auto_parts.ai_analysis import rank_suppliers, generate_price_estimation_and_country
from FastAPI.services.article_selector import select_preferred_article
from FastAPI.automotive_simulation.powerBi_upload import upload_to_powerbi
from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers
from FastAPI.actions.handle_action import handle_actions
from FastAPI.utils.data_validation import validate_uploaded_csvs

from FastAPI.core.document_generator import auto_supplychain_prompt_template, run_agent

from fastapi import UploadFile, File, Form
from io import StringIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from FastAPI.schemas.models import Item, VehicleDetails, PartItem, CategoryItem, BillOfMaterialsRequest, AlternativeSupplier, SimulationRequest, TokenRequest, Message, ChatRequest
from fastapi import APIRouter, HTTPException, BackgroundTasks
import pandas as pd
import datetime
import os
from typing import Optional, Dict, Any
from pathlib import Path
from FastAPI.powerbi_integration.auth import get_access_token
from FastAPI.services.stream_chat_services import chat_client
import openai
from dotenv import load_dotenv
import json
import traceback
import re

router = APIRouter()

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

@router.get("/suppliers")
def retrieve_suppliers():
    return fetch_suppliers()

@router.get("/countries")
def retrieve_countries():
    return fetch_countries()

@router.post("/ai/process-bill-of-materials")
async def process_bill_of_materials_with_ai(request: BillOfMaterialsRequest):
    try:
        print("Received request:")
        print(f"Vehicle Details: {request.vehicleDetails.dict()}")
        print(f"Number of parts: {len(request.parts)}")

        parts_df = pd.DataFrame([part.dict() for part in request.parts])

        manufacturer_id = request.metadata["manufacturerId"]
        manufacturer_name = request.vehicleDetails.manufacturerName
        vehicle_id = request.vehicleDetails.vehicleId
        manufacturing_origin = request.vehicleDetails.manufacturingOrigin

        article_numbers = []
        supplier_names = []
        product_names = []
        supplier_tiers = []

        suppliers = fetch_suppliers()
        shortened_suppliers = [supplier["supMatchCode"] for supplier in suppliers]
        ranked_suppliers = rank_suppliers(manufacturer_name, shortened_suppliers, manufacturing_origin)

        for category_id in parts_df['categoryId']:
            article_list = get_article_list(manufacturer_id, vehicle_id, category_id)

            articles = article_list.get('articles') or []

            extracted_articles = [
                {
                    'articleNo': article['articleNo'],
                    'supplierName': article['supplierName'],
                    'articleProductName': article['articleProductName']
                }
                for article in articles
            ]

            preferred_article, tier = select_preferred_article(extracted_articles, ranked_suppliers)

            article_numbers.append(preferred_article.get('articleNo') if preferred_article else None)
            supplier_names.append(preferred_article.get('supplierName') if preferred_article else None)
            product_names.append(preferred_article.get('articleProductName') if preferred_article else None)
            supplier_tiers.append(tier)

        # Add columns to parts_df
        parts_df['articleNo'] = article_numbers
        parts_df['supplierName'] = supplier_names
        parts_df['articleProductName'] = product_names
        parts_df['supplierTier'] = supplier_tiers

        price_country_estimation = generate_price_estimation_and_country(parts_df)

        price_map = {item['articleNo']: item['estimatedPriceGBP'] for item in price_country_estimation}
        country_map = {item['articleNo']: item['likelyManufacturingOrigin'] for item in price_country_estimation}

        parts_df['estimatedPriceGBP'] = parts_df['articleNo'].map(price_map)
        parts_df['likelyManufacturingOrigin'] = parts_df['articleNo'].map(country_map)

        print("Updated parts dataframe with parts and estimated prices:")
        print(parts_df)
        parts_df.to_csv('exports/parts_data.csv', index=False)

        ai_result = {
            "status": "success",
            "vehicle_analysis": {
                "total_parts_analyzed": len(request.parts),
            },
            "parts_data": parts_df.to_dict(orient="records"),  # Convert DataFrame to list of dictionaries
            "ai_recommendations": [
                "Insight 1",
                "Insight 2",
                "Insight 3"
            ],
            "processing_timestamp": datetime.datetime.now().isoformat(),
            "processing_duration_ms": 1500
        }

        return ai_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


@router.post("/run_simulation")
async def run_simulation(
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
        parts_data_file: UploadFile = File(..., description="CSV file with parts data"),
        articles_data_file: UploadFile = File(..., description="CSV file with articles data")
):
    """
    Run vehicle simulation with uploaded data and form parameters.

    This endpoint receives:
    - Vehicle details (engine, manufacturer, model info)
    - Category filter for parts
    - Manufacturing location
    - Tariff shock simulation country
    - Three tariff rate percentages for simulation scenarios
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

        # Parse and validate tariff rates
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

            logger.info(f"Parsed tariff rates: {tariff_rates}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing tariff rates: {str(e)}")

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
                "tariff_rates": tariff_rates
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
                }
            }
        }

        logger.info(f"Form data summary: {json.dumps(form_data_summary, indent=2)}")

        manufacturer = vehicle_data.get("manufacturerName")
        normalized_manufacturer = manufacturer.title()

        model_name = vehicle_data.get("modelName")
        clean_model_name = re.sub(r"\s*\([^)]*\)", "", model_name)

        # Generate prompt with actual received data
        prompt = auto_supplychain_prompt_template(
            manufacturer=normalized_manufacturer,
            model=clean_model_name,
            component=category_name,  # Now using the actual category name from frontend
            country=tariff_shock_country_name,  # Using country name instead of code
            rates=tariff_rates
        )

        import tempfile

        # Save uploaded CSVs temporarily
        parts_path = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        articles_path = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name

        parts_df.to_csv(parts_path, index=False)
        articles_df.to_csv(articles_path, index=False)

        # Call agent using file paths
        result = run_agent(prompt, parts_path, articles_path)

        # Clean up temporary files
        try:
            import os
            os.unlink(parts_path)
            os.unlink(articles_path)
        except Exception as cleanup_error:
            logger.warning(f"Could not clean up temporary files: {cleanup_error}")

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
        logger.error(f"Unexpected error in run_simulation: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/upload_powerbi")
async def upload_simulation_to_powerbi(csv_filename: Optional[str] = None):
    # Find the file to upload
    if csv_filename:
        csv_path = os.path.join("exports", csv_filename)
        if not csv_filename.endswith('.csv'):
            csv_path += '.csv'
    else:
        # Find the latest CSV in the exports directory
        export_dir = Path("exports")
        csv_files = list(export_dir.glob("simulation_*.csv"))

        if not csv_files:
            raise HTTPException(status_code=404, detail="No simulation export files found in exports directory")

        # Get the most recent file
        csv_path = str(max(csv_files, key=lambda x: x.stat().st_mtime))
        csv_filename = os.path.basename(csv_path)

    # Verify the CSV file exists
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"CSV file not found: {csv_path}")

    # Upload to Power BI directly from CSV
    access_token = get_access_token()
    result = upload_to_powerbi(
        csv_path=csv_path,
        access_token=access_token,
        dataset_name=f"Supply Chain Simulation {csv_filename.replace('.csv', '')}",
        workspace_id='188dcf61-6524-4b27-93ce-222438bb3545'
    )

    return result

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openai.api_key = openai_key


@router.post("/chat")
async def chat_with_openai(request: ChatRequest):
    try:

        SYSTEM_PROMPT = {
            "role": "system",
            "content": (
                "You are an AI assistant integrated into a system that can call backend APIs. "
                "If the user's request requires a backend action (e.g., retrieving manufacturers), "
                "respond with a JSON object like:\n\n"
                "{\n"
                '  "response": "I’m fetching that for you...",\n'
                '  "action": {\n'
                '    "type": "retrieve_manufacturers",\n'
                '    "params": {}\n'
                "  }\n"
                "}\n\n"
                "If no action is required, respond as plain text."
            )
        }
        # Step 1: Call OpenAI
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[SYSTEM_PROMPT] + [{"role": m.role, "content": m.content} for m in request.messages]
        )

        ai_raw = response.choices[0].message.content.strip()

        # Step 2: Parse response
        try:
            parsed = json.loads(ai_raw)
            base_message = parsed.get("response", "")
            action = parsed.get("action")
        except json.JSONDecodeError:
            base_message = ai_raw
            action = None

        # Step 3: Run action (and get any result)
        action_result = None
        if action:
            action_result = handle_actions(action)

        # Step 4: Compose final message
        if action_result:
            full_message = f"{base_message}\n\n{action_result}"
        else:
            full_message = base_message

        # Step 5: Send to Stream Chat
        try:
            channel = chat_client.channel("messaging", request.channel_id)
            channel.send_message({"text": full_message}, user_id="ai-assistant")
        except Exception as stream_error:
            print(f"Stream Chat error: {stream_error}")

        return {"message": full_message}


    except Exception as e:
        print("AI request failed:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI request failed: {e}")


@router.post("/token")
def get_token(request: TokenRequest):
    # Generate token for the requested user
    token = chat_client.create_token(request.userId)

    # Only update user data for the main user, not the AI assistant
    if request.userId == "js-user":
        try:
            chat_client.update_user({
                "id": "js-user",
                "name": "User",
            })
        except Exception as e:
            print(f"Warning: Could not update user data: {e}")

    return {"token": token}