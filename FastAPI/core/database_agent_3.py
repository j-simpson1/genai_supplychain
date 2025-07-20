import pandas as pd


# Load data
articles_df = pd.read_csv("Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
quantities_df = pd.read_csv("Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")


def parts_summary():
    try:
        grouped = articles_df.groupby('productGroupId')

        results = []
        for productGroupId, group in grouped:
            partDescription = group['articleProductName'].mode()[0]
            averagePrice = round(group['price'].mean(), 2)
            numArticles = group.shape[0]
            mostCommonCountry = group['countryOfOrigin'].mode()[0]

            results.append({
                "productGroupId": productGroupId,
                "partDescription": partDescription,
                "averagePrice": averagePrice,
                "numArticles": numArticles,
                "mostCommonCountryOfOrigin": mostCommonCountry
            })

        return results
    except Exception as e:
        print(e)
        return None

def top_5_parts_by_price():
    try:
        grouped = articles_df.groupby(['productGroupId', 'articleProductName'])

        summary_df = grouped['price'].agg(['mean', 'count']).reset_index()
        summary_df.columns = ['productGroupId', 'partDescription', 'avg_price', 'num_articles']

        top5 = summary_df.sort_values(by='avg_price', ascending=False).head(5)

        return top5.to_dict(orient='records')
    except Exception as e:
        print(e)
        return None

def top_5_part_distrubution_by_country():
    try:
        distribution = articles_df.groupby('countryOfOrigin')['articleNo'].nunique().reset_index()
        distribution.columns = ['countryOfOrigin', 'parts_count']
        top5 = distribution.sort_values(by='parts_count', ascending=False).head(5)
        return top5.to_dict(orient='records')
    except Exception as e:
        print(e)
        return None

def parts_average_price():
    try:
        avg_prices = articles_df.groupby(['productGroupId', 'articleProductName'])['price'].mean().reset_index()
        avg_prices.columns = ['productGroupId', 'partDescription', 'averagePrice']
        avg_prices['averagePrice'] = avg_prices['averagePrice'].round(2)
        return avg_prices.sort_values(by="averagePrice", ascending=False).to_dict(orient='records')
    except Exception as e:
        print(e)
        return None

