import pandas as pd
import requests
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from msal import PublicClientApplication

def upload_to_powerbi(
        csv_path: str,
        access_token: str,
        dataset_name: str = "Supply Chain Simulation",
        workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload simulation data from CSV to Power BI

    Args:
        csv_path: Path to the CSV file to upload
        access_token: Power BI access token
        dataset_name: Name for the dataset in Power BI
        workspace_id: Optional workspace ID (uses 'My Workspace' if None)

    Returns:
        Dictionary with information about the created dataset
    """
    # Verify file exists
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Set up headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Define the dataset structure based on CSV columns
    columns = []
    for col_name, dtype in df.dtypes.items():
        if pd.api.types.is_numeric_dtype(dtype):
            if pd.api.types.is_integer_dtype(dtype):
                datatype = "Int64"
            else:
                datatype = "Double"
        else:
            datatype = "String"

        columns.append({"name": col_name, "dataType": datatype})

    # Define dataset JSON
    dataset_json = {
        "name": dataset_name,
        "tables": [{
            "name": "SimulationResults",
            "columns": columns
        }]
    }

    # Construct API endpoint
    api_endpoint = "https://api.powerbi.com/v1.0/myorg"
    if workspace_id:
        api_endpoint += f"/groups/{workspace_id}"
    api_endpoint += "/datasets"

    # Create the dataset
    print(f"Creating dataset '{dataset_name}' in Power BI...")
    response = requests.post(
        api_endpoint,
        headers=headers,
        json=dataset_json
    )

    if response.status_code != 201 and response.status_code != 200:
        print(f"Failed to create dataset: {response.text}")
        raise Exception(f"Failed to create dataset: {response.status_code}")

    dataset_info = response.json()
    dataset_id = dataset_info['id']
    print(f"Dataset created with ID: {dataset_id}")

    # Prepare rows data
    rows_data = {
        "rows": df.to_dict(orient="records")
    }

    # Push data to the dataset
    push_endpoint = f"{api_endpoint}/{dataset_id}/tables/SimulationResults/rows"
    print(f"Pushing {len(df)} rows of data to Power BI...")

    push_response = requests.post(
        push_endpoint,
        headers=headers,
        json=rows_data
    )

    if push_response.status_code != 200:
        print(f"Failed to push data: {push_response.text}")
        raise Exception(f"Failed to push data: {push_response.status_code}")

    print("Data uploaded successfully to Power BI!")

    # Return information about the created dataset
    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "rows_uploaded": len(df),
        "columns": [col["name"] for col in columns]
    }


def get_access_token() -> str:
    load_dotenv()
    app_id = os.getenv("POWER_BI_CLIENT_ID")
    tenant_id = os.getenv("POWER_BI_TENANT_ID")
    username = os.getenv("POWER_BI_USERNAME")
    password = os.getenv("POWER_BI_PASSWORD")

    authority_url = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ['https://analysis.windows.net/powerbi/api/.default']

    client = PublicClientApplication(app_id, authority=authority_url)
    result = client.acquire_token_by_username_password(username, password, scopes=scopes)

    if "access_token" in result:
        print("✅ Access token obtained via username/password!")
        return result["access_token"]
    else:
        print(f"❌ Failed to get access token: {result.get('error_description')}")
        return None


def test_powerbi_upload():
    # Make sure environment variables are loaded
    load_dotenv()

    # Add this debug code
    workspace_id = os.getenv("POWER_BI_WORKSPACE_ID")
    print(f"Loaded workspace ID: {workspace_id}")

    # Get the access token
    access_token = get_access_token()
    if not access_token:
        print("Failed to get access token. Check your environment variables.")
        return

    # Define test CSV path - update this to point to a real CSV file in your project
    test_csv_path = os.path.join("exports", "test_simulation.csv")

    # If you don't have a test file, create a simple one
    if not os.path.exists(test_csv_path):
        import pandas as pd
        # Create exports directory if it doesn't exist
        os.makedirs(os.path.dirname(test_csv_path), exist_ok=True)
        # Create simple test data
        test_data = pd.DataFrame({
            "agent_id": [1, 2, 3],
            "value": [10.5, 20.1, 30.7],
            "category": ["A", "B", "C"]
        })
        test_data.to_csv(test_csv_path, index=False)
        print(f"Created test CSV at {test_csv_path}")

    # Load API key from .env
    load_dotenv()

    # Test the upload function
    try:
        result = upload_to_powerbi(
            csv_path=test_csv_path,
            access_token=access_token,
            dataset_name="Test Upload Dataset",
            workspace_id="188dcf61-6524-4b27-93ce-222438bb3545"  # Hardcoded for testing
        )
        print("Upload successful!")
        print(f"Dataset ID: {result['dataset_id']}")
        print(f"Rows uploaded: {result['rows_uploaded']}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")


if __name__ == "__main__":
    test_powerbi_upload()

