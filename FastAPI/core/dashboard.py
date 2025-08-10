import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import os
import json

# --- File paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
articles_path = os.path.join(BASE_DIR, "streamlit_data", "articles.csv")
parts_path = os.path.join(BASE_DIR, "streamlit_data", "parts.csv")
json_path = os.path.join(BASE_DIR, "streamlit_data", "ai_supplychain_state.json")

# Load JSON
with open(json_path) as f:
    data = json.load(f)

# Get chart paths
chart_metadata_paths = [c["path"] for c in data["generate"]["chart_metadata"]]
chart_output_paths = list(data["generate"]["simulation_content"]["output_files"]["chart_paths"].values())

# Combine (optional)
chart_paths = list(set(chart_metadata_paths + chart_output_paths))

# --- Load CSVs ---
@st.cache_data
def load_csv(file_path):
    return pd.read_csv(file_path)

st.title("Toyota RAV4 Braking System")

st.markdown("---")

st.header("Chart from the report")

# --- Charts Section ---
for chart_path in chart_paths:
    if os.path.exists(chart_path):
        st.image(chart_path, caption=os.path.basename(chart_path))
    else:
        st.warning(f"Chart not found: {chart_path}")

parts_df = load_csv(parts_path)
articles_df = load_csv(articles_path)

st.markdown("---")

st.header("Streamlit Generated Charts")

# --- 1. BOM Cost Breakdown ---
st.subheader("BOM Cost Contribution")
merged = pd.merge(articles_df, parts_df, on="productGroupId")
merged["total_cost"] = merged["price"] * merged["quantity"]
cost_breakdown = merged.groupby("partDescription")["total_cost"].sum()
fig, ax = plt.subplots()
cost_breakdown.plot(kind="pie", autopct='%1.1f%%', ax=ax)
ax.set_ylabel("")
st.pyplot(fig)



# --- 2. Average Cost × Quantity per Part ---
st.subheader("Average Cost per Part (excl VAT)")

# Merge price and quantity information
merged = pd.merge(articles_df, parts_df, on="productGroupId", how="left")

# Calculate average price per productGroupId and keep partDescription
avg_price_per_part = (
    merged.groupby(["productGroupId", "partDescription"], as_index=False)["price"]
    .mean()
)

# Bring quantity from parts_df (already merged, so take unique)
quantities = parts_df[["productGroupId", "quantity"]]
avg_price_per_part = pd.merge(avg_price_per_part, quantities, on="productGroupId", how="left")

# Compute total cost contribution
avg_price_per_part["total_cost_contribution"] = avg_price_per_part["price"] * avg_price_per_part["quantity"]

# Sort alphabetically by partDescription
avg_price_per_part = avg_price_per_part.sort_values("partDescription")

# Plot bar chart
fig, ax = plt.subplots()
ax.bar(avg_price_per_part["partDescription"], avg_price_per_part["total_cost_contribution"])
ax.set_ylabel("Average Cost × Quantity (£)")
ax.set_xlabel("Part Description")
ax.set_title("Average Cost × Quantity by Part")
plt.xticks(rotation=45, ha='right')
st.pyplot(fig)



# --- 3. Count of Articles by Country of Origin ---
st.subheader("Number of Articles by Country of Origin")
articles_by_country = articles_df["countryOfOrigin"].value_counts().sort_index()

fig, ax = plt.subplots()
articles_by_country.plot(kind="bar", ax=ax)
ax.set_ylabel("Number of Articles")
ax.set_xlabel("Country of Origin")
ax.set_title("Articles by Country of Origin")
st.pyplot(fig)



# --- 4. Number of Articles per Part ---
st.subheader("Number of Articles per Part Description")

# Merge to get part descriptions for each article
merged = pd.merge(articles_df, parts_df, on="productGroupId", how="left")

# Count number of articles for each part description
articles_per_part = merged["partDescription"].value_counts().sort_index()

# Plot bar chart
fig, ax = plt.subplots()
articles_per_part.plot(kind="bar", ax=ax)
ax.set_ylabel("Number of Articles")
ax.set_xlabel("Part Description")
ax.set_title("Articles per Part")
plt.xticks(rotation=45, ha='right')
st.pyplot(fig)


st.markdown("---")

st.header("Data")

# --- Parts Data ---
st.subheader("Parts Data")
st.dataframe(parts_df, use_container_width=True)

# --- Articles Data ---
st.subheader("Articles Data")
st.dataframe(articles_df, use_container_width=True)