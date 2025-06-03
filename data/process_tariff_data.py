import json
import pandas as pd

# Load JSON
with open("tariff_data/combined_tariffs_2023.json", "r") as f:
    data = json.load(f)

reporter_map = {
    "840": "United States",
    "156": "China"
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

records = []

for reporter_code, content in data.items():
    series = content["dataSets"][0]["series"]
    country = reporter_map.get(reporter_code, reporter_code)

    for key, series_data in series.items():
        product_index = key.split(":")[2]
        hs_code, description = product_map.get(product_index, (None, None))
        if hs_code is None:
            continue
        observations = series_data["observations"]
        for _, values in observations.items():
            mfn = round(values[0], 3) if values[0] is not None else None
            records.append({
                "HS Code": hs_code,
                "Product Description": description,
                "Country": country,
                "MFN Tariff (%)": mfn
            })

# Long to wide format (pivot)
df = pd.DataFrame(records)
pivot_df = df.pivot(index=["HS Code", "Product Description"], columns="Country", values="MFN Tariff (%)").reset_index()

# Reorder columns: HS Code | Product Description | [country columns...]
cols = ["HS Code", "Product Description"] + [col for col in pivot_df.columns if
                                             col not in ["HS Code", "Product Description"]]
pivot_df = pivot_df[cols]

# Save
pivot_df.to_csv("tariff_data/tariff_data_pivot.csv", index=False)
print(pivot_df)