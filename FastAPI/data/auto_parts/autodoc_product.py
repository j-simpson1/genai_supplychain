import requests
import json
import os
from dotenv import load_dotenv

def make_autodoc_request(product_url, api_key):
    """
    Make a request to the Piloterr API for AutoDoc product information
    """
    try:
        # API endpoint
        url = "https://piloterr.com/api/v2/autodoc/product"
        
        # Headers - make sure api_key is a string, not a tuple
        headers = {
            "Content-Type": "application/json",
            "x-api-key": str(api_key)  # Ensure it's a string
        }
        
        # Query parameters
        params = {
            "query": product_url
        }
        
        # Make the request
        response = requests.get(url, headers=headers, params=params)
        
        # Check if request was successful
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

# Usage example
if __name__ == "__main__":
    # Make sure your API key is a string, not a tuple
    load_dotenv()
    api_key = os.getenv("PILOTERR_API_KEY")
    product_url = "https://www.autodoc.co.uk/bosch/8168077"
    
    result = make_autodoc_request(product_url, api_key)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Request failed")