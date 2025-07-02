import requests
import base64
import os
from dotenv import load_dotenv

# --------------------
# Replace these with your Sandbox credentials
load_dotenv()
CLIENT_ID = os.getenv("EBAY_APP_ID")
CLIENT_SECRET = os.getenv("EBAY_CERT_ID")
# --------------------

# eBay OAuth token endpoint for Sandbox
TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

# eBay Browse API endpoint for Sandbox
SEARCH_URL = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"

def get_access_token(client_id, client_secret):
    """
    Get OAuth access token from eBay
    """
    # eBay requires HTTP Basic Auth: base64(client_id:client_secret)
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    token = response.json()["access_token"]
    return token

def search_car_parts(access_token, query="alternator", limit=5):
    """
    Search for car parts by keyword
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "q": query,
        "limit": str(limit)
    }

    response = requests.get(SEARCH_URL, headers=headers, params=params)
    response.raise_for_status()
    results = response.json()
    return results

def main():
    print("Getting OAuth token...")
    token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    print("Token retrieved.\n")

    print("Searching for car parts...")
    query = "alternator"  # You can change this to "brake pad", "radiator", etc.
    results = search_car_parts(token, query, limit=5)

    print("\nResults:")
    items = results.get("itemSummaries", [])
    if not items:
        print("No items found.")
    else:
        for i, item in enumerate(items, 1):
            print(f"{i}. {item}\n")

if __name__ == "__main__":
    main()