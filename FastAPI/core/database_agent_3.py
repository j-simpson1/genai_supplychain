from langchain.agents import tool
import pandas as pd
import os

@tool
def parts_summary(articles_path: str, parts_path: str) -> list:
    """Summarizes product groups by price, count, country of origin, quantity, and % of total cost."""
    try:
        articles_df = pd.read_csv(articles_path)
        parts_df = pd.read_csv(parts_path)
        grouped = articles_df.groupby('productGroupId')
        temp_costs = []

        for productGroupId, group in grouped:
            partDescription = group['articleProductName'].mode()[0]
            averagePrice = round(group['price'].mean(), 2)
            numArticles = group.shape[0]
            mostCommonCountry = group['countryOfOrigin'].mode()[0]
            quantity_row = parts_df[parts_df['productGroupId'] == productGroupId]
            quantity = int(quantity_row['quantity'].values[0]) if not quantity_row.empty else 0
            cost = averagePrice * quantity
            temp_costs.append((productGroupId, partDescription, averagePrice,
                               numArticles, mostCommonCountry, quantity, cost))

        total_cost = sum(item[6] for item in temp_costs) or 1
        return [{
            "productGroupId": item[0],
            "partDescription": item[1],
            "averagePrice": item[2],
            "numArticles": item[3],
            "mostCommonCountryOfOrigin": item[4],
            "quantity": item[5],
            "percentageOfTotalCost": round((item[6] / total_cost) * 100, 2)
        } for item in temp_costs]
    except Exception as e:
        print(e)
        return []


@tool
def top_5_parts_by_price(articles_path: str, parts_path: str) -> list:
    """Returns the top 5 parts by average price including quantity, using total group counts."""
    try:
        articles_df = pd.read_csv(articles_path)
        parts_df = pd.read_csv(parts_path)
        grouped = articles_df.groupby('productGroupId')
        summary_list = []

        for productGroupId, group in grouped:
            partDescription = group['articleProductName'].mode()[0]
            avg_price = round(group['price'].mean(), 3)
            num_articles = group.shape[0]
            quantity_row = parts_df[parts_df['productGroupId'] == productGroupId]
            quantity = int(quantity_row['quantity'].values[0]) if not quantity_row.empty else 0

            summary_list.append({
                "productGroupId": productGroupId,
                "partDescription": partDescription,
                "avg_price": avg_price,
                "num_articles": num_articles,
                "quantity": quantity
            })

        return sorted(summary_list, key=lambda x: x['avg_price'], reverse=True)[:5]
    except Exception as e:
        print(e)
        return []


@tool
def top_5_part_distribution_by_country(articles_path: str) -> list:
    """Returns the top 5 countries by number of unique parts."""
    try:
        articles_df = pd.read_csv(articles_path)
        distribution = articles_df.groupby('countryOfOrigin')['articleNo'].nunique().reset_index()
        distribution.columns = ['countryOfOrigin', 'parts_count']
        return distribution.sort_values(by='parts_count', ascending=False).head(5).to_dict(orient='records')
    except Exception as e:
        print(e)
        return []


@tool
def parts_average_price(articles_path: str) -> list:
    """Returns average price of each part grouped by productGroupId."""
    try:
        articles_df = pd.read_csv(articles_path)
        avg_prices = articles_df.groupby(['productGroupId', 'articleProductName'])['price'].mean().reset_index()
        avg_prices.columns = ['productGroupId', 'partDescription', 'averagePrice']
        avg_prices['averagePrice'] = avg_prices['averagePrice'].round(2)
        return avg_prices.sort_values(by="averagePrice", ascending=False).to_dict(orient='records')
    except Exception as e:
        print(e)
        return []


@tool
def total_component_price(articles_path: str, parts_path: str, vat_rate: float) -> dict:
    """
    Calculates total component cost using the bottom quartile (Q1 threshold) average
    prices for each product group, charging VAT only on taxable parts.
    """

    try:
        # --- Normalize VAT rate ---
        if vat_rate > 1:
            vat_rate = vat_rate / 100.0

        # --- Load Data ---
        articles_df = pd.read_csv(articles_path)
        parts_df = pd.read_csv(parts_path)

        # --- Bottom quartile average calculation ---
        def bottom_quartile_avg(group):
            prices = group['price']
            if len(prices) == 1:
                return prices.iloc[0]
            q1 = prices.quantile(0.25)
            return prices[prices <= q1].mean()

        # --- Compute bottom quartile prices (pandas ≥ 2.1) ---
        bottom_quartile_prices = (
            articles_df.groupby('productGroupId', group_keys=False)
            .apply(bottom_quartile_avg, include_groups=False)
            .reset_index(name='avg_price')
        )

        # --- Merge with quantity & taxable flag ---
        merged = bottom_quartile_prices.merge(parts_df, on='productGroupId', how='left')
        merged['quantity'] = merged['quantity'].fillna(0).astype(int)
        merged['taxable'] = merged['taxable'].fillna(False).astype(bool)

        # --- Calculate costs ---
        taxable_cost = (merged.loc[merged['taxable'], 'avg_price'] *
                        merged.loc[merged['taxable'], 'quantity']).sum()
        nontaxable_cost = (merged.loc[~merged['taxable'], 'avg_price'] *
                           merged.loc[~merged['taxable'], 'quantity']).sum()

        # --- Apply VAT only to taxable parts ---
        total_cost_incl_vat = round(taxable_cost * (1 + vat_rate) + nontaxable_cost, 2)
        total_cost_excl_vat = round(taxable_cost + nontaxable_cost, 2)

        return {
            "totalComponentCostExclVAT": total_cost_excl_vat,
            "totalComponentCostInclVAT": total_cost_incl_vat
        }

    except Exception as e:
        print(f"Error calculating total component price: {e}")
        return {"totalComponentCostExclVAT": 0.0, "totalComponentCostInclVAT": 0.0}


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Build full paths
    articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

    # Call one of the tools
    result = parts_summary.invoke({
        "articles_path": articles_path,
        "parts_path": parts_path
    })
    print(result)