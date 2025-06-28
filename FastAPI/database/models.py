from sqlmodel import SQLModel, Field
from typing import Optional

class Manufacturers(SQLModel, table=True):
    manufacturerId: int = Field(primary_key=True)
    description: str

class Models(SQLModel, table=True):
    modelSeriesId: int = Field(primary_key=True)
    description: str
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")

class Vehicle(SQLModel, table=True):
    vehicleId: int = Field(primary_key=True)
    description: str
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")
    modelSeriesId: int = Field(foreign_key="models.modelSeriesId")

class Parts(SQLModel, table=True):
    productGroupId: int = Field(primary_key=True)
    Description: str
    parent_id: Optional[int] = Field(default=None, foreign_key="category.id")
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")
    vehicleId: int = Field(foreign_key="vehicle.vehicleId")

class ArticleVehicleLink(SQLModel, table=True):
    articleNo: str = Field(foreign_key="articles.articleNo", primary_key=True)
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId", primary_key=True)
    vehicleId: int = Field(foreign_key="vehicle.vehicleId", primary_key=True)
    productGroupId: int = Field(foreign_key="parts.productGroupId", primary_key=True)

class Articles(SQLModel, table=True):
    articleNo: str = Field(primary_key=True)
    articleProductName:str
    productId: int
    price: Optional[float] = None
    supplierId: int = Field(foreign_key="suppliers.supplierId", primary_key=True)

class Suppliers(SQLModel, table=True):
    supplierId: int = Field(primary_key=True)
    supplierName: str


