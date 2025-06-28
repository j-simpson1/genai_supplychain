from sqlmodel import create_engine

DATABASE_URL = "postgresql://devuser:devpass@localhost:5432/devdb"
engine = create_engine(DATABASE_URL, echo=True)