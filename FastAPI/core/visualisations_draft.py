import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import squarify

# Load data
# df = pd.read_csv('Toyota_RAV4_brake_dummy_data/article_dummy_data.csv')

# Ensure price source is string for labeling
# df['priceSource'] = df['priceSource'].astype(str)

# Configure general style
sns.set(style="whitegrid")

# 1️⃣ Box Plot: Price by Country of Origin
plt.figure(figsize=(10, 6))
sns.boxplot(
    x="countryOfOrigin",
    y="price",
    hue="countryOfOrigin",  # Added hue parameter
    data=df,
    palette="Set2",
    legend=False  # Disable legend since hue matches x-axis
)
plt.title("Price Distribution by Country of Origin")
plt.xlabel("Country of Origin")
plt.ylabel("Price (€)")
plt.tight_layout()
plt.savefig("boxplot_price_by_country.png")
plt.close()

# 2️⃣ Bar Chart: Average Price per Supplier
avg_price_supplier = df.groupby("supplierId")["price"].mean().reset_index()
plt.figure(figsize=(12, 6))
sns.barplot(
    x="supplierId",
    y="price",
    hue="supplierId",  # Added hue parameter
    data=avg_price_supplier,
    palette="viridis",
    legend=False  # Disable legend since hue matches x-axis
)
plt.title("Average Price per Supplier")
plt.xlabel("Supplier ID")
plt.ylabel("Average Price (€)")
plt.tight_layout()
plt.savefig("bar_chart_avg_price_per_supplier.png")
plt.close()

# 4️⃣ Treemap: Product Types and Prices
# Aggregate prices per product type
product_agg = df.groupby("articleProductName")["price"].sum().reset_index()
labels = [
    f"{row['articleProductName']}\n€{row['price']:.2f}"
    for _, row in product_agg.iterrows()
]
sizes = product_agg["price"].values

plt.figure(figsize=(12, 8))
squarify.plot(
    sizes=sizes,
    label=labels,
    alpha=0.8
)
plt.title("Treemap of Total Price by Product Type")
plt.axis('off')
plt.tight_layout()
plt.savefig("treemap_product_types.png")
plt.close()

print("✅ Visualisations saved as PNG files:")
print(" - boxplot_price_by_country.png")
print(" - bar_chart_avg_price_per_supplier.png")
print(" - scatter_price_vs_source.png")
print(" - treemap_product_types.png")