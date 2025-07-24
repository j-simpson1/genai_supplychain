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
    """Summarizes product groups by price, count, country of origin, quantity, and % of total cost."""
    try:
        # Group article data
        grouped = articles_df.groupby('productGroupId')
        results = []

        # Temporary list to calculate total cost later
        temp_costs = []

        for productGroupId, group in grouped:
            partDescription = group['articleProductName'].mode()[0]
            averagePrice = round(group['price'].mean(), 2)
            numArticles = group.shape[0]
            mostCommonCountry = group['countryOfOrigin'].mode()[0]
            quantity_row = quantities_df[quantities_df['productGroupId'] == productGroupId]
            quantity = int(quantity_row['quantity'].values[0]) if not quantity_row.empty else 0

            cost = averagePrice * quantity
            temp_costs.append((productGroupId, partDescription, averagePrice, numArticles, mostCommonCountry, quantity, cost))

        # Calculate total cost
        total_cost = sum(item[6] for item in temp_costs) or 1  # Avoid division by zero

        # Final results with percentage
        for item in temp_costs:
            percentage = round((item[6] / total_cost) * 100, 2)
            results.append({
                "productGroupId": item[0],
                "partDescription": item[1],
                "averagePrice": item[2],
                "numArticles": item[3],
                "mostCommonCountryOfOrigin": item[4],
                "quantity": item[5],
                "percentageOfTotalCost": percentage
            })

        return results
    except Exception as e:
        print(e)
        return []


@tool
def top_5_parts_by_price() -> list:
    """Returns the top 5 parts by average price including quantity, using total group counts."""
    try:
        # Group by productGroupId only, like parts_summary
        grouped = articles_df.groupby('productGroupId')
        summary_list = []

        for productGroupId, group in grouped:
            # Most common part name for description
            partDescription = group['articleProductName'].mode()[0]
            avg_price = round(group['price'].mean(), 3)
            num_articles = group.shape[0]

            # Merge quantity
            quantity_row = quantities_df[quantities_df['productGroupId'] == productGroupId]
            quantity = int(quantity_row['quantity'].values[0]) if not quantity_row.empty else 0

            summary_list.append({
                "productGroupId": productGroupId,
                "partDescription": partDescription,
                "avg_price": avg_price,
                "num_articles": num_articles,
                "quantity": quantity
            })

        # Take top 5 by average price
        top5 = sorted(summary_list, key=lambda x: x['avg_price'], reverse=True)[:5]
        return top5
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