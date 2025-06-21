from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers, fetch_models, fetch_engine_types, fetch_categories_data, get_article_list, fetch_suppliers, fetch_countries
from FastAPI.data.auto_parts.ai_analysis import rank_suppliers, generate_price_estimation_and_country
from FastAPI.services.article_selector import select_preferred_article
from FastAPI.automotive_abm.run import run_simulation_with_plots

from FastAPI.schemas.models import Item, VehicleDetails, PartItem, CategoryItem, BillOfMaterialsRequest, AlternativeSupplier, SimulationRequest
from fastapi import APIRouter, HTTPException
import pandas as pd
import datetime

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
async def run_simulation(request: SimulationRequest):
    try:
        # Process the simulation based on the request data
        # This is where you would implement your simulation logic

        print("Parts data received:")
        parts_data = request.aiProcessingResult
        parts_df = pd.DataFrame(parts_data['parts_data'])
        parts_df = parts_df.drop(['level', 'supplierTier'], axis=1)
        print(parts_df)

        model = run_simulation_with_plots(parts_df, steps=24)

        # Example of a simulation result
        simulation_result = {
            "status": "success",
            "scenario": request.scenarioType,
            "results": {
                "cost_impact": model.get_cost_impact(),
                "supply_chain_analysis": model.get_supply_chain_analysis(),
                "risk_assessment": model.get_risk_assessment()
            },
            "timestamp": datetime.datetime.now().isoformat()
        }

        return simulation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")