import requests
import json
import os
import time


def fetch_tariff_data(reporter_code, partner_code="000", product_codes="All", year=2023, output_dir="tariff_data"):
    # Convert product codes to API string
    if isinstance(product_codes, list):
        product_param = ";".join(product_codes)
    else:
        product_param = product_codes  # "All" or single string

    # Construct URL
    url = (
        f"https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/"
        f"reporter/{reporter_code}/partner/{partner_code}/product/{product_param}/"
        f"year/{year}/datatype/reported?format=JSON"
    )

    print(f"🔍 Fetching data for reporter={reporter_code}, year={year}, products={product_param}...")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()

            # Save to file
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f"tariffs_{reporter_code}_{year}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"✅ Data saved to {filename}")
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error occurred: {e}")


# ---------------------
# 🔧 Example usage:
# ---------------------

fetch_tariff_data(
    reporter_code="840",  # United States
    product_codes=["870322", "870323"],  # Example: car types
    year=2023
)

# Other examples:
# fetch_tariff_data("124", product_codes="All", year=2023)   # All products for Canada
# fetch_tariff_data("156", product_codes=["8708"], year=2022)  # Auto parts for China