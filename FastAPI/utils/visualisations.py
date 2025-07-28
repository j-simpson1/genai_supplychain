import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import squarify

from FastAPI.utils.theme import apply_corporate_theme

def generate_visualisations(csv_path: str = "article_dummy_data.csv") -> list:
    """Generate professional visualisations and return list of image paths."""
    df = pd.read_csv(csv_path)
    df['priceSource'] = df['priceSource'].astype(str)
    image_paths = []

    output_dir = "visualisations"
    os.makedirs(output_dir, exist_ok=True)
    print("Saving visualisations to:", os.path.abspath(output_dir))

    # Apply corporate theme and get color palette
    corporate_palette = apply_corporate_theme()

    # Box Plot with enhanced styling
    plt.figure(figsize=(12, 7))
    ax = sns.boxplot(
        x="countryOfOrigin",
        y="price",
        hue="countryOfOrigin",  # Fix deprecation warning
        data=df,
        palette=corporate_palette,
        width=0.6,
        linewidth=1.2,
        legend=False  # Hide redundant legend
    )
    ax.set_title("Price Distribution by Country of Origin", fontweight='bold', pad=20)
    ax.set_xlabel("Country of Origin", fontweight='bold')
    ax.set_ylabel("Price (€)", fontweight='bold')

    # Add value labels to median lines
    medians = df.groupby('countryOfOrigin')['price'].median().values
    for i, median in enumerate(medians):
        ax.text(i, median + 0.1, f'€{median:.2f}', ha='center', fontsize=9)

    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    boxplot_path = os.path.join(output_dir, "boxplot_price_by_country.png")
    plt.savefig(boxplot_path, dpi=300, bbox_inches='tight')
    plt.close()
    image_paths.append(boxplot_path)

    # Bar Chart with enhanced styling
    avg_price_supplier = df.groupby("supplierId")["price"].mean().sort_values(ascending=False).reset_index()
    plt.figure(figsize=(12, 7))

    # Create dynamic color palette for suppliers
    num_suppliers = len(avg_price_supplier)
    if num_suppliers > len(corporate_palette):
        # Create a more varied color gradient
        supplier_palette = sns.color_palette([
            "#003366",  # Primary blue
            "#0072CE",  # Secondary blue
            "#4A99D8",  # Lighter blue
            "#7FB2E5",  # Very light blue
            "#001F3D"  # Darker blue
        ], n_colors=num_suppliers)
    else:
        supplier_palette = corporate_palette[:num_suppliers]

    ax = sns.barplot(
        x="supplierId",
        y="price",
        hue="supplierId",  # Fix deprecation warning
        data=avg_price_supplier,
        palette=supplier_palette,
        edgecolor='black',
        linewidth=0.8,
        legend=False  # Hide redundant legend
    )
    ax.set_title("Average Price per Supplier", fontweight='bold', pad=20)
    ax.set_xlabel("Supplier ID", fontweight='bold')
    ax.set_ylabel("Average Price (€)", fontweight='bold')

    # Add value labels on top of bars
    for i, p in enumerate(ax.patches):
        ax.annotate(f'€{p.get_height():.2f}',
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom',
                    fontsize=9, rotation=0)

    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    bar_chart_path = os.path.join(output_dir, "bar_chart_avg_price_per_supplier.png")
    plt.savefig(bar_chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    image_paths.append(bar_chart_path)

    # Treemap with enhanced styling
    product_agg = df.groupby("articleProductName")["price"].sum().reset_index().sort_values("price", ascending=False)
    labels = [
        f"{row['articleProductName']}\n€{row['price']:.2f}"
        for _, row in product_agg.iterrows()
    ]
    sizes = product_agg["price"].values

    # Use corporate colors for treemap
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(sizes)))  # Blue gradient

    plt.figure(figsize=(12, 8))
    squarify.plot(
        sizes=sizes,
        label=labels,
        color=colors,
        alpha=0.9,
        pad=0.02,
        text_kwargs={'fontsize': 11, 'fontweight': 'bold'}
    )
    plt.title("Treemap of Total Price by Product Type", fontsize=16, fontweight='bold', pad=20)
    plt.axis('off')

    # Add footer with data source info
    plt.figtext(0.01, 0.01, f"Data source: {csv_path}", fontsize=8, ha='left')
    plt.figtext(0.99, 0.01, "Generated: " + pd.Timestamp.now().strftime("%Y-%m-%d"), fontsize=8, ha='right')

    plt.tight_layout()
    treemap_path = os.path.join(output_dir, "treemap_product_types.png")
    plt.savefig(treemap_path, dpi=300, bbox_inches='tight')
    plt.close()
    image_paths.append(treemap_path)

    return image_paths

def parts_summary_table_generator(parts_summary):
    headers = [
        "Product Group ID",
        "Description",
        "Average Price (€)",
        "Number of Articles",
        "Most Common Country"
    ]
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

    rows = []
    for p in parts_summary:
        row = (
            f"| {p['productGroupId']} "
            f"| {p['partDescription']} "
            f"| {p['averagePrice']:.2f} "
            f"| {p['numArticles']} "
            f"| {p['mostCommonCountryOfOrigin']} |"
        )
        rows.append(row)

    table = "\n".join([header_row, separator_row] + rows)
    return table
