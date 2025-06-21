import requests
import msal
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
app_id = os.getenv("POWER_BI_CLIENT_ID")
tenant_id = os.getenv("POWER_BI_TENANT_ID")

# Define authority and scopes
authority_url = f"https://login.microsoftonline.com/{tenant_id}"
scopes = ['https://analysis.windows.net/powerbi/api/.default']

# Step 1: Use Device Code Flow to get token
client = msal.PublicClientApplication(app_id, authority=authority_url)

flow = client.initiate_device_flow(scopes=scopes)
if "user_code" not in flow:
    raise ValueError("Failed to initiate device flow")

# Instruct user to authenticate
print(flow["message"])  # Follow the printed instructions

# Wait for user to complete authentication
response = client.acquire_token_by_device_flow(flow)

if "access_token" not in response:
    raise Exception(f"Authentication failed: {response.get('error_description')}")

access_token = response["access_token"]

# Step 2: Use access token to call Power BI API
endpoint = 'https://api.powerbi.com/v1.0/myorg/groups'
headers = {
    'Authorization': f'Bearer {access_token}'
}

response_request = requests.get(endpoint, headers=headers)
if response_request.status_code == 200:
    result = response_request.json()
    for item in result['value']:
        print(item['name'])
else:
    print(f"Error calling Power BI API: {response_request.status_code}")
    print(response_request.text)