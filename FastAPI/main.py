import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data.auto_parts.tecdoc import fetch_manufacturers, fetch_models, fetch_engine_types, fetch_categories_data, get_article_list, fetch_suppliers, fetch_countries
from data.auto_parts.ai_analysis import rank_suppliers, generate_price_estimation_and_country
from services.article_selector import select_preferred_article
from automotive_abm.run import run_simulation_with_plots


from typing import Optional, Dict, Any, List
import datetime

app = FastAPI()

class Item(BaseModel):
    text: str = None
    is_done: bool = False

class VehicleDetails(BaseModel):
    vehicleId: int
    manufacturerName: str
    modelName: str
    typeEngineName: str
    powerPs: str
    fuelType: str
    bodyType: str
    manufacturingOrigin: str

class PartItem(BaseModel):
    categoryId: str
    categoryName: str
    fullPath: str
    level: int

class CategoryItem(BaseModel):
    categoryId: str
    categoryName: str
    fullPath: str
    level: int
    hasChildren: bool

class BillOfMaterialsRequest(BaseModel):
    vehicleDetails: VehicleDetails
    parts: List[PartItem]
    categories: List[CategoryItem]
    metadata: Dict[str, Any]

class AlternativeSupplier(BaseModel):
    supplierCode: str
    country: str

class SimulationRequest(BaseModel):
    vehicleDetails: Dict[str, Any]
    scenarioType: str
    country: str
    tariffRate: float
    inflationRate: float
    dispatchCost: float
    alternativeSupplier: AlternativeSupplier
    selectedCategoryFilter: Optional[str] = None
    selectedManufacturingOrigin: Optional[str] = None
    partsData: List[Dict[str, Any]]
    aiProcessingResult: Optional[Dict[str, Any]] = None

items = []

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/manufacturers")
def retrieve_manufacturers():
    return fetch_manufacturers()

@app.get("/manufacturers/models")
def retrieve_models(id: int):
    return fetch_models(id)

@app.get("/manufacturers/models/engine_type")
def retrieve_engine_types(manufacturerId: int, modelSeriesId: int):
    return fetch_engine_types(manufacturerId, modelSeriesId)

@app.get("/manufacturers/models/engine_type/category_v3")
def retrieve_category_v3(vehicleId: int, manufacturerId: int):
    return fetch_categories_data(vehicleId, manufacturerId)

@app.get("/manufacturers/models/engine_type/category_v3/article_list")
def retrieve_article_list(manufacturerId: int, vehicleId: int, productGroupId: int):
    return get_article_list(manufacturerId, vehicleId, productGroupId)

@app.get("/suppliers")
def retrieve_suppliers():
    return fetch_suppliers()

@app.get("/countries")
def retrieve_countries():
    return fetch_countries()

@app.post("/ai/process-bill-of-materials")
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


@app.post("/run_simulation")
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
                "cost_impact",
                "supply_chain_analysis",
                "risk_assessment",
            },
            "timestamp": datetime.datetime.now().isoformat()
        }

        return simulation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")