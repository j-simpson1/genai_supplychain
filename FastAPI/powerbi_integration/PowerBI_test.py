import requests
import msal
from dotenv import load_dotenv
import os

load_dotenv()
app_id = os.getenv("POWER_BI_CLIENT_ID")
tennant_id = os.getenv("POWER_BI_TENANT_ID")
username = os.getenv("POWER_BI_USERNAME")
password = os.getenv("POWER_BI_PASSWORD")

authority_url = 'https://login.microsoftonline.com/' + tennant_id
scopes = ['https://analysis.windows.net/powerbi/api/.default']

# Step 1: Generate Power BI Access Token
client = msal.PublicClientApplication(app_id, authority=authority_url)
response = client.acquire_token_by_username_password(username=username, password=password, scopes=scopes)
# print(response)
# print(response.keys())
# print(response.get('scope'))

access_id = response.get('access_token')

# Step 2.
endpoint = 'https://api.powerbi.com/v1.0/myorg/groups'
headers = {
    'Authorization': f'Bearer {access_id}'
}
response_request = requests.get(endpoint, headers=headers)
if response_request.status_code == 200:
    result = response_request.json()
    for item in result['value']:
        print(item['name'])