from langchain.agents import tool
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build full paths
articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
quantities_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

# Load data
articles_df = pd.read_csv(articles_path)
quantities_df = pd.read_csv(quantities_path)

@tool
def parts_summary() -> list:
    """Summarizes product groups by price, count, country of origin, and quantity."""
    try:
        # Group article data
        grouped = articles_df.groupby('productGroupId')
        results = []

        for productGroupId, group in grouped:
            partDescription = group['articleProductName'].mode()[0]
            averagePrice = round(group['price'].mean(), 2)
            numArticles = group.shape[0]
            mostCommonCountry = group['countryOfOrigin'].mode()[0]
            quantity_row = quantities_df[quantities_df['productGroupId'] == productGroupId]
            quantity = int(quantity_row['quantity'].values[0]) if not quantity_row.empty else 0

            results.append({
                "productGroupId": productGroupId,
                "partDescription": partDescription,
                "averagePrice": averagePrice,
                "numArticles": numArticles,
                "mostCommonCountryOfOrigin": mostCommonCountry,
                "quantity": quantity
            })
        return results
    except Exception as e:
        print(e)
        return []


@tool
def top_5_parts_by_price() -> list:
    """Returns the top 5 parts by average price including quantity."""
    try:
        # Group articles by product group and part name
        grouped = articles_df.groupby(['productGroupId', 'articleProductName'])
        summary_df = grouped['price'].agg(['mean', 'count']).reset_index()
        summary_df.columns = ['productGroupId', 'partDescription', 'avg_price', 'num_articles']

        # Merge with quantities_df to include quantity
        summary_df = summary_df.merge(quantities_df[['productGroupId', 'quantity']], on='productGroupId', how='left')
        summary_df['quantity'] = summary_df['quantity'].fillna(0).astype(int)

        # Take top 5 by average price
        top5 = summary_df.sort_values(by='avg_price', ascending=False).head(5)
        return top5.to_dict(orient='records')
    except Exception as e:
        print(e)
        return []

@tool
def top_5_part_distribution_by_country() -> list:
    """Returns the top 5 countries by number of unique parts."""
    try:
        distribution = articles_df.groupby('countryOfOrigin')['articleNo'].nunique().reset_index()
        distribution.columns = ['countryOfOrigin', 'parts_count']
        top5 = distribution.sort_values(by='parts_count', ascending=False).head(5)
        return top5.to_dict(orient='records')
    except Exception as e:
        print(e)
        return []

@tool
def parts_average_price() -> list:
    """Returns average price of each part grouped by productGroupId."""
    try:
        avg_prices = articles_df.groupby(['productGroupId', 'articleProductName'])['price'].mean().reset_index()
        avg_prices.columns = ['productGroupId', 'partDescription', 'averagePrice']
        avg_prices['averagePrice'] = avg_prices['averagePrice'].round(2)
        return avg_prices.sort_values(by="averagePrice", ascending=False).to_dict(orient='records')
    except Exception as e:
        print(e)
        return []

@tool
def total_component_price() -> float:
    """Calculates the total price of the component using average price * quantity for each part."""
    try:
        # Calculate average price for each product group
        avg_prices = articles_df.groupby('productGroupId')['price'].mean().reset_index()
        avg_prices.columns = ['productGroupId', 'avg_price']

        # Merge with quantities
        merged = avg_prices.merge(quantities_df, on='productGroupId', how='left')
        merged['quantity'] = merged['quantity'].fillna(0).astype(int)

        # Calculate total price and sum it
        total_price = round((merged['avg_price'] * merged['quantity']).sum(), 2)

        return total_price
    except Exception as e:
        print(e)
        return 0.0

if __name__ == "__main__":
    print(top_5_parts_by_price.invoke({}))