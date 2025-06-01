import requests
import os
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("WTO_API_KEY")

# Base URL for the WTO Time Series API
BASE_URL = "https://api.wto.org/timeseries/v1/data"

# Parameters for the API request
params = {
    "i": "ITS_CS_QAX",      # Indicator: Trade in commercial services
    "ps": "2018-2025",      # Period: 2018 to 2025
    "fmt": "json"           # Response format
}

# Headers including the subscription key
headers = {
    "Ocp-Apim-Subscription-Key": API_KEY
}

def fetch_wto_services_data():
    try:
        response = requests.get(BASE_URL, params=params, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        print("✅ Data fetched successfully:")
        print(data)
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"❌ Other error occurred: {err}")

if __name__ == "__main__":
    fetch_wto_services_data()