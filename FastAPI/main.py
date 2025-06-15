from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from data.auto_parts.transform import transform_data_articles_list
from data.auto_parts.load import insert_article_data_into_neo4j
from data.auto_parts.tecdoc import get_articles_list, fetch_manufacturers, fetch_models, fetch_engine_types, fetch_categories_data

app = FastAPI()

class Item(BaseModel):
    text: str = None
    is_done: bool = False

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

def main():
    driver = get_driver(URI, USER, PASSWORD)

    # data = fetch_categories_data("140099", "111")
    # nodes, edges = parse_categories(data)
    # load_into_neo4j(nodes, edges)

    article_list = get_articles_list("0 986 495 169")
    transformed_article_list = transform_data_articles_list(article_list)
    insert_article_data_into_neo4j(driver, transformed_article_list)


if __name__ == "__main__":
    main()