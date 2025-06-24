import requests
import json
import os
from dotenv import load_dotenv

def search_autodoc(query, api_key):
    """
    Make a GET request to the Piloterr autodoc search API
    
    Args:
        query (str): The search query URL
        api_key (str): Your API key
    
    Returns:
        dict: API response as JSON
    """
    url = "https://piloterr.com/api/v2/autodoc/search"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    params = {
        "query": query
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Replace with your actual API key
    load_dotenv()
    API_KEY = os.getenv("PILOTERR_API_KEY")

    keyword = "0+986+495+169"
    
    # The query from your curl command
    QUERY = f"https://www.auto-doc.fr/search?keyword={keyword}"
    
    result = search_autodoc(QUERY, API_KEY)
    
    if result:
        print("API Response:")
        print(json.dumps(result, indent=2))
    else:
        print("Failed to get response from API")