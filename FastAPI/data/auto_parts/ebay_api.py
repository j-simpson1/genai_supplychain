import requests
import base64
import os
from dotenv import load_dotenv

# --------------------
load_dotenv()
CLIENT_ID = os.getenv("EBAY_APP_ID")
CLIENT_SECRET = os.getenv("EBAY_CERT_ID")
# --------------------

def get_access_token(client_id, client_secret):
    """
    Get OAuth access token from eBay
    """
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

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
    print("Access token obtained:")
    print(token)
    return token

def safe_get(url, headers=None, params=None):
    """
    Wrapper for GET requests with safeguards:
    - Enforce GET method
    - Allow only Browse API URLs
    """
    BROWSE_API_BASE = "https://api.ebay.com/buy/browse"

    assert url.startswith(BROWSE_API_BASE), f"Blocked request: URL {url} is outside Browse API."
    response = requests.get(url, headers=headers, params=params)
    return response

def ebay_search_car_parts(access_token, query, limit=5):
    """
    Search for car parts by keyword with marketplace and affiliate tracking.
    Only allows Browse API GET calls.
    """

    SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=YOUR_CAMPAIGN_ID,affiliateReferenceId=YOUR_REF_ID"
    }

    params = {
        "q": query,
        "limit": str(limit)
    }

    # Use safe_get instead of requests.get directly
    response = safe_get(SEARCH_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def main():
    print("Getting OAuth token...")
    try:
        token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    except requests.HTTPError as e:
        print("Failed to get token:", e.response.text)
        raise
    print("\nToken retrieved.\n")

    print("Searching for car parts...")
    query = "53012145282"
    limit = 5
    results = ebay_search_car_parts(token, query, limit)

    print("\nResults:")
    items = results.get("itemSummaries", [])
    if not items:
        print("No items found.")
    else:
        for i, item in enumerate(items, 1):
            title = item.get("title", "No Title")
            url = item.get("itemWebUrl", "No URL")
            price = item.get("price", {}).get("value", "N/A")
            currency = item.get("price", {}).get("currency", "")
            print(f"{i}. {title}\n   {url}\n   {price} {currency}\n")

if __name__ == "__main__":
    main()