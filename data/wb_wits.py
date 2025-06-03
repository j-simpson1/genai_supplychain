import requests
import json
import os


def fetch_tariff_data(reporter_code, partner_code="000", product_codes="All", year=2023):
    """
    Fetch tariff data from WITS API.

    Returns:
        dict or None: JSON response as Python dict, or None if failed.
    """
    # Format product codes
    if isinstance(product_codes, list):
        product_param = ";".join(product_codes)
    else:
        product_param = product_codes

    # Construct request URL
    url = (
        f"https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/"
        f"reporter/{reporter_code}/partner/{partner_code}/product/{product_param}/"
        f"year/{year}/datatype/reported?format=JSON"
    )

    print(f"🔍 Requesting: {url}")
    response = requests.get(url)

    if response.status_code == 200:
        print("✅ Data retrieved successfully.")
        return response.json()
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        return None


def save_tariff_data(data, reporter_code, year, output_dir="tariff_data"):
    """
    Save tariff data to a JSON file.
    """
    if data is None:
        print("⚠️ No data to save.")
        return

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"tariffs_{reporter_code}_{year}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"📁 Data saved to {filename}")


# ---------------------
# 🔧 Example usage:
# ---------------------

reporter = "840"  # United States
products = ["870322", "870323"]  # Example HS6 codes for vehicles
year = 2023

# Step 1: Fetch
tariff_data = fetch_tariff_data(reporter_code=reporter, product_codes=products, year=year)

# Step 2: Save
save_tariff_data(tariff_data, reporter_code=reporter, year=year)