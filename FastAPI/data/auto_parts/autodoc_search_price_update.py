import requests
import json
import os
import pandas as pd
import random
import time
from dotenv import load_dotenv

EUR_TO_GBP = 0.871  # Conversion rate

def load_parts_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    return pd.read_csv(file_path)

def search_autodoc(keyword):
    load_dotenv()
    api_key = os.getenv("PILOTERR_API_KEY")
    query = f"https://www.auto-doc.fr/search?keyword={keyword}"
    url = "https://piloterr.com/api/v2/autodoc/search"
    headers = {"Content-Type": "application/json", "x-api-key": api_key}
    params = {"query": query}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None

if __name__ == "__main__":
    input_csv = "RAV4_brake_articles_data_2.csv"
    output_csv = "RAV4_brake_articles_data_processed.csv"

    # Load source data
    parts_df = load_parts_data(input_csv)

    # If progress exists, resume
    if os.path.exists(output_csv):
        processed_df = pd.read_csv(output_csv)
        processed_articles = set(processed_df["articleNo"].unique())
        print("Resuming from saved progress...")
    else:
        processed_df = pd.DataFrame(columns=list(parts_df.columns) + ["updated_price"])
        processed_articles = set()

    for index, row in parts_df.iloc[145:186].iterrows():
        keyword = row['articleNo']
        if keyword in processed_articles:
            continue  # Skip already processed

        print(f"Processing {index}: {keyword}")
        result = search_autodoc(keyword)

        if result and "results" in result:
            for item in result["results"]:
                # Match reference ignoring spaces
                if str(item.get("reference", "")).replace(" ", "") == str(keyword).replace(" ", ""):
                    new_price = round(item.get("price") * EUR_TO_GBP, 2)
                    print(f"Match found: {keyword} -> £{new_price}")
                    row["updated_price"] = new_price
                    processed_df = pd.concat([processed_df, row.to_frame().T], ignore_index=True)
                    break
            else:
                # If loop finishes without break, no match
                print(f"No valid API match for {keyword}")
        else:
            print(f"No valid API result for {keyword}")

        # Save progress every 5 rows
        if index % 5 == 0:
            processed_df.to_csv(output_csv, index=False)
            print("Progress saved.")

        # Random delay
        time.sleep(random.uniform(0.8, 1.5))

    processed_df.to_csv(output_csv, index=False)
    print(f"\nAll matched data saved to {output_csv}")