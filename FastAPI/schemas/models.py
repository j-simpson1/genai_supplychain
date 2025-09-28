from pydantic import BaseModel
from typing import Optional, Dict, Any, List


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
    alternativeSupplier: AlternativeSupplier
    selectedCategoryFilter: Optional[str] = None
    selectedManufacturingOrigin: Optional[str] = None
    partsData: List[Dict[str, Any]]
    aiProcessingResult: Optional[Dict[str, Any]] = None

class TokenRequest(BaseModel):
    userId: str

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    channel_id: str