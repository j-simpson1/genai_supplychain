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

# 5) Get Articles List
# GET /articles/list/vehicle-id/{vehicleId}/product-group-id/{productGroupId}/manufacturer-id/{manufacturerId}/lang-id/{langId}/country-filter-id/{countryFilterId}/type-id/{typeId}

# 6) Get Complete Details for Article Number
# GET /articles/article-number-details/lang-id/{langId}/country-filter-id/{countryFilterId}/article-no/{articleNumber}


# Example TOYOTA RAV 4 V
langId = "4" # English (GB)
manufacturerId = "111" # TOYOTA
modelSeriesId = "39268" # RAV 4 V (_A5_, _H5_)
typeId = "1" # Automobile
countryFilterId = "91" # Great Britain
vehicleId = "140099" # 2.5 Hybrid AWD (AXAH54)
productGroupId = "100030" # Brake Pad
articleNumber = "0 986 495 169" # Bosch
articleId = "71734"
supplierId = "30" # Bosch

def fetch_manufacturers():
	url = f"https://tecdoc-catalog.p.rapidapi.com/manufacturers/list/lang-id/4/country-filter-id/91/type-id/1"

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
	}

	response = requests.get(url, headers=headers)
	return response.json()

def fetch_models(manufacturerId):

	url = f"https://tecdoc-catalog.p.rapidapi.com/models/list/manufacturer-id/{manufacturerId}/lang-id/4/country-filter-id/91/type-id/1"

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
	}

	response = requests.get(url, headers=headers)
	return response.json()

def fetch_engine_types(manufacturerId, modelSeriesId):

	url = f"https://tecdoc-catalog.p.rapidapi.com/types/list-vehicles-types/{modelSeriesId}/manufacturer-id/{manufacturerId}/lang-id/4/country-filter-id/91/type-id/1"

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
	}

	response = requests.get(url, headers=headers)
	return response.json()

def fetch_categories_data(vehicleId, manufacturerId, langId="4", countryFilterId="91", typeId="1"):
	url = f"https://tecdoc-catalog.p.rapidapi.com/category/category-products-groups-variant-3/{vehicleId}/manufacturer-id/{manufacturerId}/lang-id/{langId}/country-filter-id/{countryFilterId}/type-id/{typeId}"

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
	}

	response = requests.get(url, headers=headers)
	return response.json()

# to check on Rapid API
def get_article_list(manufacturerId, vehicleId, productGroupId):

	url = f"https://tecdoc-catalog.p.rapidapi.com/articles/list/vehicle-id/{vehicleId}/product-group-id/{productGroupId}/manufacturer-id/{manufacturerId}/lang-id/4/country-filter-id/91/type-id/1"

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
	}

	response = requests.get(url, headers=headers)
	return response.json()

def get_article_details(articleNumber, countryFilterId="91", langId="4"):

	url = "https://tecdoc-catalog.p.rapidapi.com/articles/article-number-details-post"

	payload = {
		"langId": f"{langId}",
		"countryFilterId": f"{countryFilterId}",
		"articleNo": f"{articleNumber}"
	}

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com",
		"Content-Type": "application/x-www-form-urlencoded"
	}

	response = requests.post(url, data=payload, headers=headers)
	return response.json()

def fetch_suppliers():

	url = "https://tecdoc-catalog.p.rapidapi.com/suppliers/list"

	load_dotenv()
	headers = {
		"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
		"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
	}

	response = requests.get(url, headers=headers)

	return response.json()

# '100006': {
# 	'text': 'Braking System',
# 	'children': {
# 		'100027': {
# 			'text': 'Brake Caliper',
# 			'children': {
# 				'100807': {
# 					'text': 'Brake Caliper Mounting',
# 					'children': []
# 				},
# 				'100806': {
# 					'text': 'Brake Caliper Parts',
# 					'children': []
# 				}
# 			}
# 		},
# 		'102208': {
# 			'text': 'Brake Fluid',
# 			'children': []
# 		},
# 		'100035': {
# 			'text': 'Brake Hoses',
# 			'children': []
# 		},
# 		'100626': {
# 			'text': 'Disc Brake',
# 			'children': {
# 				'100630': {
# 					'text': 'Accessories/Parts',
# 					'children': []
# 				},
# 				'100032': {
# 					'text': 'Brake Disc',
# 					'children': []
# 				},
# 				'100030': {
# 					'text': 'Brake Pad',
# 					'children': []
# 				}
# 			}
# 		},
# 		'102224': {
# 			'text': 'High Performance Brakes',
# 			'children': {
# 				'102225': {
# 					'text': 'High Performance Brake Kit',
# 					'children': []
# 				}
# 			}
# 		}
# 	}
# },


# supId:"30"
# supBrand:"BOSCH"
# supMatchCode:"BOSCH"
# supLogoName:"BOSCH.PNG"