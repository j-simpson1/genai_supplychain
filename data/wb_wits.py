import requests
import pandas as pd
import numpy as np
import xmltodict
from IPython.display import display

# Updated to use HTTPS and correct WITS API endpoint
endpoint = "https://wits.worldbank.org/API/V1/SDMX/V21/rest"
path = '/'.join([endpoint, 'dataflow', 'wbg_wits'])

print(f"Requesting URL: {path}")
response = requests.get(path)
print(f"Status Code: {response.status_code}")
print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")

if response.status_code == 200:
    try:
        # Convert XML Response to Dictionary Object
        response_dict = xmltodict.parse(response.text)

        # Print the top-level keys to understand the structure
        print("Top-level keys in response:")
        print(list(response_dict.keys()))

        # Navigate through the SDMX structure
        # SDMX responses typically have a different structure than your original expectation
        if 'message:Structure' in response_dict:
            structure_data = response_dict['message:Structure']
        elif 'mes:Structure' in response_dict:
            structure_data = response_dict['mes:Structure']
        elif 'Structure' in response_dict:
            structure_data = response_dict['Structure']
        else:
            # Print the structure to understand the format
            print("Full response structure (first 2000 chars):")
            import json

            print(json.dumps(response_dict, indent=2)[:2000])


            # Look for dataflows in the structure
            def find_dataflows(data, path=""):
                if isinstance(data, dict):
                    if 'Dataflow' in data:
                        print(f"Found Dataflow at path: {path}")
                        return data['Dataflow']
                    for key, value in data.items():
                        result = find_dataflows(value, f"{path}.{key}" if path else key)
                        if result is not None:
                            return result
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        result = find_dataflows(item, f"{path}[{i}]")
                        if result is not None:
                            return result
                return None


            dataflows_raw = find_dataflows(response_dict)
            if dataflows_raw is None:
                raise KeyError("Could not find 'Dataflow' in response structure")

        if 'dataflows_raw' not in locals():
            # Standard SDMX structure navigation
            if 'Structures' in structure_data and 'Dataflows' in structure_data['Structures']:
                dataflows_raw = structure_data['Structures']['Dataflows']['Dataflow']
            elif 'Dataflows' in structure_data:
                dataflows_raw = structure_data['Dataflows']['Dataflow']
            else:
                print("Available keys in structure_data:")
                print(list(structure_data.keys()) if isinstance(structure_data, dict) else "Not a dictionary")
                raise KeyError("Expected nested structure not found")

        # Handle both single dataflow and list of dataflows
        if not isinstance(dataflows_raw, list):
            dataflows_raw = [dataflows_raw]

        # Normalize to pandas dataframe
        dataflows = pd.json_normalize(dataflows_raw)

        print("Available columns in dataflows:")
        print(dataflows.columns.tolist())
        print("\nSample data:")
        print(dataflows.head())

        # Try to filter for English versions if language columns exist
        filtered_dataflows = dataflows.copy()

        # Look for language-specific filtering
        name_lang_cols = [col for col in dataflows.columns if 'Name' in col and 'xml:lang' in col]
        desc_lang_cols = [col for col in dataflows.columns if 'Description' in col and 'xml:lang' in col]

        if name_lang_cols and desc_lang_cols:
            name_col = name_lang_cols[0]
            desc_col = desc_lang_cols[0]
            filtered_dataflows = dataflows[
                (dataflows[name_col] == 'en') &
                (dataflows[desc_col] == 'en')
                ]
            print(f"Filtered by language using columns: {name_col}, {desc_col}")

        # Create column mapping for final output
        available_cols = filtered_dataflows.columns.tolist()
        col_mapping = {}

        # More flexible column mapping
        for expected, patterns in [
            ('id', ['@id', 'id', 'ID']),
            ('agencyID', ['@agencyID', 'agencyID', 'AgencyID']),
            ('version', ['@version', 'version', 'Version']),
            ('isFinal', ['@isFinal', 'isFinal', 'IsFinal']),
            ('description', ['Description.#text', 'Description', 'Name.#text', 'Name']),
            ('datastructure', ['Structure.Ref.@id', 'datastructure', 'DataStructure'])
        ]:
            for pattern in patterns:
                if pattern in available_cols:
                    col_mapping[expected] = pattern
                    break

        print("\nColumn mapping found:")
        for k, v in col_mapping.items():
            print(f"  {k} -> {v}")

        # Create final dataframe with available columns
        if col_mapping:
            select_cols = [v for v in col_mapping.values()]
            final_dataflows = filtered_dataflows[select_cols].copy()

            # Rename columns
            rename_dict = {v: k for k, v in col_mapping.items()}
            final_dataflows = final_dataflows.rename(columns=rename_dict)

            # Display the results
            display_cols = [col for col in ['id', 'datastructure', 'description'] if col in final_dataflows.columns]

            print(f"\nFinal dataflows with columns: {display_cols}")
            if display_cols:
                display(final_dataflows[display_cols])
            else:
                print("No standard display columns found, showing all:")
                display(final_dataflows)
        else:
            print("Could not map any expected columns. Showing raw data:")
            display(filtered_dataflows)

    except Exception as e:
        print(f"Error processing response: {e}")
        print(f"\nFirst 1000 characters of response:")
        print(response.text[:1000])

else:
    print(f"Request failed with status code: {response.status_code}")
    print("Response content:")
    print(response.text[:1000])