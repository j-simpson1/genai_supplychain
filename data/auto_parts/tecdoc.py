import requests
import os
from dotenv import load_dotenv

#API calls

# Get All Manufacturers by Type ID, Language ID & Country ID
# GET /manufacturers/list/lang-id/4/country-filter-id/91/type-id/1"

# 2) Get Models List by Manufacturer ID
# GET /models/list/manufacturer-id/{manufacturerId}/lang-id/{langId}/country-filter-id/{countryFilterId}/type-id/{typeId}

# 3) Get All Vehicle Engine Types
# GET /types/list-vehicles-types/{modelSeriesId}/manufacturer-id/{manufacturerId}/lang-id/{langId}/country-filter-id/{countryFilterId}/type-id/{typeId}

# 4) Get Category v3
# GET /category/category-products-groups-variant-3/{vehicleId}/manufacturer-id/{manufacturerId}/lang-id/{langId}/country-filter-id/{countryFilterId}/type-id/{typeId}


# Example TOYOTA RAV 4 V
langId = "4" # English (GB)
manufacturerId = "111" # TOYOTA
modelSeriesId = "39268" # RAV 4 V (_A5_, _H5_)
typeId = "1" # Automobile
countryFilterId = "91" # Great Britain
vehicleId = "140099" # 2.5 Hybrid AWD (AXAH54)

url = f"https://tecdoc-catalog.p.rapidapi.com/category/category-products-groups-variant-3/{vehicleId}/manufacturer-id/{manufacturerId}/lang-id/{langId}/country-filter-id/{countryFilterId}/type-id/{typeId}"

load_dotenv()
headers = {
	"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
	"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
}



response = requests.get(url, headers=headers)

print(response.json())