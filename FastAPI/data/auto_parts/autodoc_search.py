import requests
import json
import os
from dotenv import load_dotenv

def search_autodoc(keyword):
    """
    Make a GET request to the Piloterr autodoc search API
    
    Args:
        keyword (str): The search query keyword
    Returns:
        dict: API response as JSON
    """
    load_dotenv()
    api_key = os.getenv("PILOTERR_API_KEY")

    query = f"https://www.auto-doc.fr/search?keyword={keyword}"

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

    keyword = "82B0076"
    
    result = search_autodoc(keyword)
    
    if result:
        print("API Response:")
        print(json.dumps(result, indent=2))
    else:
        print("Failed to get response from API")