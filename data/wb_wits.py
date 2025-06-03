import requests
import json
import os


def fetch_tariff_data(reporter_codes, partner_code="000", product_codes="All", year=2023):
    """
    Fetch WITS tariff data for one or more reporter countries and optional list of products.

    Parameters:
        reporter_codes (str or list): One or more numeric reporter codes (e.g. '840' or ['840', '156'])
        partner_code (str): Partner ISO numeric code (default '000' = World)
        product_codes (str or list): 'All' or list of HS6 codes (e.g. ['870810', '870829'])
        year (int): Year to query

    Returns:
        dict or None: JSON response or None if request failed.
    """
    # Format reporter(s)
    if isinstance(reporter_codes, list):
        reporter_param = ";".join(reporter_codes)
    else:
        reporter_param = reporter_codes

    # Format product(s)
    if isinstance(product_codes, list):
        product_param = ";".join(product_codes)
    else:
        product_param = product_codes  # Either "All" or a single code

    # Build URL
    url = (
        f"https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/"
        f"reporter/{reporter_param}/partner/{partner_code}/product/{product_param}/"
        f"year/{year}/datatype/reported?format=JSON"
    )

    print(f"🔍 Requesting: {url}")
    response = requests.get(url)

    if response.status_code == 200:
        print("Data retrieved successfully.")
        return response.json()
    else:
        print(f"Failed with status code: {response.status_code}")
        return None


def save_tariff_data(data, reporter_code, year, output_dir="tariff_data"):
    """
    Save tariff data to a JSON file.
    """
    if data is None:
        print("No data to save.")
        return

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"tariffs_{reporter_code}_{year}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Data saved to {filename}")


# ---------------------
# Example usage – Combine all into one file:
# ---------------------

automotive_parts = [
    "870810", "870821", "870829", "870830", "870840", "870850",
    "870860", "870870", "870880", "870891", "870892", "870893",
    "870894", "870899"
]
reporter_codes = ["840", "156"]  # USA and China
year = 2023

combined_data = {}

for reporter_code in reporter_codes:
    data = fetch_tariff_data(reporter_codes=reporter_code, product_codes=automotive_parts, year=year)
    if data:
        combined_data[reporter_code] = data
    else:
        print(f"Skipping {reporter_code} due to fetch failure.")

# Save all data to one file
output_dir = "tariff_data"
os.makedirs(output_dir, exist_ok=True)
filename = os.path.join(output_dir, f"combined_tariffs_{year}.json")

with open(filename, "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2)

print(f"All data saved to {filename}")