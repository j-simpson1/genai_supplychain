from sqlmodel import SQLModel
from FastAPI.database.database import engine
from FastAPI.database.models import Manufacturers, Models, Vehicle, Parts, ArticleVehicleLink, Articles, Suppliers

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()