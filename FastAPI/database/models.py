from sqlmodel import SQLModel, Field
from sqlalchemy import ForeignKeyConstraint
from typing import Optional

class Manufacturers(SQLModel, table=True):
    manufacturerId: int = Field(primary_key=True)
    description: str

class Suppliers(SQLModel, table=True):
    supplierId: int = Field(primary_key=True)
    supplierName: str

class DataSource(SQLModel, table=True):
    dataSourceId: int = Field(primary_key=True)
    dataSourceName: str

class Models(SQLModel, table=True):
    modelSeriesId: int = Field(primary_key=True)
    description: str
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")

class Vehicle(SQLModel, table=True):
    vehicleId: int = Field(primary_key=True)
    description: str
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")
    modelSeriesId: int = Field(foreign_key="models.modelSeriesId")

class Category(SQLModel, table=True):
    categoryId: int = Field(primary_key=True)
    description: str
    parentId: Optional[int] = Field(default=None, foreign_key="category.categoryId")
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")
    vehicleId: int = Field(foreign_key="vehicle.vehicleId")

class Parts(SQLModel, table=True):
    productGroupId: int = Field(primary_key=True)
    description: str
    categoryId: int = Field(foreign_key="category.categoryId")
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId")
    vehicleId: int = Field(foreign_key="vehicle.vehicleId")

class Articles(SQLModel, table=True):
    articleNo: str = Field(primary_key=True)
    articleProductName: str
    productId: int
    price: Optional[float] = None
    priceSource: Optional[int] = None
    countryOfOrigin: Optional[str] = None
    countryOfOriginSource: Optional[str] = None
    supplierId: int = Field(foreign_key="suppliers.supplierId", primary_key=True)

class ArticleVehicleLink(SQLModel, table=True):
    articleNo: str = Field(primary_key=True)
    supplierId: int = Field(primary_key=True)
    manufacturerId: int = Field(foreign_key="manufacturers.manufacturerId", primary_key=True)
    vehicleId: int = Field(foreign_key="vehicle.vehicleId", primary_key=True)
    productGroupId: int = Field(foreign_key="parts.productGroupId", primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["articleNo", "supplierId"],
            ["articles.articleNo", "articles.supplierId"],
            ondelete="CASCADE"
        ),
    )