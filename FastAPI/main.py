import pandas as pd
import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data.auto_parts.tecdoc import fetch_manufacturers, fetch_models, fetch_engine_types, fetch_categories_data, get_article_list, fetch_suppliers
from data.auto_parts.ai_analysis import rank_suppliers, generate_price_estimation
from services.article_selector import select_preferred_article

from typing import List, Dict, Any
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


@app.post("/ai/process-bill-of-materials")
async def process_bill_of_materials_with_ai(request: BillOfMaterialsRequest):
    try:
        print("Received request:")
        print(f"Vehicle Details: {request.vehicleDetails.dict()}")
        print(f"Number of parts: {len(request.parts)}")

        parts_df = pd.DataFrame([part.dict() for part in request.parts])

        article_numbers = []
        supplier_names = []
        product_names = []
        supplier_tiers = []

        manufacturer_id = request.metadata["manufacturerId"]
        manufacturer_name = request.vehicleDetails.manufacturerName
        vehicle_id = request.vehicleDetails.vehicleId

        suppliers = fetch_suppliers()
        shortened_suppliers = [supplier["supMatchCode"] for supplier in suppliers]

        ranked_suppliers = rank_suppliers(manufacturer_name, shortened_suppliers)

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

        price_estimattion = generate_price_estimation(parts_df)
        print(price_estimattion)

        print("Updated parts dataframe with selected articles:")
        print(parts_df)

        # Your AI processing logic here
        # For example, you might:
        # 1. Analyze the parts for compatibility
        # 2. Generate recommendations
        # 3. Predict maintenance schedules
        # 4. Optimize part configurations

        # Print the received information


        # Example AI processing result
        ai_result = {
            "status": "success",
            "vehicle_analysis": {
                "total_parts_analyzed": len(request.parts),
            },
            "ai_recommendations": [
                "Consider upgrading brake pads based on performance requirements",
                "Engine components show optimal configuration for fuel efficiency",
                "Recommended service interval: 12 months or 15,000 km"
            ],
            "processing_timestamp": datetime.datetime.now().isoformat(),
            "processing_duration_ms": 1500
        }

        return ai_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

# Examples

# @app.get("/")
# async def root():
#     return {"message": "Hello World"}
#
# @app.post("/items")
# def create_item(item: Item):
#     items.append(item)
#     return items
#
# @app.get("/items", response_model=list[Item])
# def list_items(limit: int = 10):
#     return items[0:limit]
#
# @app.get("/items/{item_id}", response_model=Item)
# def get_items(item_id: int) -> Item:
#     if item_id < len(items):
#         return items[item_id]
#     else:
#         raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_driver(uri, user, password):
    return GraphDatabase.driver(uri, auth=(user, password))