import msal
from dotenv import load_dotenv
import os

def get_access_token():

    load_dotenv()
    app_id = os.getenv("POWER_BI_CLIENT_ID")
    tenant_id = os.getenv("POWER_BI_TENANT_ID")

    authority_url = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ['https://analysis.windows.net/powerbi/api/.default']
    client = msal.PublicClientApplication(app_id, authority=authority_url)
    flow = client.initiate_device_flow(scopes=scopes)

    if "user_code" not in flow:
        raise ValueError("Failed to initiate device flow")

    print(flow["message"])
    result = client.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise Exception(f"Authentication failed: {result.get('error_description')}")
    return result["access_token"]
