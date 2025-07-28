import requests
import json
import os
import pandas as pd

# -------------------------
# Configurable parameters
# -------------------------
automotive_parts = [
    "870810", "870821", "870829", "870830", "870840", "870850",
    "870860", "870870", "870880", "870891", "870892", "870893",
    "870894", "870899"
]

# Top 50 automotive exporters (numeric WITS country codes)
reporter_codes = [
    "840","156","392","410","250","724","826","276","380","246",
    "528","344","756","410","792","124","826","826","554","203",
    "616","643","752","344","702","344","352","392","528","826",
    "620","191","554","124","276","208","348","196","352","756",
    "724","642","246","348","616","352","470","410","410","826"
]  # repeated values trimmed below

# Deduplicate codes
reporter_codes = list(sorted(set(reporter_codes)))

year = 2023
output_dir = "../tariff_data"
os.makedirs(output_dir, exist_ok=True)

# Country code map (simplified; should be fully expanded)
reporter_map = {
    "840": "United States", "156": "China", "392": "Japan",
    "410": "Korea, Rep.", "250": "France", "724": "Spain",
    "826": "United Kingdom", "276": "Germany", "380": "Italy",
    "246": "Finland", "528": "Netherlands", "344": "Hong Kong SAR, China",
    "756": "Switzerland", "792": "Turkey", "124": "Canada",
    "554": "New Zealand", "203": "Czech Republic", "616": "Poland",
    "643": "Russian Federation", "752": "Sweden", "702": "Singapore",
    "352": "Iceland", "620": "Portugal", "191": "Croatia",
    "208": "Denmark", "348": "Hungary", "196": "Cyprus",
    "642": "Romania", "470": "Malta"
    # Extend this map if needed
}

product_map = {
    "0": ("870810", "Bumpers and parts thereof"),
    "1": ("870821", "Safety seat belts"),
    "2": ("870829", "Other"),
    "3": ("870830", "Brakes and servo-brakes"),
    "4": ("870840", "Gear boxes and parts thereof"),
    "5": ("870850", "Drive-axles"),
    "6": ("870870", "Road wheels and parts"),
    "7": ("870880", "Suspension systems"),
    "8": ("870891", "Radiators"),
    "9": ("870892", "Silencers and exhaust pipes"),
    "10": ("870893", "Clutches"),
    "11": ("870894", "Steering wheels"),
    "12": ("870899", "Other automotive parts")
}

# -------------------------
# Fetch tariff data
# -------------------------
def fetch_tariff_data(reporter_code, product_codes="All", partner_code="000", year=2023):
    if isinstance(product_codes, list):
        product_param = ";".join(product_codes)
    else:
        product_param = product_codes

    url = (
        f"https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/"
        f"reporter/{reporter_code}/partner/{partner_code}/product/{product_param}/"
        f"year/{year}/datatype/reported?format=JSON"
    )
    print(f"🔍 Requesting: {url}")
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Collect all data
combined_data = {}
for reporter_code in reporter_codes:
    data = fetch_tariff_data(reporter_code, product_codes=automotive_parts, year=year)
    if data:
        combined_data[reporter_code] = data
    else:
        print(f"Skipping {reporter_code} due to fetch failure.")

# Save combined JSON
combined_filename = os.path.join(output_dir, f"combined_tariffs_{year}.json")
with open(combined_filename, "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2)
print(f"Combined tariff data saved to {combined_filename}")

# -------------------------
# Process & Pivot
# -------------------------
records = []
for reporter_code, content in combined_data.items():
    series = content["dataSets"][0]["series"]
    country = reporter_map.get(reporter_code, reporter_code)
    for key, series_data in series.items():
        product_index = key.split(":")[2]
        hs_code, description = product_map.get(product_index, (None, None))
        if hs_code is None:
            continue
        for _, values in series_data["observations"].items():
            mfn = round(values[0], 3) if values[0] is not None else None
            records.append({
                "HS Code": hs_code,
                "Product Description": description,
                "Country": country,
                "MFN Tariff (%)": mfn
            })

df = pd.DataFrame(records)
pivot_df = df.pivot(index=["HS Code", "Product Description"], columns="Country", values="MFN Tariff (%)").reset_index()
pivot_cols = ["HS Code", "Product Description"] + [c for c in pivot_df.columns if c not in ["HS Code", "Product Description"]]
pivot_df = pivot_df[pivot_cols]

pivot_filename = os.path.join(output_dir, "tariff_data_pivot.csv")
pivot_df.to_csv(pivot_filename, index=False)
print(f"Pivot CSV saved to {pivot_filename}")

# -------------------------
# Compute Average Tariffs
# -------------------------
avg_tariffs = pivot_df.drop(columns=["HS Code", "Product Description"]).mean(numeric_only=True).round(3)
avg_tariff_dict = avg_tariffs.to_dict()

avg_filename = os.path.join(output_dir, "avg_tariff_dict.json")
with open(avg_filename, "w") as f:
    json.dump(avg_tariff_dict, f, indent=2)

print(f"Average tariffs by country: {avg_tariff_dict}")
print(f"Saved average tariff dictionary to {avg_filename}")