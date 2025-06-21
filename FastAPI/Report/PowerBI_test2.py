import requests
import msal
from dotenv import load_dotenv
import os
import pandas as pd
import json

# Load environment variables
load_dotenv()
app_id = os.getenv("POWER_BI_CLIENT_ID")
tennant_id = os.getenv("POWER_BI_TENANT_ID")
username = os.getenv("POWER_BI_USERNAME")
password = os.getenv("POWER_BI_PASSWORD")

# Authentication details
authority_url = 'https://login.microsoftonline.com/' + tennant_id
scopes = ['https://analysis.windows.net/powerbi/api/.default']

# Step 1: Generate Power BI Access Token
client = msal.PublicClientApplication(app_id, authority=authority_url)
response = client.acquire_token_by_username_password(username=username, password=password, scopes=scopes)
access_id = response.get('access_token')

# Step 2: Retrieve list of workspaces (groups)
endpoint = 'https://api.powerbi.com/v1.0/myorg/groups'
headers = {
    'Authorization': f'Bearer {access_id}'
}
response_request = requests.get(endpoint, headers=headers)

# ✅ FIXED: Add this line to store the parsed JSON
result = response_request.json()

# Set your target workspace
target_workspace_name = "GenAI_supplychain"
workspace_id = None

# Step 3: Match the workspace name
for item in result['value']:
    if item['name'] == target_workspace_name:
        workspace_id = item['id']
        print(f"Found workspace: {target_workspace_name} with ID: {workspace_id}")
        break

if workspace_id is None:
    raise ValueError(f"Workspace '{target_workspace_name}' not found.")

# --- Sample DataFrame ---
df = pd.DataFrame({
    "Product": ["Widget", "Gadget", "Thingamajig"],
    "Quantity": [10, 25, 15],
    "Price": [9.99, 14.99, 7.50]
})

# --- Define Dataset Structure ---
dataset_name = "GenAI_Supply_Chain_Demo"
dataset_def = {
    "name": dataset_name,
    "defaultMode": "Push",
    "tables": [
        {
            "name": "Inventory",
            "columns": [
                {"name": "Product", "dataType": "string"},
                {"name": "Quantity", "dataType": "Int64"},
                {"name": "Price", "dataType": "Double"}
            ]
        }
    ]
}

# --- Create Dataset in Power BI Workspace ---
create_dataset_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets'
headers['Content-Type'] = 'application/json'  # reuse your access_token header

create_response = requests.post(create_dataset_url, headers=headers, json=dataset_def)

if create_response.status_code == 201:
    dataset_id = create_response.json()['id']
    print(f"✅ Dataset '{dataset_name}' created with ID: {dataset_id}")
else:
    print(f"❌ Failed to create dataset: {create_response.status_code} - {create_response.text}")
    exit()

# --- Push Rows to the Table ---
push_rows_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/tables/Inventory/rows'
rows_payload = {"rows": df.to_dict(orient='records')}

push_response = requests.post(push_rows_url, headers=headers, data=json.dumps(rows_payload))

if push_response.status_code == 200:
    print("✅ Data successfully pushed to Power BI.")
else:
    print(f"❌ Failed to push data: {push_response.status_code} - {push_response.text}")